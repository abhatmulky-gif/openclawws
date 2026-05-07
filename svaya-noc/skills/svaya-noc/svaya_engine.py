"""
ASTRA Cognitive Engine — FWA Edition
Listens for CPE QoE SOS events from the Redis queue.
All topology and reasoning queries run against TypeDB (replaces Neo4j).
Datalog inference rules in TypeDB provide deterministic decisions;
the LLM is used only for explanation and operator communication.

Spec ref: ASTRA Architecture Spec v1.1, Sections 4.4–4.6
"""

import os
import json
import time
import sys
import redis
import requests
from dotenv import load_dotenv

# Allow importing ASTRA modules from the project root
_ROOT = os.path.join(os.path.dirname(__file__), "../..")
sys.path.insert(0, _ROOT)

from fwa_mvnl import normalize, normalize_alarm
from fwa_uplink_engine import run_uplink_engine, GREEN, AMBER, RED
from fwa_typedb_client import (
    get_topology_context,
    get_interference_pairs,
    get_inferred_decisions,
    insert_cpe_telemetry,
    ping as typedb_ping,
)

env_path = os.path.join(os.path.dirname(__file__), "svaya-poc.env")
load_dotenv(env_path)

REDIS_URL = os.getenv("REDIS_URL")
LLM_URL   = os.getenv("RUNPOD_URL", "http://127.0.0.1:11434/api/chat")

AUTONOMY_LABELS = {
    GREEN: "GREEN  Auto-Execute (no approval required)",
    AMBER: "AMBER  Pending NOC Approval",
    RED:   "RED    Pending Engineering Review",
}


# ---------------------------------------------------------------------------
# DRM validation (CPE data authentication)
# ---------------------------------------------------------------------------

def validate_drm(events: list[dict]) -> list[dict]:
    valid = []
    for ev in events:
        sig = ev.get("drm_signature", "MISSING")
        if "VALID" in sig:
            print(f"  [SECURITY] Valid DRM ({sig}). Accepted.")
            valid.append(ev)
        else:
            print(f"  [SECURITY] Invalid DRM on {ev.get('cpe_id', '?')}. Dropped.")
    return valid


# ---------------------------------------------------------------------------
# LLM-powered FWA RCA (advisory only — decisions come from Datalog)
# ---------------------------------------------------------------------------

def run_fwa_rca(
    events: list[dict],
    topology: list[str],
    inferred: dict,
    uplink_result: dict,
) -> str:
    green_actions = uplink_result.get("execution_plan", {}).get("auto_execute", [])
    amber_actions = uplink_result.get("execution_plan", {}).get("pending_noc_approval", [])

    # Include TypeDB Datalog decisions in the prompt context
    datalog_summary = {
        "green_auto_cpes": [d.get("cpe_id") for d in inferred.get("green_auto", [])],
        "amber_noc_interference": [
            f"{d.get('interferer')} → {d.get('cpe_id')}"
            for d in inferred.get("amber_noc", []) if "interferer" in d
        ],
        "red_silent_zone": [d.get("cpe_id") for d in inferred.get("red_engineering", [])],
        "uplink_audit_required": [d.get("cpe_id") for d in inferred.get("uplink_audit_required", [])],
    }

    prompt = f"""
You are ASTRA, the FWA Autonomous RAN Assurance AI (built on Svaya V9 architecture).
The Datalog reasoning engine (TypeDB) has already determined the safety-critical decisions below.
Your role is to explain the Root Cause Analysis to the NOC operator and confirm the action plan.

=== CPE SOS EVENTS ===
{json.dumps(events, indent=2)}

=== TYPEDB DATALOG DECISIONS (deterministic, no LLM) ===
{json.dumps(datalog_summary, indent=2)}

=== UPLINK ENGINE EXECUTION PLAN ===
Green (auto-execute): {json.dumps(green_actions, indent=2)}
Amber (NOC approval): {json.dumps(amber_actions, indent=2)}

=== TOPOLOGY GRAPH (TypeDB) ===
{chr(10).join(topology) if topology else "TypeDB unavailable — topology not fetched."}

Provide a concise FWA RCA for the NOC operator:
1. ROOT CAUSE — Which FWA uplink challenge?
   (a) Power Splitting/Rank Dilemma  (b) UL/DL Coverage Asymmetry
   (c) High PAPR/Thermal Stress      (d) Static Inter-Cell Interference
2. AFFECTED HOUSEHOLDS — CPE IDs and estimated impact.
3. EXECUTION SUMMARY — confirm what will auto-execute vs. what needs approval.
4. TRUST DASHBOARD — Confidence score + data source tier + counterfactual impact estimate.
"""

    try:
        resp = requests.post(
            "http://127.0.0.1:11434/api/chat",
            json={
                "model": "llama3",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["message"]["content"]
        return f"LLM API error: {resp.text}"
    except Exception as e:
        return f"LLM unreachable at Ollama: {e}"


# ---------------------------------------------------------------------------
# Dashboard printer + Redis state publisher
# ---------------------------------------------------------------------------

def publish_dashboard(r: redis.Redis, events: list[dict], inferred: dict, uplink_result: dict, rca: str):
    green_inferred = len(inferred.get("green_auto", []))
    amber_inferred = len(inferred.get("amber_noc", []))
    red_inferred   = len(inferred.get("red_engineering", []))
    audit          = len(inferred.get("uplink_audit_required", []))
    isolated       = len(inferred.get("isolated_cpes", []))

    uplink_green = uplink_result.get("green_auto", 0)
    uplink_amber = uplink_result.get("amber_noc", 0)
    uplink_red   = uplink_result.get("red_engineering", 0)

    state = {
        "mode": "ASTRA FWA — GRADUATED AUTONOMY",
        "graph_backend": "TypeDB (Datalog deterministic reasoning)",
        "cpes_in_event": len(events),
        "typedb_inferred": {
            "green_auto": green_inferred,
            "amber_noc": amber_inferred,
            "red_engineering": red_inferred,
            "uplink_audit": audit,
            "isolated": isolated,
        },
        "uplink_engine": {
            "green_auto": uplink_green,
            "amber_noc": uplink_amber,
            "red_engineering": uplink_red,
        },
        "guardrails": "All decisions via deterministic Datalog rules. LLM = explanation only.",
        "rca_summary": rca[:500],
        "timestamp": time.time(),
    }
    r.set("astra_dashboard_state", json.dumps(state))

    w = 60
    print("\n" + "=" * w)
    print("ASTRA FWA TRUST DASHBOARD")
    print("=" * w)
    print(f"Knowledge Graph:  TypeDB (Datalog, deterministic)")
    print(f"CPEs in Event:    {len(events)}")
    print()
    print("TypeDB Inference Results (deterministic Datalog rules):")
    print(f"  {AUTONOMY_LABELS[GREEN]}: {green_inferred}")
    print(f"  {AUTONOMY_LABELS[AMBER]}: {amber_inferred}")
    print(f"  {AUTONOMY_LABELS[RED]}:   {red_inferred}")
    print(f"  Uplink Audit Required: {audit}")
    print(f"  Cell Isolation Cascade: {isolated}")
    print()
    print("Uplink Intelligence Engine:")
    print(f"  {AUTONOMY_LABELS[GREEN]}: {uplink_green}")
    print(f"  {AUTONOMY_LABELS[AMBER]}: {uplink_amber}")
    print(f"  {AUTONOMY_LABELS[RED]}:   {uplink_red}")
    print()
    print("Guardrails: Deterministic Datalog (TypeDB) — zero LLM in decision loop")
    print("=" * w + "\n")


# ---------------------------------------------------------------------------
# Main event loop
# ---------------------------------------------------------------------------

def main():
    # Verify TypeDB is reachable before starting
    if not typedb_ping():
        print(f"[WARN] TypeDB not reachable at {TYPEDB_HOST_NOTE}. "
              "Topology queries will be skipped. Run topology_typedb.py first.")

    r = redis.from_url(REDIS_URL)
    print("ASTRA FWA Engine starting. Listening for CPE SOS events on Redis...")
    print("Knowledge Graph: TypeDB (Datalog deterministic reasoning)")

    while True:
        raw_events = []
        while r.llen("raw_alarms") > 0:
            item = r.lpop("raw_alarms")
            if item:
                raw_events.append(json.loads(item))

        if raw_events:
            print(f"\n[!] {len(raw_events)} SOS event(s) received.")

            # 1. DRM validation
            print("[SECURITY] Validating DRM signatures...")
            events = validate_drm(raw_events)
            if not events:
                print("[SECURITY] All payloads failed DRM. Discarding.")
                time.sleep(2)
                continue

            # 2. Normalize through MVNL + persist to TypeDB
            canonical_metrics = []
            for ev in events:
                if "source" in ev or "vendor" in ev:
                    try:
                        cm = normalize(ev)
                        canonical_metrics.append(cm)
                        # Write canonical metric into TypeDB knowledge graph
                        insert_cpe_telemetry(cm)
                    except Exception as exc:
                        print(f"  MVNL/TypeDB error: {exc}")

            # 3. Affected CPE IDs
            affected_cpes = list({
                ev.get("cpe_id") or ev.get("ueId", "unknown")
                for ev in events
            })
            print(f"  Affected CPEs: {affected_cpes}")

            # 4. Topology context from TypeDB (replaces Neo4j)
            topology = []
            try:
                print("  Querying TypeDB for FWA topology context...")
                topology, nms_list = get_topology_context(affected_cpes)
                print(f"  {len(topology)} topology edges, {len(nms_list)} NMS systems")
            except Exception as e:
                print(f"  TypeDB topology query failed: {e}")

            # 5. Interference pairs from TypeDB (replaces Neo4j INTERFERES_WITH query)
            interference_pairs = []
            try:
                interference_pairs = get_interference_pairs(min_persistence_h=0.0)
                print(f"  {len(interference_pairs)} interference pair(s) found in TypeDB")
            except Exception as e:
                print(f"  TypeDB interference query failed: {e}")

            # 6. TypeDB Datalog inference — deterministic decisions
            inferred = {}
            try:
                print("  Running TypeDB Datalog inference (deterministic decisions)...")
                inferred = get_inferred_decisions()
                total_inferred = sum(
                    len(v) for v in inferred.values() if isinstance(v, list)
                )
                print(f"  {total_inferred} inference result(s) derived by Datalog rules")
            except Exception as e:
                print(f"  TypeDB inference query failed: {e}")

            # 7. Uplink Intelligence Engine (complementary rule-based layer)
            print("  Running ASTRA Uplink Intelligence Engine...")
            uplink_result = run_uplink_engine(canonical_metrics, interference_pairs)
            print(
                f"  Engine decisions: {uplink_result['green_auto']} Green / "
                f"{uplink_result['amber_noc']} Amber / {uplink_result['red_engineering']} Red"
            )

            # 8. LLM RCA (explanation only — decisions already determined above)
            print("  Running LLM RCA (advisory explanation)...")
            rca = run_fwa_rca(events, topology, inferred, uplink_result)

            # 9. Publish dashboard
            publish_dashboard(r, events, inferred, uplink_result, rca)

            # 10. Push RCA to notification queue
            r.rpush("rca_notifications", rca)
            print("\n--- ASTRA RCA ---")
            print(rca)

        time.sleep(2)


TYPEDB_HOST_NOTE = "127.0.0.1:1729"

if __name__ == "__main__":
    main()
