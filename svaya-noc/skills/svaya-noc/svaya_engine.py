"""
ASTRA Cognitive Engine — FWA Edition
Listens for CPE QoE SOS events from the Redis queue, runs multi-vendor
topology correlation via Neo4j, applies ASTRA's graduated autonomy model,
and publishes RCA decisions.

Evolved from Svaya V9 engine. Spec ref: ASTRA Architecture Spec v1.1,
Sections 4.2–4.7 (Layers 1–6).
"""

import os
import json
import time
import sys
import redis
import requests
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Allow importing MVNL and Uplink Engine from parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fwa_mvnl import normalize, normalize_alarm
from fwa_uplink_engine import (
    run_uplink_engine, InterferencePair,
    CanonicalUplinkMetrics, GREEN, AMBER, RED,
)

env_path = os.path.join(os.path.dirname(__file__), "svaya-poc.env")
load_dotenv(env_path)

REDIS_URL = os.getenv("REDIS_URL")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
LLM_URL = os.getenv("RUNPOD_URL", "http://127.0.0.1:11434/api/chat")

# ---------------------------------------------------------------------------
# Graduated autonomy tier labels (spec Section 6.1)
# ---------------------------------------------------------------------------
AUTONOMY_LABELS = {
    GREEN: "GREEN — Auto-Execute (No approval required)",
    AMBER: "AMBER — Pending NOC Approval",
    RED:   "RED — Pending Engineering Review",
}

# FWA-specific operation → autonomy tier mapping
FWA_AUTONOMY_MAP = {
    "CPE_REBOOT":              GREEN,
    "MIMO_RANK_ADJUSTMENT":    GREEN,
    "WIFI_CHANNEL_OPT":        GREEN,
    "DPD_UPDATE":              GREEN,
    "SINGLE_CELL_BEAM_ADJ":    AMBER,
    "CARRIER_SHUTDOWN":        AMBER,
    "MULTI_SITE_COMP":         AMBER,
    "TDD_RATIO_CHANGE":        RED,
    "UL_DL_DECOUPLING":        RED,
    "FIRMWARE_UPGRADE":        RED,
}


# ---------------------------------------------------------------------------
# Neo4j topology: FWA CPE-centric graph queries
# ---------------------------------------------------------------------------

def get_fwa_topology_context(cpe_ids: list[str]) -> tuple[list[str], list[str]]:
    """
    Queries Neo4j for CPE → Cell → NMS topology.
    Returns (topology_edges, upstream_nms_systems).
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    topology = []
    nms_systems = set()
    try:
        with driver.session() as session:
            for cpe_id in cpe_ids:
                # CPE → Cell → NMS chain
                q = (
                    "MATCH (c:CPE {id: $cpe_id})-[r]-(n) "
                    "RETURN c.id as src, type(r) as rel, n.id as dst, n.vendor as vendor"
                )
                for rec in session.run(q, cpe_id=cpe_id):
                    edge = f"{rec['src']} -{rec['rel']}→ {rec['dst']}"
                    topology.append(edge)
                    if rec.get("vendor") in ["Ericsson", "Nokia", "Samsung", "Huawei"]:
                        nms_systems.add(rec["dst"])

            # Interference neighbors
            for cpe_id in cpe_ids:
                q = (
                    "MATCH (c:CPE {id: $cpe_id})-[:INTERFERES_WITH]-(n:CPE) "
                    "RETURN c.id as src, n.id as dst"
                )
                for rec in session.run(q, cpe_id=cpe_id):
                    topology.append(f"{rec['src']} -INTERFERES_WITH→ {rec['dst']}")

    finally:
        driver.close()
    return list(set(topology)), list(nms_systems)


def get_interference_pairs_from_graph(cpe_ids: list[str]) -> list[InterferencePair]:
    """Fetches persistent interference edges from Neo4j for the given CPEs."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    pairs = []
    try:
        with driver.session() as session:
            for cpe_id in cpe_ids:
                q = (
                    "MATCH (v:CPE {id: $cpe_id})<-[:INTERFERES_WITH]-(i:CPE) "
                    "OPTIONAL MATCH (i)-[:SERVED_BY]->(ci:Cell) "
                    "OPTIONAL MATCH (v)-[:SERVED_BY]->(cv:Cell) "
                    "RETURN i.id as interferer, v.id as victim, "
                    "       i.vendor as iv, v.vendor as vv, "
                    "       ci.id as cell_i, cv.id as cell_v, "
                    "       i.interference_db as idb, i.persistence_h as ph"
                )
                for rec in session.run(q, cpe_id=cpe_id):
                    pairs.append(InterferencePair(
                        interferer_cpe=rec["interferer"],
                        victim_cpe=rec["victim"],
                        cell_interferer=rec.get("cell_i") or "",
                        cell_victim=rec.get("cell_v") or "",
                        interference_db=float(rec.get("idb") or 0),
                        persistence_hours=float(rec.get("ph") or 0),
                        vendor_interferer=rec.get("iv") or "",
                        vendor_victim=rec.get("vv") or "",
                    ))
    finally:
        driver.close()
    return pairs


# ---------------------------------------------------------------------------
# LLM-powered FWA RCA
# ---------------------------------------------------------------------------

def run_fwa_rca(
    alarms: list[dict],
    topology: list[str],
    uplink_decisions: dict,
    active_telemetry: list[dict],
) -> str:
    green_actions = uplink_decisions.get("execution_plan", {}).get("auto_execute", [])
    amber_actions = uplink_decisions.get("execution_plan", {}).get("pending_noc_approval", [])

    prompt = f"""
You are ASTRA, the FWA Autonomous RAN Assurance AI (inspired by Svaya V9).
Perform a Root Cause Analysis for the following FWA uplink event.

=== CPE SOS EVENTS ===
{json.dumps(alarms, indent=2)}

=== ASTRA UPLINK ENGINE DECISIONS ===
Green (Auto-Execute): {json.dumps(green_actions, indent=2)}
Amber (NOC Approval): {json.dumps(amber_actions, indent=2)}

=== TOPOLOGY GRAPH (Neo4j) ===
{chr(10).join(topology) if topology else "No topology data available."}

=== ACTIVE TELEMETRY ===
{json.dumps(active_telemetry, indent=2)}

Provide a concise professional FWA RCA:
1. ROOT CAUSE — Identify which FWA uplink challenge applies:
   (a) Power Splitting / Rank Dilemma  (b) UL/DL Coverage Asymmetry
   (c) High PAPR / Thermal Stress      (d) Static Inter-Cell Interference
2. AFFECTED HOUSEHOLDS — List CPE IDs and their impact.
3. EXECUTION STRATEGY:
   - Green actions already queued for auto-execution (list them).
   - Amber actions awaiting NOC approval (list with rationale).
   - Red actions requiring engineering review (if any).
4. TRUST DASHBOARD:
   - Confidence Score
   - Data Source Tier (which CPE intelligence tier provided the key signal)
   - Estimated household impact if left unresolved
"""

    try:
        resp = requests.post(
            "http://127.0.0.1:11434/api/chat",
            json={
                "model": "llama3",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        if resp.status_code == 200:
            return resp.json()["message"]["content"]
        return f"LLM API error: {resp.text}"
    except Exception as e:
        return f"LLM unreachable: {e}"


# ---------------------------------------------------------------------------
# DRM validation (retained from Svaya, adapted for FWA)
# ---------------------------------------------------------------------------

def validate_drm(alarms: list[dict]) -> list[dict]:
    valid = []
    for alarm in alarms:
        sig = alarm.get("drm_signature", "MISSING")
        if "VALID" in sig:
            print(f"  [SECURITY] Valid DRM signature ({sig}). Accepted.")
            valid.append(alarm)
        else:
            print(f"  [SECURITY] Invalid DRM signature on payload from {alarm.get('cpe_id', '?')}. Dropped.")
    return valid


# ---------------------------------------------------------------------------
# Dashboard state publisher
# ---------------------------------------------------------------------------

def publish_dashboard(r: redis.Redis, alarms: list[dict], uplink_result: dict, rca: str):
    green = uplink_result.get("green_auto", 0)
    amber = uplink_result.get("amber_noc", 0)
    red = uplink_result.get("red_engineering", 0)
    total = green + amber + red

    state = {
        "mode": "ASTRA FWA — GRADUATED AUTONOMY",
        "cpes_analyzed": len(alarms),
        "total_decisions": total,
        "green_auto": green,
        "amber_noc": amber,
        "red_engineering": red,
        "guardrails": "Deterministic Datalog rules active. LLM advisory only.",
        "rca_summary": rca[:500],
        "timestamp": time.time(),
    }
    r.set("astra_dashboard_state", json.dumps(state))

    print("\n" + "=" * 60)
    print("ASTRA FWA TRUST DASHBOARD")
    print("=" * 60)
    print(f"CPEs Analyzed:        {len(alarms)}")
    print(f"Decisions Generated:  {total}")
    print(f"  {AUTONOMY_LABELS[GREEN]}: {green}")
    print(f"  {AUTONOMY_LABELS[AMBER]}: {amber}")
    print(f"  {AUTONOMY_LABELS[RED]}:   {red}")
    print("Guardrails: Deterministic Datalog rules (TypeDB) — zero LLM in decision loop")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Main event loop
# ---------------------------------------------------------------------------

def main():
    r = redis.from_url(REDIS_URL)
    print("ASTRA FWA Engine starting. Listening for CPE SOS events on Redis...")

    while True:
        raw_events = []
        while r.llen("raw_alarms") > 0:
            item = r.lpop("raw_alarms")
            if item:
                raw_events.append(json.loads(item))

        if raw_events:
            print(f"\n[!] {len(raw_events)} SOS event(s) received. Processing...")

            # 1. DRM validation
            print("[SECURITY] Validating DRM signatures...")
            valid_events = validate_drm(raw_events)
            if not valid_events:
                print("[SECURITY] All payloads failed DRM. Discarding batch.")
                time.sleep(2)
                continue

            # 2. Normalize through MVNL (best effort)
            canonical_metrics: list[CanonicalUplinkMetrics] = []
            for ev in valid_events:
                if "source" in ev or "vendor" in ev:
                    try:
                        canonical_metrics.append(normalize(ev))
                    except Exception as exc:
                        print(f"  MVNL normalization skipped: {exc}")

            # 3. Extract affected CPE IDs
            affected_cpes = list({
                ev.get("cpe_id") or ev.get("ueId", "unknown")
                for ev in valid_events
            })
            print(f"  Affected CPEs: {affected_cpes}")

            # 4. Topology context from Neo4j
            topology, nms_list = [], []
            try:
                print("  Querying Neo4j for FWA topology context...")
                topology, nms_list = get_fwa_topology_context(affected_cpes)
                print(f"  {len(topology)} topology edges found, {len(nms_list)} NMS systems identified")
            except Exception as e:
                print(f"  Neo4j unavailable ({e}) — proceeding without topology")

            # 5. Interference pairs from graph
            interference_pairs = []
            try:
                interference_pairs = get_interference_pairs_from_graph(affected_cpes)
            except Exception:
                pass

            # 6. Run Uplink Intelligence Engine
            print("  Running ASTRA Uplink Intelligence Engine...")
            uplink_result = run_uplink_engine(canonical_metrics, interference_pairs)
            print(
                f"  Decisions: {uplink_result['green_auto']} Green / "
                f"{uplink_result['amber_noc']} Amber / "
                f"{uplink_result['red_engineering']} Red"
            )

            # 7. LLM RCA
            print("  Running Cognitive RCA (LLM advisory)...")
            rca = run_fwa_rca(valid_events, topology, uplink_result, [])

            # 8. Publish dashboard state
            publish_dashboard(r, valid_events, uplink_result, rca)

            # 9. Push RCA to notification queue
            r.rpush("rca_notifications", rca)
            print("\n--- ASTRA RCA OUTPUT ---")
            print(rca)

        time.sleep(2)


if __name__ == "__main__":
    main()
