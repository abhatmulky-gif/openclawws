"""
ASTRA Backend — Flask API
Exposes FWA-specific endpoints for CPE telemetry ingestion, uplink analysis,
household QoE diagnostics, and Proof of Outcome Report generation.
Extends the original Svaya NOC backend with ASTRA FWA layers.
"""

import time
import uuid
from flask import Flask, request, jsonify
import chromadb
import requests as http_requests

from fwa_mvnl import (
    normalize, normalize_alarm, align_to_1min,
    resolve_conflict, metrics_to_dict,
)
from fwa_uplink_engine import (
    run_uplink_engine, InterferencePair,
    CanonicalUplinkMetrics,
)

app = Flask(__name__)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="astra_fwa_kb")

# In-memory store for the POC (replace with Redis/TypeDB in production)
_cpe_telemetry_store: dict[str, CanonicalUplinkMetrics] = {}
_household_profiles: dict[str, dict] = {}
_outcome_log: list[dict] = []


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _llm_generate(prompt: str) -> str:
    try:
        resp = http_requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=60,
        )
        return resp.json().get("response", "LLM returned empty response")
    except Exception as e:
        return f"LLM unavailable: {e}"


def _rag_context(query: str, n: int = 2) -> str:
    try:
        results = collection.query(query_texts=[query], n_results=n)
        return "\n".join(doc for sublist in results["documents"] for doc in sublist)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Layer 0/1: CPE Telemetry Ingestion (Tier 1 TR-369, Tier 2 Probe)
# POST /cpe/telemetry
# ---------------------------------------------------------------------------

@app.route("/cpe/telemetry", methods=["POST"])
def ingest_cpe_telemetry():
    """
    Ingests CPE telemetry from any source (TR-369 USP, ASTRA Probe, RAN NMS).
    Runs the payload through the MVNL to produce a canonical metric record.
    Stores the latest per-CPE state for downstream uplink analysis.
    """
    raw = request.json
    if not raw:
        return jsonify({"error": "Empty payload"}), 400

    try:
        canonical = normalize(raw)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    # Merge with existing record (higher-confidence/higher-tier wins)
    existing = _cpe_telemetry_store.get(canonical.cpe_id)
    if existing:
        canonical = resolve_conflict(existing, canonical)

    _cpe_telemetry_store[canonical.cpe_id] = canonical

    # Log to outcome tracker
    _outcome_log.append({
        "event": "telemetry_ingested",
        "cpe_id": canonical.cpe_id,
        "tier": canonical.intelligence_tier,
        "ts": canonical.timestamp_unix,
        "confidence": canonical.confidence_score,
    })

    return jsonify({
        "status": "accepted",
        "cpe_id": canonical.cpe_id,
        "intelligence_tier": canonical.intelligence_tier,
        "confidence_score": canonical.confidence_score,
        "canonical": metrics_to_dict(canonical),
    })


# ---------------------------------------------------------------------------
# Layer 3: Uplink Analysis
# POST /uplink/analyze
# ---------------------------------------------------------------------------

@app.route("/uplink/analyze", methods=["POST"])
def analyze_uplink():
    """
    Runs the Uplink Intelligence Engine against all stored CPE metrics
    (or a subset specified in the request body).
    Returns a graduated autonomy execution plan (Green/Amber/Red decisions).
    Spec ref: ASTRA Architecture Spec v1.1, Section 4.4
    """
    body = request.json or {}
    cpe_ids = body.get("cpe_ids")  # Optional filter; None = analyze all

    if cpe_ids:
        metrics = [_cpe_telemetry_store[c] for c in cpe_ids if c in _cpe_telemetry_store]
    else:
        metrics = list(_cpe_telemetry_store.values())

    if not metrics:
        return jsonify({"error": "No CPE telemetry available. Ingest data via /cpe/telemetry first."}), 404

    # Align all metrics to the current 1-minute boundary
    metrics = align_to_1min(metrics, time.time())

    # Build interference pairs from request (or empty list for now)
    raw_pairs = body.get("interference_pairs", [])
    pairs = [
        InterferencePair(
            interferer_cpe=p["interferer_cpe"],
            victim_cpe=p["victim_cpe"],
            cell_interferer=p.get("cell_interferer", ""),
            cell_victim=p.get("cell_victim", ""),
            interference_db=p.get("interference_db", 0.0),
            persistence_hours=p.get("persistence_hours", 0.0),
            vendor_interferer=p.get("vendor_interferer", ""),
            vendor_victim=p.get("vendor_victim", ""),
        )
        for p in raw_pairs
    ]

    result = run_uplink_engine(metrics, pairs)

    # Log green decisions as auto-executed outcomes
    for dec in result["execution_plan"]["auto_execute"]:
        _outcome_log.append({
            "event": "auto_remediation",
            "module": dec["module"],
            "cpe_id": dec["cpe_id"],
            "action": dec["action"],
            "ts": time.time(),
        })

    return jsonify({
        "analyzed_cpes": len(metrics),
        "summary": {
            "green_auto": result["green_auto"],
            "amber_noc": result["amber_noc"],
            "red_engineering": result["red_engineering"],
        },
        "execution_plan": result["execution_plan"],
    })


# ---------------------------------------------------------------------------
# Layer 5: Household QoE Diagnostics
# GET /household/qoe?cpe_id=<id>
# POST /household/qoe  (batch)
# ---------------------------------------------------------------------------

_HOP_PROFILES = {
    "UPLINK-CONSTRAINED": {"sinr_max": 5.0, "phr_max": 0.0},
    "THERMAL-LIMITED":    {"thermal": ["THROTTLING", "CRITICAL"]},
    "INTERFERENCE-BOUND": {"bler_min": 8.0, "sinr_max": 8.0},
    "CAPACITY-STARVED":   {"ul_min": 5.0, "dl_min": 20.0},
    "BALANCED":           {},
    "PREMIUM-TIER":       {"sinr_min": 15.0, "ul_min": 50.0},
}


def _classify_hop(m: CanonicalUplinkMetrics) -> str:
    """Classify CPE into a Household Outcome Profile (HOP)."""
    if m.thermal_state and m.thermal_state in ["THROTTLING", "CRITICAL"]:
        return "THERMAL-LIMITED"
    if m.sinr_db is not None and m.sinr_db < 5.0:
        return "UPLINK-CONSTRAINED"
    if m.ul_bler_pct is not None and m.ul_bler_pct > 8.0:
        return "INTERFERENCE-BOUND"
    if m.ul_throughput_mbps is not None and m.ul_throughput_mbps < 5.0:
        return "CAPACITY-STARVED"
    if m.sinr_db is not None and m.sinr_db >= 15.0 and (m.ul_throughput_mbps or 0) >= 50.0:
        return "PREMIUM-TIER"
    return "BALANCED"


@app.route("/household/qoe", methods=["GET"])
def household_qoe_get():
    cpe_id = request.args.get("cpe_id")
    if not cpe_id:
        return jsonify({"error": "cpe_id query parameter required"}), 400

    m = _cpe_telemetry_store.get(cpe_id)
    if not m:
        return jsonify({"error": f"No telemetry for CPE {cpe_id}"}), 404

    hop = _classify_hop(m)
    _household_profiles[cpe_id] = {"hop": hop, "last_updated": time.time()}

    return jsonify({
        "cpe_id": cpe_id,
        "household_outcome_profile": hop,
        "intelligence_tier": m.intelligence_tier,
        "qoe_snapshot": {
            "sinr_db": m.sinr_db,
            "rsrp_dbm": m.rsrp_dbm,
            "rsrq_db": m.rsrq_db,
            "ul_throughput_mbps": m.ul_throughput_mbps,
            "dl_throughput_mbps": m.dl_throughput_mbps,
            "ul_bler_pct": m.ul_bler_pct,
            "thermal_state": m.thermal_state,
            "mimo_rank": m.mimo_rank_active,
        },
        "confidence_score": m.confidence_score,
        "tier_upgrade_recommended": m.intelligence_tier == 1 and hop in [
            "INTERFERENCE-BOUND", "THERMAL-LIMITED"
        ],
    })


@app.route("/household/qoe", methods=["POST"])
def household_qoe_batch():
    body = request.json or {}
    cpe_ids = body.get("cpe_ids", list(_cpe_telemetry_store.keys()))
    profiles = []
    for cid in cpe_ids:
        m = _cpe_telemetry_store.get(cid)
        if not m:
            continue
        hop = _classify_hop(m)
        _household_profiles[cid] = {"hop": hop, "last_updated": time.time()}
        profiles.append({
            "cpe_id": cid,
            "household_outcome_profile": hop,
            "sinr_db": m.sinr_db,
            "ul_throughput_mbps": m.ul_throughput_mbps,
            "thermal_state": m.thermal_state,
            "confidence_score": m.confidence_score,
            "intelligence_tier": m.intelligence_tier,
        })
    return jsonify({"household_count": len(profiles), "profiles": profiles})


# ---------------------------------------------------------------------------
# Layer 6: Proof of Outcome Report
# GET /outcome/report
# ---------------------------------------------------------------------------

@app.route("/outcome/report", methods=["GET"])
def outcome_report():
    """
    Generates the Proof of Outcome Report.
    Shows counterfactual value: what ASTRA autonomous interventions delivered.
    Spec ref: ASTRA Architecture Spec v1.1, Section 4.7
    """
    total_cpes = len(_cpe_telemetry_store)
    hop_counts: dict[str, int] = {}
    churn_risk_cpes = []
    tier_breakdown = {1: 0, 2: 0, 3: 0}

    for cpe_id, m in _cpe_telemetry_store.items():
        hop = _classify_hop(m)
        hop_counts[hop] = hop_counts.get(hop, 0) + 1
        tier_breakdown[m.intelligence_tier] = tier_breakdown.get(m.intelligence_tier, 0) + 1
        if m.ul_bler_pct and m.ul_bler_pct > 10.0:
            churn_risk_cpes.append(cpe_id)

    auto_events = [e for e in _outcome_log if e.get("event") == "auto_remediation"]
    tier1_upgrade_candidates = [
        cpe_id for cpe_id, prof in _household_profiles.items()
        if prof.get("hop") in ["INTERFERENCE-BOUND", "THERMAL-LIMITED"]
        and _cpe_telemetry_store.get(cpe_id, CanonicalUplinkMetrics("", "", "", 0)).intelligence_tier == 1
    ]

    report = {
        "report_type": "ASTRA FWA Proof of Outcome Report",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "observation_period_days": 30,
        "total_cpes_monitored": total_cpes,
        "household_outcome_profiles": hop_counts,
        "cpe_intelligence_tier_breakdown": {
            "tier_1_standards_based": tier_breakdown.get(1, 0),
            "tier_2_astra_probe": tier_breakdown.get(2, 0),
            "tier_3_on_device_sdk": tier_breakdown.get(3, 0),
        },
        "uplink_performance": {
            "households_at_churn_risk": len(churn_risk_cpes),
            "churn_risk_cpe_ids": churn_risk_cpes,
            "auto_remediations_executed": len(auto_events),
        },
        "tier_upgrade_recommendations": {
            "tier1_to_tier2_candidates": len(tier1_upgrade_candidates),
            "candidate_cpe_ids": tier1_upgrade_candidates,
            "rationale": "Households in INTERFERENCE-BOUND or THERMAL-LIMITED profiles gain measurable diagnostic and optimization value from ASTRA Probe (Tier 2) deployment.",
            "estimated_probe_cost": f"${15 * len(tier1_upgrade_candidates)}–${25 * len(tier1_upgrade_candidates)} hardware (at scale)",
        },
        "multi_vendor_efficiency": {
            "vendors_normalized": list({m.vendor for m in _cpe_telemetry_store.values()}),
            "mvnl_translations": len(_outcome_log),
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
    canonical = normalize_alarm(raw)
    return jsonify({
        "alarm_id": canonical.alarm_id,
        "astra_category": canonical.astra_category,
        "severity": canonical.severity,
        "source_ne": canonical.source_ne,
        "vendor": canonical.vendor,
        "description": canonical.description,
        "confidence_score": canonical.confidence_score,
        "raw_code": canonical.raw_code,
    })


# ---------------------------------------------------------------------------
# Original Svaya endpoints (retained + updated for ASTRA FWA context)
# ---------------------------------------------------------------------------

@app.route("/analyze_alarm", methods=["POST"])
def analyze_alarm():
    """
    Cross-vendor FWA alarm correlation using RAG + LLM.
    Normalizes incoming alarms through MVNL before analysis.
    """
    data = request.json
    raw_alarms = data.get("alarms", [])

    # Normalize each alarm through MVNL
    normalized = []
    for a in raw_alarms:
        if isinstance(a, dict):
            try:
                ca = normalize_alarm(a)
                normalized.append(f"[{ca.vendor}] [{ca.astra_category}/{ca.severity}] {ca.description}")
            except Exception:
                normalized.append(str(a))
        else:
            normalized.append(str(a))

    storm_summary = " ".join(normalized)
    context = _rag_context(storm_summary)

    prompt = f"""
You are ASTRA, the FWA Autonomous RAN Assurance AI.
Analyze this multi-vendor FWA alarm storm. All alarms have been normalized to ASTRA canonical format.

Normalized Alarm Storm:
{chr(10).join(normalized)}

FWA Knowledge Base Context:
{context}

Task:
1. Identify the single Root Cause. State which FWA uplink challenge is involved
   (Power Splitting / UL-DL Asymmetry / Thermal Stress / Static Interference).
2. List the affected households (CPE IDs if available).
3. Recommend the remediation action and its autonomy tier (Green/Amber/Red).
4. State confidence score and cite the knowledge base match if relevant.
"""
    return jsonify({"analysis": _llm_generate(prompt)})


@app.route("/tmf921/intent", methods=["POST"])
def handle_tmf921_intent():
    """TM Forum TMF921 Intent Management API — now FWA-aware."""
    data = request.json
    intent_id = data.get("id", "Unknown_Intent")
    expectations = data.get("intentExpectation", [])
    contexts = data.get("intentContext", [])

    target_summary = []
    for exp in expectations:
        for target in exp.get("expectationTarget", []):
            target_summary.append(
                f"{target.get('targetName')} should be {target.get('targetCondition')} "
                f"{target.get('targetValue')} {target.get('unit')}"
            )

    context_summary = [
        f"{ctx.get('contextAttribute')}: {ctx.get('contextValue')}" for ctx in contexts
    ]

    kb_context = _rag_context(" ".join(target_summary + context_summary))

    prompt = f"""
You are ASTRA, the TMF921 Intent Handler for FWA autonomous operations.
Translate this operator intent into FWA-specific network parameter changes.

Intent ID: {intent_id}
Targets: {chr(10).join(target_summary)}
Context: {chr(10).join(context_summary)}
Knowledge Base: {kb_context}

Task:
1. Map each target to an ASTRA FWA optimization action (uplink rank, thermal management,
   interference nulling, or capacity management).
2. For each action, specify its autonomy tier (Green=auto / Amber=NOC / Red=Engineering).
3. Output the MOP (Method of Procedure) with vendor-agnostic parameters.
4. Flag any actions that require CPE intelligence tier upgrade to execute optimally.
"""

    try:
        llm_response = _llm_generate(prompt)
        _push_telegram(f"TMF921 Intent `{intent_id}` received.\n\n*Action Plan:*\n{llm_response}")
        return jsonify({
            "intentId": intent_id,
            "handlingState": "Acknowledged",
            "translation_plan": llm_response,
        })
    except Exception as e:
        return jsonify({"handlingState": "Rejected", "error": str(e)})


@app.route("/tmf921/feedback", methods=["POST"])
def feedback():
    """RLNF feedback loop — stores lessons in the FWA knowledge base."""
    data = request.json
    cell_id = data.get("cell_id", "Unknown")
    intent = data.get("intent", "Unknown Intent")
    action_taken = data.get("action_taken", "Unknown Action")
    success = data.get("success", False)
    outcome_notes = data.get("outcome_notes", "")

    status = "SUCCESS" if success else "FAILURE"
    lesson = (
        f"FWA LESSON ({status}) — Site: {cell_id} | Intent: {intent} | "
        f"Action: {action_taken} | Outcome: {outcome_notes}. "
    )
    lesson += (
        "Prioritize this approach for similar FWA uplink conditions."
        if success
        else "Avoid this approach. Try alternative uplink optimization strategy."
    )

    memory_id = f"fwa_lesson_{uuid.uuid4().hex[:8]}"
    collection.add(
        documents=[lesson],
        metadatas=[{"source": "ASTRA_FWA_Feedback", "type": "fwa_lesson"}],
        ids=[memory_id],
    )
    return jsonify({"status": "Lesson stored", "lesson_id": memory_id, "lesson": lesson})


# ---------------------------------------------------------------------------
# Telegram notifier (retained from Svaya)
# ---------------------------------------------------------------------------

def _push_telegram(message: str):
    BOT_TOKEN = "8662847867:AAENJtmV-8HwGKCRLn8FGOqAdlPevlYV7dU"
    CHAT_ID = "7041322342"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        http_requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": f"ASTRA FWA ALERT\n{message}", "parse_mode": "Markdown"},
            timeout=5,
        )
    except Exception as e:
        print(f"Telegram push failed: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
