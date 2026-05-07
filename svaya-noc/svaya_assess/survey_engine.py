"""
TM Forum Autonomous Networks Maturity Survey Engine
Aligned to: TM Forum IG1218, IG1230, TR-285
Five eTOM domains assessed at L0–L4 per TM Forum AN framework.

TM Forum L0–L4 definitions:
  L0  Manual operations         — humans perform and decide everything
  L1  Assisted                  — tools surface data; humans decide and act
  L2  Partial automation        — system executes routine tasks; human oversight
  L3  Conditional automation    — intent-driven; human approves exceptions only
  L4  High automation           — system manages end-to-end; human sets objectives
"""

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Question bank
# Each question tagged with a scoring domain (None = profile only, no score)
# ---------------------------------------------------------------------------

SECTIONS = [
    {
        "id": "profile",
        "title": "Network Profile",
        "subtitle": "Help us understand your organisation and network scale",
        "tmf_ref": None,
        "questions": [
            {
                "id": "org_type",
                "text": "What best describes your organisation?",
                "type": "radio",
                "required": True,
                "domain": None,
                "options": [
                    {"value": "mno",      "label": "Mobile Network Operator (MNO)"},
                    {"value": "isp_fwa",  "label": "ISP / FWA-specialised operator"},
                    {"value": "mvno",     "label": "MVNO"},
                    {"value": "other",    "label": "Other / Regional operator"},
                ],
            },
            {
                "id": "fwa_subscribers",
                "text": "How many FWA subscribers do you currently serve?",
                "type": "radio",
                "required": True,
                "domain": None,
                "options": [
                    {"value": "lt_1k",    "label": "Fewer than 1,000"},
                    {"value": "1k_50k",   "label": "1,000 – 50,000"},
                    {"value": "50k_500k", "label": "50,000 – 500,000"},
                    {"value": "gt_500k",  "label": "More than 500,000"},
                ],
            },
            {
                "id": "ran_vendors",
                "text": "Which RAN vendors are in your network?",
                "type": "checkbox",
                "required": False,
                "domain": None,
                "options": [
                    {"value": "ericsson", "label": "Ericsson"},
                    {"value": "nokia",    "label": "Nokia"},
                    {"value": "samsung",  "label": "Samsung"},
                    {"value": "huawei",   "label": "Huawei"},
                    {"value": "other_ran","label": "Other"},
                ],
            },
            {
                "id": "cpe_vendors",
                "text": "Which CPE vendors are in your FWA fleet?",
                "type": "checkbox",
                "required": False,
                "domain": None,
                "options": [
                    {"value": "zte",       "label": "ZTE"},
                    {"value": "inseego",   "label": "Inseego"},
                    {"value": "nokia_cpe", "label": "Nokia FastMile"},
                    {"value": "arcadyan",  "label": "Arcadyan"},
                    {"value": "sagemcom",  "label": "Sagemcom"},
                    {"value": "huawei_cpe","label": "Huawei CPE"},
                    {"value": "other_cpe", "label": "Other"},
                ],
            },
            {
                "id": "vendor_count",
                "text": "How many different RAN + CPE + backhaul vendors do you manage simultaneously?",
                "type": "radio",
                "required": True,
                "domain": None,
                "options": [
                    {"value": "1",   "label": "1 (single-vendor)"},
                    {"value": "2-3", "label": "2–3 vendors"},
                    {"value": "4-6", "label": "4–6 vendors"},
                    {"value": "7+",  "label": "7 or more vendors"},
                ],
            },
        ],
    },
    {
        "id": "fault",
        "title": "Fault Management",
        "subtitle": "Detect, diagnose and resolve network faults",
        "tmf_ref": "eTOM 1.3.6 – Trouble Management",
        "questions": [
            {
                "id": "fault_detection",
                "text": "How does your team detect FWA network faults today?",
                "type": "radio",
                "required": True,
                "domain": "fault",
                "options": [
                    {"value": 0, "label": "Manual monitoring — operators check dashboards and act on subscriber complaints"},
                    {"value": 1, "label": "Automated NMS alerts — threshold-based alarms sent to the NOC"},
                    {"value": 2, "label": "Correlated alerts — multi-vendor alarms aggregated; some scripted first response"},
                    {"value": 3, "label": "Predictive — system forecasts faults and proposes actions; human approves before execution"},
                    {"value": 4, "label": "Autonomous — system detects and resolves faults end-to-end across all vendors"},
                ],
            },
            {
                "id": "mttr",
                "text": "What is your typical Mean Time to Repair (MTTR) for an FWA household outage?",
                "type": "radio",
                "required": True,
                "domain": "fault",
                "options": [
                    {"value": 0, "label": "More than 4 hours"},
                    {"value": 1, "label": "1–4 hours"},
                    {"value": 2, "label": "30 minutes – 1 hour"},
                    {"value": 3, "label": "5–30 minutes"},
                    {"value": 4, "label": "Under 5 minutes (automated resolution)"},
                ],
            },
            {
                "id": "cross_vendor_alarm",
                "text": "Do you correlate alarms across RAN, CPE and backhaul vendors in a single view?",
                "type": "radio",
                "required": True,
                "domain": "fault",
                "options": [
                    {"value": 0, "label": "No — each vendor's NMS is completely siloed"},
                    {"value": 1, "label": "Partially — engineers manually cross-reference multiple systems"},
                    {"value": 2, "label": "Basic — logs exported to a shared dashboard; correlation is still manual"},
                    {"value": 3, "label": "Yes — automated cross-vendor correlation in our OSS/BSS"},
                    {"value": 4, "label": "Yes — full root cause analysis across vendors, automatically"},
                ],
            },
        ],
    },
    {
        "id": "performance",
        "title": "Performance Management",
        "subtitle": "Monitor, analyse and optimise network KPIs",
        "tmf_ref": "eTOM 1.3.7 – QoS / SLA Management",
        "questions": [
            {
                "id": "kpi_review",
                "text": "How often do you review per-CPE KPIs (SINR, uplink throughput, BLER)?",
                "type": "radio",
                "required": True,
                "domain": "performance",
                "options": [
                    {"value": 0, "label": "Rarely — only when subscribers complain"},
                    {"value": 1, "label": "Weekly reports generated by the NMS"},
                    {"value": 2, "label": "Daily dashboards with threshold alerts"},
                    {"value": 3, "label": "Near-real-time with automated threshold-triggered actions"},
                    {"value": 4, "label": "Continuous closed-loop optimisation executing automatically"},
                ],
            },
            {
                "id": "uplink_optimisation",
                "text": "Do you actively optimise FWA uplink parameters (MIMO rank, power headroom, UL/DL ratio)?",
                "type": "radio",
                "required": True,
                "domain": "performance",
                "options": [
                    {"value": 0, "label": "No — vendor defaults used; no uplink tuning"},
                    {"value": 1, "label": "Occasionally during planned maintenance windows"},
                    {"value": 2, "label": "Via scripts or NMS rules on a subset of CPEs"},
                    {"value": 3, "label": "Automated per-CPE optimisation triggered by KPI thresholds"},
                    {"value": 4, "label": "Continuous closed-loop across 100% of CPEs"},
                ],
            },
            {
                "id": "interference_management",
                "text": "How do you handle static inter-cell interference between FWA CPEs?",
                "type": "radio",
                "required": True,
                "domain": "performance",
                "options": [
                    {"value": 0, "label": "We don't — it's not a process today"},
                    {"value": 1, "label": "Identified by NOC engineers during drive tests or subscriber complaints"},
                    {"value": 2, "label": "Identified from NMS reports; resolved manually via beam or power changes"},
                    {"value": 3, "label": "System flags interference pairs; engineer approves remediation"},
                    {"value": 4, "label": "Automated detection and coordinated beam nulling across cell sites"},
                ],
            },
        ],
    },
    {
        "id": "configuration",
        "title": "Configuration Management",
        "subtitle": "Provision, configure and maintain network elements",
        "tmf_ref": "eTOM 1.3.4 – Configuration & Activation",
        "questions": [
            {
                "id": "config_change",
                "text": "How do you push configuration changes to your RAN and CPE fleet?",
                "type": "radio",
                "required": True,
                "domain": "configuration",
                "options": [
                    {"value": 0, "label": "Manual CLI — engineers SSH into individual elements one at a time"},
                    {"value": 1, "label": "Vendor NMS GUI — changes made through each vendor's management console separately"},
                    {"value": 2, "label": "Scripts / automation tools — batch changes scripted, but still per-vendor"},
                    {"value": 3, "label": "Policy-driven intent — changes defined once in OSS; system translates to vendor commands"},
                    {"value": 4, "label": "Fully autonomous — system self-configures based on observed conditions"},
                ],
            },
            {
                "id": "tr369_support",
                "text": "What is the TR-369 (USP) or TR-069 (CWMP) status in your CPE fleet?",
                "type": "radio",
                "required": True,
                "domain": "configuration",
                "options": [
                    {"value": 0, "label": "Not assessed / don't know"},
                    {"value": 1, "label": "TR-069 (CWMP) on some CPEs, no active ACS"},
                    {"value": 2, "label": "TR-069 on most CPEs with an active ACS deployed"},
                    {"value": 3, "label": "TR-369 (USP) on newer CPEs; TR-069 fallback on legacy fleet"},
                    {"value": 4, "label": "TR-369 fully deployed — using USP for real-time telemetry and control"},
                ],
            },
        ],
    },
    {
        "id": "fulfillment",
        "title": "Service Fulfillment",
        "subtitle": "Activate and manage FWA subscriber services",
        "tmf_ref": "eTOM 1.3.3 – Service Configuration & Activation",
        "questions": [
            {
                "id": "cpe_activation",
                "text": "How do you activate a new FWA CPE for a subscriber today?",
                "type": "radio",
                "required": True,
                "domain": "fulfillment",
                "options": [
                    {"value": 0, "label": "Engineer visit required — manual on-site configuration every time"},
                    {"value": 1, "label": "Pre-configured device shipped; call-centre agent walks subscriber through setup"},
                    {"value": 2, "label": "Subscriber self-install; online portal or app assists configuration"},
                    {"value": 3, "label": "Zero-touch: CPE auto-registers using pre-provisioned profile — no human interaction"},
                    {"value": 4, "label": "Autonomous: CPE registers, configures, and optimises placement-specific settings automatically"},
                ],
            },
            {
                "id": "truck_roll_rate",
                "text": "What percentage of new FWA activations still require an engineer truck roll?",
                "type": "radio",
                "required": True,
                "domain": "fulfillment",
                "options": [
                    {"value": 0, "label": "More than 80%"},
                    {"value": 1, "label": "50–80%"},
                    {"value": 2, "label": "20–50%"},
                    {"value": 3, "label": "5–20%"},
                    {"value": 4, "label": "Less than 5% — near-zero touch"},
                ],
            },
        ],
    },
    {
        "id": "energy",
        "title": "Energy Management",
        "subtitle": "Monitor and optimise energy consumption across your network",
        "tmf_ref": "eTOM 1.3.14 – Resource Sustainability",
        "questions": [
            {
                "id": "energy_monitoring",
                "text": "How do you currently monitor energy consumption at cell site and CPE level?",
                "type": "radio",
                "required": True,
                "domain": "energy",
                "options": [
                    {"value": 0, "label": "No energy monitoring at network element level"},
                    {"value": 1, "label": "Site-level power monitoring via utility meters only"},
                    {"value": 2, "label": "Per-sector energy from NMS; manual reporting"},
                    {"value": 3, "label": "Automated energy dashboards with anomaly alerts"},
                    {"value": 4, "label": "Closed-loop: automatic carrier shutdown, traffic steering, CPE power management"},
                ],
            },
        ],
    },
    {
        "id": "contact",
        "title": "Get Your Report",
        "subtitle": "We'll send your full PDF report and keep you informed about Svaya",
        "tmf_ref": None,
        "questions": [
            {
                "id": "contact_name",
                "text": "Your name",
                "type": "text",
                "required": True,
                "domain": None,
                "placeholder": "Jane Smith",
            },
            {
                "id": "company",
                "text": "Company / Organisation",
                "type": "text",
                "required": True,
                "domain": None,
                "placeholder": "Acme Telecom",
            },
            {
                "id": "email",
                "text": "Work email",
                "type": "email",
                "required": True,
                "domain": None,
                "placeholder": "jane@acmetelecom.com",
            },
            {
                "id": "phone",
                "text": "Phone (optional)",
                "type": "text",
                "required": False,
                "domain": None,
                "placeholder": "+1 555 000 0000",
            },
            {
                "id": "probe_consent",
                "text": "Would you like Svaya to perform a live network readiness check?",
                "type": "radio",
                "required": True,
                "domain": None,
                "options": [
                    {"value": "yes", "label": "Yes — I'll provide my NMS endpoint details on the next screen"},
                    {"value": "no",  "label": "No — show my maturity score now"},
                ],
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Industry benchmarks (FWA operators, TM Forum 2025 survey data estimates)
# ---------------------------------------------------------------------------
BENCHMARKS = {
    "fault":         {"avg": 1.4, "top_quartile": 2.8},
    "performance":   {"avg": 1.2, "top_quartile": 2.5},
    "configuration": {"avg": 1.5, "top_quartile": 2.9},
    "fulfillment":   {"avg": 1.8, "top_quartile": 3.1},
    "energy":        {"avg": 0.9, "top_quartile": 2.2},
}

DOMAIN_LABELS = {
    "fault":         "Fault Management",
    "performance":   "Performance Management",
    "configuration": "Configuration Management",
    "fulfillment":   "Service Fulfillment",
    "energy":        "Energy Management",
}

LEVEL_LABELS = {
    0: "L0 — Manual",
    1: "L1 — Assisted",
    2: "L2 — Partial Automation",
    3: "L3 — Conditional Automation",
    4: "L4 — High Automation",
}

LEVEL_COLORS = {0: "#ef4444", 1: "#f97316", 2: "#eab308", 3: "#3b82f6", 4: "#22c55e"}


# ---------------------------------------------------------------------------
# Svaya gap-to-capability mapping
# ---------------------------------------------------------------------------
SVAYA_CAPABILITIES = {
    "fault": {
        "name": "ASTRA Cross-Vendor RCA Engine",
        "description": (
            "Correlates alarms across Ericsson, Nokia, Samsung and Huawei in real time. "
            "Deterministic Datalog reasoning (TypeDB) traces root cause across CPE, RAN and backhaul "
            "without relying on statistical ML — so every decision can be audited and explained."
        ),
        "outcome": "Reduce MTTR from hours to under 5 minutes for 70–85% of FWA fault categories.",
        "threshold": 2.0,  # Recommend when domain score < threshold
    },
    "performance": {
        "name": "Uplink Intelligence Engine",
        "description": (
            "Solves the four FWA uplink challenges: MIMO rank optimisation, UL/DL coverage asymmetry, "
            "PAPR-driven thermal stress, and static inter-cell interference. "
            "Tier 1 (TR-369, zero vendor dependency) delivers 85–90% of the optimisation value "
            "with no CPE firmware changes required."
        ),
        "outcome": "Recover 15–30% uplink throughput for edge CPEs; reduce subscriber churn by 20–40%.",
        "threshold": 2.5,
    },
    "configuration": {
        "name": "Multi-Vendor Normalisation Layer (MVNL)",
        "description": (
            "A vendor-agnostic configuration layer with adapters for every major RAN NMS "
            "(Ericsson ENM, Nokia NetAct, Samsung OSS, Huawei iMaster NCE) and CPE protocol "
            "(TR-369 USP, TR-069 CWMP). Write once — execute across your entire multi-vendor fleet."
        ),
        "outcome": "Eliminate per-vendor scripting overhead. Reduce config change OPEX by 40–60%.",
        "threshold": 2.0,
    },
    "fulfillment": {
        "name": "Tier 1 TR-369 CPE Management",
        "description": (
            "Zero-touch CPE activation using the TR-369 (USP) standard — supported by every modern "
            "FWA CPE without firmware changes. Svaya acts as the USP Controller: CPEs auto-register, "
            "receive their subscriber profile, and optimise placement-specific beam settings "
            "within 60 seconds of being powered on."
        ),
        "outcome": "Reduce truck roll rate by 40–60%. Cut new subscriber activation cost by £30–80 per CPE.",
        "threshold": 2.5,
    },
    "energy": {
        "name": "Energy Efficiency Module",
        "description": (
            "Automated carrier shutdown during off-peak hours, traffic-aware beam management, "
            "and CPE transmit power optimisation. Closed-loop energy policy executes against "
            "operator-defined objectives (QoE vs. energy trade-off weights) per Household Outcome Profile."
        ),
        "outcome": "Reduce RAN energy consumption by 15–25% with no QoE degradation during peak hours.",
        "threshold": 1.5,
    },
}


# ---------------------------------------------------------------------------
# Scoring logic
# ---------------------------------------------------------------------------

@dataclass
class MaturityScore:
    domains: dict = field(default_factory=dict)   # {domain: float L0–L4}
    overall: float = 0.0
    level: str = "L0"
    gaps: list = field(default_factory=list)       # domains scoring below threshold
    recommendations: list = field(default_factory=list)


def score_answers(answers: dict) -> MaturityScore:
    """
    Calculate TM Forum L0–L4 maturity score from survey answers.
    answers: {question_id: value}  (value is 0–4 int for scored questions)
    """
    domain_values: dict[str, list] = {}

    for section in SECTIONS:
        for q in section["questions"]:
            if q.get("domain") is None:
                continue
            raw = answers.get(q["id"])
            if raw is None:
                continue
            try:
                level = int(raw)
            except (TypeError, ValueError):
                continue
            domain_values.setdefault(q["domain"], []).append(level)

    domain_scores = {
        domain: round(sum(vals) / len(vals), 2)
        for domain, vals in domain_values.items()
        if vals
    }

    overall = round(sum(domain_scores.values()) / len(domain_scores), 2) if domain_scores else 0.0
    level_int = min(4, int(overall))
    level = f"L{level_int}"

    # Identify gaps and map to Svaya capabilities
    gaps = []
    recommendations = []
    for domain, cap in SVAYA_CAPABILITIES.items():
        score = domain_scores.get(domain, 0.0)
        bench = BENCHMARKS.get(domain, {})
        if score < cap["threshold"]:
            gaps.append(domain)
            recommendations.append({
                "domain": DOMAIN_LABELS.get(domain, domain),
                "domain_key": domain,
                "current_score": score,
                "target_score": int(cap["threshold"]) + 1,
                "benchmark_avg": bench.get("avg", 0),
                "benchmark_top": bench.get("top_quartile", 0),
                "gap_to_benchmark": round(bench.get("avg", 0) - score, 2),
                "capability": cap["name"],
                "description": cap["description"],
                "outcome": cap["outcome"],
            })

    # Sort by biggest gap first
    recommendations.sort(key=lambda r: r["gap_to_benchmark"], reverse=True)

    return MaturityScore(
        domains=domain_scores,
        overall=overall,
        level=level,
        gaps=gaps,
        recommendations=recommendations,
    )


def level_label(score: float) -> str:
    return LEVEL_LABELS.get(min(4, int(score)), "L0 — Manual")


def bar_pct(score: float) -> int:
    return int((score / 4.0) * 100)


def benchmark_pct(domain: str, key: str = "avg") -> int:
    val = BENCHMARKS.get(domain, {}).get(key, 0)
    return int((val / 4.0) * 100)
