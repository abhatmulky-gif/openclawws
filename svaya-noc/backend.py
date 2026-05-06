"""
ASTRA Backend — Flask API
All persistence goes through TypeDB (no Neo4j, no in-memory dict).
Datalog inference results are surfaced directly through /uplink/analyze
and /outcome/report — the knowledge graph does the reasoning.

Spec ref: ASTRA Architecture Spec v1.1
"""

import time
import uuid
from flask import Flask, request, jsonify
import chromadb
import requests as http_requests

from fwa_mvnl import normalize, normalize_alarm
from fwa_uplink_engine import run_uplink_engine
from fwa_typedb_client import (
    insert_cpe_telemetry,
    get_all_uplink_states,
    get_cpe_uplink_state,
    get_interference_pairs,
    get_inferred_decisions,
    get_household_profiles,
    get_multi_vendor_summary,
    update_cpe_status,
    ping as typedb_ping,
)

app = Flask(__name__)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="astra_fwa_kb")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _llm(prompt: str) -> str:
    try:
        resp = http_requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=60,
        )
        return resp.json().get("response", "LLM returned empty response")
    except Exception as e:
        return f"LLM unavailable: {e}"


def _rag(query: str, n: int = 2) -> str:
    try:
        results = collection.query(query_texts=[query], n_results=n)
        return "\n".join(doc for sublist in results["documents"] for doc in sublist)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "typedb": "reachable" if typedb_ping() else "unreachable",
        "graph_backend": "TypeDB (Datalog deterministic reasoning)",
    })


# ---------------------------------------------------------------------------
# Layer 0/1: CPE Telemetry Ingestion
# POST /cpe/telemetry
# Accepts TR-369, ASTRA Probe JSON, or any vendor NMS payload.
# Normalized via MVNL → persisted to TypeDB knowledge graph.
# ---------------------------------------------------------------------------

@app.route("/cpe/telemetry", methods=["POST"])
def ingest_cpe_telemetry():
    raw = request.json
    if not raw:
        return jsonify({"error": "Empty payload"}), 400

    try:
        canonical = normalize(raw)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    try:
        insert_cpe_telemetry(canonical)
        storage = "TypeDB"
    except Exception as e:
        storage = f"TypeDB write failed: {e}"

    return jsonify({
        "status": "accepted",
        "storage": storage,
        "cpe_id": canonical.cpe_id,
        "intelligence_tier": canonical.intelligence_tier,
        "confidence_score": canonical.confidence_score,
        "vendor": canonical.vendor,
    })


# ---------------------------------------------------------------------------
# Layer 3: Uplink Analysis
# POST /uplink/analyze
# Returns two layers of decisions:
#   1. TypeDB Datalog inference (deterministic — zero LLM)
#   2. Uplink Intelligence Engine (rule-based Python layer)
# ---------------------------------------------------------------------------

@app.route("/uplink/analyze", methods=["POST"])
def analyze_uplink():
    body = request.json or {}
    cpe_ids = body.get("cpe_ids")  # None = analyze all CPEs in TypeDB

    # Fetch canonical metrics from TypeDB
    try:
        metrics = get_all_uplink_states(cpe_ids)
    except Exception as e:
        return jsonify({"error": f"TypeDB read failed: {e}"}), 503

    if not metrics:
        return jsonify({"error": "No CPE uplink states in TypeDB. Ingest via /cpe/telemetry first."}), 404

    # Fetch interference pairs from TypeDB graph
    try:
        pairs = get_interference_pairs(min_persistence_h=0.0)
    except Exception:
        pairs = []

    # Layer A: TypeDB Datalog inference (deterministic)
    try:
        inferred = get_inferred_decisions()
    except Exception as e:
        inferred = {"error": str(e)}

    # Layer B: Python Uplink Intelligence Engine
    engine_result = run_uplink_engine(metrics, pairs)

    return jsonify({
        "analyzed_cpes": len(metrics),
        "graph_backend": "TypeDB (Datalog deterministic reasoning)",
        "typedb_inference": {
            "green_auto": len(inferred.get("green_auto", [])),
            "amber_noc": len(inferred.get("amber_noc", [])),
            "red_engineering": len(inferred.get("red_engineering", [])),
            "uplink_audit_required": len(inferred.get("uplink_audit_required", [])),
            "isolated_cpes": len(inferred.get("isolated_cpes", [])),
            "decisions": inferred,
        },
        "uplink_engine": {
            "green_auto": engine_result["green_auto"],
            "amber_noc": engine_result["amber_noc"],
            "red_engineering": engine_result["red_engineering"],
            "execution_plan": engine_result["execution_plan"],
        },
    })


# ---------------------------------------------------------------------------
# Layer 5: Household QoE Diagnostics
# GET /household/qoe?cpe_id=<id>
# POST /household/qoe  (batch — all households in TypeDB)
# ---------------------------------------------------------------------------

_HOP_RULES = [
    ("THERMAL-LIMITED",    lambda m: m.thermal_state in ["THROTTLING", "CRITICAL"]),
    ("UPLINK-CONSTRAINED", lambda m: m.sinr_db is not None and m.sinr_db < 5.0),
    ("INTERFERENCE-BOUND", lambda m: m.ul_bler_pct is not None and m.ul_bler_pct > 8.0),
    ("CAPACITY-STARVED",   lambda m: m.ul_throughput_mbps is not None and m.ul_throughput_mbps < 5.0),
    ("PREMIUM-TIER",       lambda m: m.sinr_db is not None and m.sinr_db >= 15.0
                                     and (m.ul_throughput_mbps or 0) >= 50.0),
]


def _classify_hop(m) -> str:
    for label, rule in _HOP_RULES:
        try:
            if rule(m):
                return label
        except Exception:
            pass
    return "BALANCED"


@app.route("/household/qoe", methods=["GET"])
def household_qoe_get():
    cpe_id = request.args.get("cpe_id")
    if not cpe_id:
        return jsonify({"error": "cpe_id query parameter required"}), 400

    try:
        m = get_cpe_uplink_state(cpe_id)
    except Exception as e:
        return jsonify({"error": f"TypeDB read failed: {e}"}), 503

    if m is None:
        return jsonify({"error": f"CPE '{cpe_id}' not found in TypeDB"}), 404

    hop = _classify_hop(m)
    return jsonify({
        "cpe_id": cpe_id,
        "household_outcome_profile": hop,
        "intelligence_tier": m.intelligence_tier,
        "qoe_snapshot": {
            "sinr_db":            m.sinr_db,
            "rsrp_dbm":           m.rsrp_dbm,
            "rsrq_db":            m.rsrq_db,
            "ul_throughput_mbps": m.ul_throughput_mbps,
            "dl_throughput_mbps": m.dl_throughput_mbps,
            "ul_bler_pct":        m.ul_bler_pct,
            "power_headroom_db":  m.power_headroom_db,
            "thermal_state":      m.thermal_state,
            "mimo_rank":          m.mimo_rank_active,
        },
        "confidence_score": m.confidence_score,
        "tier_upgrade_recommended": (
            m.intelligence_tier == 1 and hop in ["INTERFERENCE-BOUND", "THERMAL-LIMITED"]
        ),
        "source": "TypeDB",
    })


@app.route("/household/qoe", methods=["POST"])
def household_qoe_batch():
    body = request.json or {}
    cpe_ids = body.get("cpe_ids")

    try:
        metrics = get_all_uplink_states(cpe_ids)
    except Exception as e:
        return jsonify({"error": f"TypeDB read failed: {e}"}), 503

    profiles = []
    for m in metrics:
        hop = _classify_hop(m)
        profiles.append({
            "cpe_id":                   m.cpe_id,
            "vendor":                   m.vendor,
            "household_outcome_profile": hop,
            "sinr_db":                  m.sinr_db,
            "ul_throughput_mbps":       m.ul_throughput_mbps,
            "thermal_state":            m.thermal_state,
            "confidence_score":         m.confidence_score,
            "intelligence_tier":        m.intelligence_tier,
        })

    return jsonify({"household_count": len(profiles), "profiles": profiles, "source": "TypeDB"})


# ---------------------------------------------------------------------------
# Layer 6: Proof of Outcome Report
# GET /outcome/report
# Queries TypeDB for all households, Datalog-inferred decisions, vendor stats.
# ---------------------------------------------------------------------------

@app.route("/outcome/report", methods=["GET"])
def outcome_report():
    try:
        hh_profiles  = get_household_profiles()
        inferred      = get_inferred_decisions()
        vendor_summary = get_multi_vendor_summary()
        all_metrics   = get_all_uplink_states()
    except Exception as e:
        return jsonify({"error": f"TypeDB read failed: {e}"}), 503

    # HOP distribution
    hop_counts: dict[str, int] = {}
    tier_counts = {1: 0, 2: 0, 3: 0}
    for m in all_metrics:
        hop = _classify_hop(m)
        hop_counts[hop] = hop_counts.get(hop, 0) + 1
        tier_counts[m.intelligence_tier] = tier_counts.get(m.intelligence_tier, 0) + 1

    # Tier-upgrade candidates (Tier 1 CPEs with problematic HOPs)
    upgrade_candidates = [
        m.cpe_id for m in all_metrics
        if m.intelligence_tier == 1 and _classify_hop(m) in ["INTERFERENCE-BOUND", "THERMAL-LIMITED"]
    ]

    report = {
        "report_type": "ASTRA FWA Proof of Outcome Report",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "observation_period_days": 30,
        "graph_backend": "TypeDB (Datalog deterministic reasoning, no Neo4j)",
        "total_cpes_monitored": len(all_metrics),
        "total_households": len(hh_profiles),
        "household_outcome_profiles": hop_counts,
        "cpe_intelligence_tier_breakdown": {
            "tier_1_standards_based_tr369": tier_counts.get(1, 0),
            "tier_2_astra_probe":           tier_counts.get(2, 0),
            "tier_3_on_device_sdk":         tier_counts.get(3, 0),
        },
        "datalog_inference_summary": {
            "green_auto_actions":     len(inferred.get("green_auto", [])),
            "amber_noc_actions":      len(inferred.get("amber_noc", [])),
            "red_engineering_actions": len(inferred.get("red_engineering", [])),
            "uplink_audit_required":  len(inferred.get("uplink_audit_required", [])),
            "isolated_cpes":          len(inferred.get("isolated_cpes", [])),
        },
        "multi_vendor_summary": vendor_summary,
        "tier_upgrade_recommendations": {
            "tier1_to_tier2_candidates": len(upgrade_candidates),
            "candidate_cpe_ids": upgrade_candidates,
            "rationale": (
                "INTERFERENCE-BOUND and THERMAL-LIMITED CPEs gain measurable diagnostic "
                "value from ASTRA Probe (Tier 2): deep Wi-Fi diagnostics, application-layer "
                "QoE measurement, and LTE-fallback Death Rattle forensics."
            ),
            "estimated_probe_cost": (
                f"${15 * len(upgrade_candidates)}–${25 * len(upgrade_candidates)} "
                f"hardware (at scale, {len(upgrade_candidates)} units)"
            ),
        },
    }
    return jsonify(report)


# ---------------------------------------------------------------------------
# Layer 1/4: Multi-Vendor Alarm Normalization
# POST /mvnl/normalize_alarm
# ---------------------------------------------------------------------------

@app.route("/mvnl/normalize_alarm", methods=["POST"])
def mvnl_normalize_alarm():
    raw = request.json
    if not raw:
        return jsonify({"error": "Empty payload"}), 400
    ca = normalize_alarm(raw)
    return jsonify({
        "alarm_id":       ca.alarm_id,
        "astra_category": ca.astra_category,
        "severity":       ca.severity,
        "source_ne":      ca.source_ne,
        "vendor":         ca.vendor,
        "description":    ca.description,
        "confidence_score": ca.confidence_score,
        "raw_code":       ca.raw_code,
    })


# ---------------------------------------------------------------------------
# Original Svaya endpoints — updated for ASTRA FWA context
# ---------------------------------------------------------------------------

@app.route("/analyze_alarm", methods=["POST"])
def analyze_alarm():
    data = request.json
    raw_alarms = data.get("alarms", [])

    normalized = []
    for a in raw_alarms:
        if isinstance(a, dict):
            try:
                ca = normalize_alarm(a)
                normalized.append(
                    f"[{ca.vendor}][{ca.astra_category}/{ca.severity}] {ca.description}"
                )
            except Exception:
                normalized.append(str(a))
        else:
            normalized.append(str(a))

    context = _rag(" ".join(normalized))
    prompt = f"""
You are ASTRA, the FWA Autonomous RAN Assurance AI.
Analyze this multi-vendor FWA alarm storm. All alarms are in ASTRA canonical format.

Normalized Alarm Storm:
{chr(10).join(normalized)}

FWA Knowledge Base:
{context}

Task:
1. Identify the Root Cause. State which FWA uplink challenge:
   (a) Power Splitting/Rank Dilemma  (b) UL/DL Coverage Asymmetry
   (c) High PAPR/Thermal Stress      (d) Static Inter-Cell Interference
2. List affected CPE IDs and households.
3. Recommend action and its autonomy tier (Green/Amber/Red).
4. Confidence score and knowledge base citation.
"""
    return jsonify({"analysis": _llm(prompt)})


@app.route("/tmf921/intent", methods=["POST"])
def handle_tmf921_intent():
    data = request.json
    intent_id = data.get("id", "Unknown")
    expectations = data.get("intentExpectation", [])
    contexts = data.get("intentContext", [])

    target_summary = [
        f"{t.get('targetName')} should be {t.get('targetCondition')} "
        f"{t.get('targetValue')} {t.get('unit')}"
        for exp in expectations for t in exp.get("expectationTarget", [])
    ]
    context_summary = [
        f"{c.get('contextAttribute')}: {c.get('contextValue')}" for c in contexts
    ]

    kb_context = _rag(" ".join(target_summary + context_summary))
    prompt = f"""
You are ASTRA, the TMF921 Intent Handler for FWA autonomous operations.

Intent ID: {intent_id}
Targets: {chr(10).join(target_summary)}
Context: {chr(10).join(context_summary)}
Knowledge Base: {kb_context}

Task:
1. Map each target to an ASTRA FWA action (uplink rank, thermal, interference nulling, capacity).
2. Autonomy tier for each action (Green=auto / Amber=NOC / Red=Engineering).
3. Output vendor-agnostic MOP parameters.
4. Flag actions requiring CPE intelligence tier upgrade.
"""

    try:
        llm_response = _llm(prompt)
        _push_telegram(f"TMF921 Intent `{intent_id}` received.\n*Plan:*\n{llm_response}")
        return jsonify({
            "intentId": intent_id,
            "handlingState": "Acknowledged",
            "translation_plan": llm_response,
        })
    except Exception as e:
        return jsonify({"handlingState": "Rejected", "error": str(e)})


@app.route("/tmf921/feedback", methods=["POST"])
def feedback():
    data = request.json
    cell_id = data.get("cell_id", "Unknown")
    intent = data.get("intent", "")
    action_taken = data.get("action_taken", "")
    success = data.get("success", False)
    outcome_notes = data.get("outcome_notes", "")

    status = "SUCCESS" if success else "FAILURE"
    lesson = (
        f"FWA LESSON ({status}) — Site: {cell_id} | Intent: {intent} | "
        f"Action: {action_taken} | Outcome: {outcome_notes}. "
        + ("Prioritize for similar FWA conditions." if success else "Avoid — try alternative.")
    )

    memory_id = f"fwa_lesson_{uuid.uuid4().hex[:8]}"
    collection.add(
        documents=[lesson],
        metadatas=[{"source": "ASTRA_FWA_Feedback", "type": "fwa_lesson"}],
        ids=[memory_id],
    )
    return jsonify({"status": "Lesson stored", "lesson_id": memory_id, "lesson": lesson})


# ---------------------------------------------------------------------------
# Telegram notifier
# ---------------------------------------------------------------------------

def _push_telegram(message: str):
    BOT_TOKEN = "8662847867:AAENJtmV-8HwGKCRLn8FGOqAdlPevlYV7dU"
    CHAT_ID = "7041322342"
    try:
        http_requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": f"ASTRA FWA ALERT\n{message}", "parse_mode": "Markdown"},
            timeout=5,
        )
    except Exception as e:
        print(f"Telegram push failed: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
