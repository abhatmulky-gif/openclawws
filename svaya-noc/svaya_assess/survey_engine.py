"""
Svaya Network Autonomy Assessment — Survey Engine
Aligned with TM Forum IG1218 v2.2.0 and IG1252 v1.2.0 (Autonomous Networks
Levels Evaluation Methodology). Assesses across the five cognitive capability
dimensions that TM Forum uses to evaluate autonomous network maturity:
Intent, Awareness, Analysis, Decision, Execution.

Scoring: L0 (Manual) through L5 (Cognitive Autonomous) per IG1218.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Survey structure
# ---------------------------------------------------------------------------

SECTIONS = [
    # ------------------------------------------------------------------ #
    # 0. Operator profile (no scoring — used for segmentation/benchmark)  #
    # ------------------------------------------------------------------ #
    {
        "id": "profile",
        "title": "About Your Network",
        "description": "A few questions to tailor your benchmark results to your technology mix.",
        "tmf_ref": None,
        "questions": [
            {
                "id": "org_type",
                "text": "What best describes your organisation?",
                "type": "radio",
                "domain": None,
                "options": [
                    {"value": "mno",        "label": "Mobile Network Operator (MNO)"},
                    {"value": "fwa",        "label": "Fixed Wireless Access operator / WISP"},
                    {"value": "integrated", "label": "Integrated operator (fixed + mobile + transport)"},
                    {"value": "mvno",       "label": "MVNO with own network elements"},
                    {"value": "integrator", "label": "System integrator / managed service provider"},
                ],
            },
            {
                "id": "network_size",
                "text": "How many subscribers / connections does your network serve?",
                "type": "radio",
                "domain": None,
                "options": [
                    {"value": "<100k",   "label": "Fewer than 100,000"},
                    {"value": "100k-1m", "label": "100,000 – 1 million"},
                    {"value": "1m-10m",  "label": "1 million – 10 million"},
                    {"value": ">10m",    "label": "More than 10 million"},
                ],
            },
            {
                "id": "ran_generations",
                "text": "Which radio generations are active in your RAN today?",
                "type": "checkbox",
                "domain": None,
                "options": [
                    {"value": "2g",    "label": "2G (GSM / GPRS / EDGE)"},
                    {"value": "3g",    "label": "3G (UMTS / HSPA / HSPA+)"},
                    {"value": "4g",    "label": "4G (LTE / LTE-A / LTE-A Pro)"},
                    {"value": "5g_nsa","label": "5G NR Non-Standalone (NSA, anchored on LTE)"},
                    {"value": "5g_sa", "label": "5G NR Standalone (SA, 5G Core)"},
                ],
            },
            {
                "id": "core_type",
                "text": "Which core network domains are in scope for your automation programme?",
                "type": "checkbox",
                "domain": None,
                "options": [
                    {"value": "legacy_core", "label": "Legacy circuit-switched core (MSC, SGSN, HLR)"},
                    {"value": "epc",         "label": "4G EPC (MME, SGW, PGW, HSS, PCRF)"},
                    {"value": "5gc",         "label": "5G Core (AMF, SMF, UPF, PCF, UDM)"},
                    {"value": "ims",         "label": "IMS / VoLTE / VoNR"},
                    {"value": "transport",   "label": "Transport / backhaul (microwave, fiber, IP/MPLS)"},
                ],
            },
            {
                "id": "ran_vendors",
                "text": "Which RAN vendors are in your network? (select all that apply)",
                "type": "checkbox",
                "domain": None,
                "options": [
                    {"value": "ericsson", "label": "Ericsson"},
                    {"value": "nokia",    "label": "Nokia"},
                    {"value": "samsung",  "label": "Samsung"},
                    {"value": "huawei",   "label": "Huawei"},
                    {"value": "zte",      "label": "ZTE"},
                    {"value": "other",    "label": "Other / open RAN / vRAN"},
                ],
            },
            {
                "id": "primary_challenge",
                "text": "What is your single biggest operational challenge today?",
                "type": "radio",
                "domain": None,
                "options": [
                    {"value": "performance",  "label": "Network performance and QoE across generations"},
                    {"value": "faults",       "label": "Fault detection, RCA, and MTTR"},
                    {"value": "energy",       "label": "Energy costs and sustainability targets"},
                    {"value": "multivendor",  "label": "Multi-vendor complexity and OPEX"},
                    {"value": "zerotouch",    "label": "Zero-touch provisioning and service activation"},
                    {"value": "transport",    "label": "Transport capacity planning and protection"},
                    {"value": "core",         "label": "Core network slicing and session management"},
                ],
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # 1. INTENT — Does the system understand and translate business intent? #
    # IG1252 §4.1 Cognitive Dimension: Intent                              #
    # ------------------------------------------------------------------ #
    {
        "id": "intent",
        "title": "Intent — Translating Business Goals into Network Policy",
        "description": (
            "This dimension assesses whether your operations can express high-level "
            "business objectives (QoE targets, energy limits, SLAs) and have those "
            "automatically translated into actionable network parameters."
        ),
        "tmf_ref": "TM Forum IG1252 §4.1 · Intent Cognitive Dimension",
        "questions": [
            {
                "id": "intent_service_objectives",
                "text": "How do you define and communicate service objectives to your network operations?",
                "type": "radio",
                "domain": "intent",
                "required": True,
                "options": [
                    {"value": 0, "label": "Informal verbal instructions; no documented SLAs or KPI targets"},
                    {"value": 1, "label": "Static SLA documents reviewed periodically; operators manually translate targets to network parameters"},
                    {"value": 2, "label": "Structured KPI dashboards with threshold alerts; operators act on breaches"},
                    {"value": 3, "label": "Policy-based configuration templates applied automatically when intent conditions are met"},
                    {"value": 4, "label": "API-driven intent statements (e.g., per-subscriber QoE targets) automatically translated to multi-vendor network parameters"},
                    {"value": 5, "label": "Self-learning intent engine derives optimal policies from observed subscriber outcomes and autonomously adapts without engineering input"},
                ],
            },
            {
                "id": "intent_qoe_translation",
                "text": "How are QoE targets (e.g., throughput, latency, reliability) translated into network element configuration?",
                "type": "radio",
                "domain": "intent",
                "required": True,
                "options": [
                    {"value": 0, "label": "Manual CLI commands per network element; no automation"},
                    {"value": 1, "label": "Script-assisted bulk changes; engineer reviews each batch before execution"},
                    {"value": 2, "label": "Template-based configuration push with manual approval gate"},
                    {"value": 3, "label": "Automated parameter mapping from QoE targets to vendor-specific settings for standard scenarios"},
                    {"value": 4, "label": "Continuous closed-loop: QoE degradation automatically triggers multi-vendor reconfiguration without human approval"},
                    {"value": 5, "label": "Intent engine predicts QoE degradation and pre-adapts configuration before subscriber impact occurs"},
                ],
            },
            {
                "id": "intent_energy_policy",
                "text": "How are energy efficiency and regulatory mandates incorporated into network policy?",
                "type": "radio",
                "domain": "intent",
                "required": True,
                "options": [
                    {"value": 0, "label": "Manual compliance review; ad-hoc network changes"},
                    {"value": 1, "label": "Documented procedures; human ensures compliance is maintained on every change"},
                    {"value": 2, "label": "Automated compliance checks on configuration changes against known rules"},
                    {"value": 3, "label": "Energy and compliance policies automatically enforced alongside QoE optimisation"},
                    {"value": 4, "label": "Multi-objective autonomous optimisation balances QoE, energy, and regulatory constraints simultaneously"},
                    {"value": 5, "label": "Regulatory changes are automatically interpreted and network policies updated; system self-certifies compliance"},
                ],
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # 2. AWARENESS — Does the system have comprehensive network visibility? #
    # IG1252 §4.2 Cognitive Dimension: Awareness                          #
    # ------------------------------------------------------------------ #
    {
        "id": "awareness",
        "title": "Awareness — Real-Time Network State Visibility",
        "description": (
            "This dimension assesses the depth and timeliness of your network "
            "observability — across RAN, core, and transport domains — and your "
            "ability to detect issues before subscribers are impacted."
        ),
        "tmf_ref": "TM Forum IG1252 §4.2 · Awareness Cognitive Dimension",
        "questions": [
            {
                "id": "awareness_telemetry",
                "text": "What is your real-time telemetry coverage across your managed network elements (RAN, core, transport)?",
                "type": "radio",
                "domain": "awareness",
                "required": True,
                "options": [
                    {"value": 0, "label": "No real-time data; periodic manual drive tests or customer complaints only"},
                    {"value": 1, "label": "SNMP traps or TR-069 polling; <50% of fleet covered; 15-minute granularity"},
                    {"value": 2, "label": "TR-069/TR-369 streaming; 5-minute granularity; most fleet covered"},
                    {"value": 3, "label": "TR-369 USP streaming + NMS PM counters; 1-minute granularity; full fleet; cross-domain correlation"},
                    {"value": 4, "label": "Sub-minute telemetry correlated across CPE, RAN, and backhaul; anomalies detected before customer impact"},
                    {"value": 5, "label": "Predictive awareness via digital twin; model-based anomaly detection before network events actually occur"},
                ],
            },
            {
                "id": "awareness_correlation",
                "text": "How do you correlate performance across network domains (RAN, core, transport, access)?",
                "type": "radio",
                "domain": "awareness",
                "required": True,
                "options": [
                    {"value": 0, "label": "Manual correlation by experienced engineers; ad-hoc and slow"},
                    {"value": 1, "label": "Separate dashboards per domain; operator manually correlates events"},
                    {"value": 2, "label": "Basic cross-domain views in NMS; limited automation"},
                    {"value": 3, "label": "Automated cross-domain event correlation; root-cause hypotheses generated automatically"},
                    {"value": 4, "label": "Real-time topology-aware correlation across CPE, RAN, and backhaul with confidence-scored root-cause identification"},
                    {"value": 5, "label": "Self-learning correlation model continuously discovers new failure mode patterns autonomously"},
                ],
            },
            {
                "id": "awareness_detection_speed",
                "text": "How quickly do you become aware of subscriber-impacting events?",
                "type": "radio",
                "domain": "awareness",
                "required": True,
                "options": [
                    {"value": 0, "label": "Customer complaint-driven; often more than 24 hours after impact begins"},
                    {"value": 1, "label": "NMS alarm within 15 minutes; requires NOC analyst review to assess impact"},
                    {"value": 2, "label": "Automated alert within 5 minutes with estimated affected subscriber count"},
                    {"value": 3, "label": "Pre-emptive detection within 1 minute; subscribers not yet impacted when action begins"},
                    {"value": 4, "label": "Predictive detection: degradation forecast minutes before occurrence; system pre-positions remediation"},
                    {"value": 5, "label": "Event predicted hours in advance; network self-heals proactively, subscribers never aware"},
                ],
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # 3. ANALYSIS — Can the system derive insight and root cause?         #
    # IG1252 §4.3 Cognitive Dimension: Analysis                           #
    # ------------------------------------------------------------------ #
    {
        "id": "analysis",
        "title": "Analysis — Root Cause and Impact Reasoning",
        "description": (
            "This dimension assesses how well your operations diagnose faults, "
            "identify root causes across domains, and quantify business impact — "
            "and how much of that is automated vs. manual."
        ),
        "tmf_ref": "TM Forum IG1252 §4.3 · Analysis Cognitive Dimension",
        "questions": [
            {
                "id": "analysis_rca",
                "text": "How do you diagnose the root cause of network performance degradation across domains?",
                "type": "radio",
                "domain": "analysis",
                "required": True,
                "options": [
                    {"value": 0, "label": "Engineer manually inspects logs; diagnosis takes hours to days"},
                    {"value": 1, "label": "Rule-based alarm correlation; engineer selects likely cause from a checklist"},
                    {"value": 2, "label": "Pattern-matching RCA system suggests probable causes; engineer validates selection"},
                    {"value": 3, "label": "AI-assisted RCA identifies root cause across domains with 70–85% confidence; reasoning is auditable"},
                    {"value": 4, "label": "Deterministic reasoning engine traces root cause across CPE, RAN, and backhaul with full audit trail in under 60 seconds"},
                    {"value": 5, "label": "Proactive analysis identifies emerging failure patterns and resolves root cause before the first subscriber is impacted"},
                ],
            },
            {
                "id": "analysis_alarm_storms",
                "text": "How do you manage alarm storms (mass simultaneous events from a single root cause)?",
                "type": "radio",
                "domain": "analysis",
                "required": True,
                "options": [
                    {"value": 0, "label": "Each alarm handled individually; NOC is overwhelmed during storms"},
                    {"value": 1, "label": "Basic deduplication by alarm type; manual grouping by experienced engineers"},
                    {"value": 2, "label": "Automated grouping by topology proximity; root-cause hypothesis is presented to NOC"},
                    {"value": 3, "label": "Intelligent suppression presents a single root-cause alarm plus impacted subscriber count"},
                    {"value": 4, "label": "Zero alarm storm reaches NOC; root cause identified and actioned before secondary alarms trigger"},
                    {"value": 5, "label": "Pre-emptive suppression: system resolves the root cause before any alarms fire"},
                ],
            },
            {
                "id": "analysis_business_impact",
                "text": "Can you quantify the business impact (revenue, churn risk) of a network event in real time?",
                "type": "radio",
                "domain": "analysis",
                "required": True,
                "options": [
                    {"value": 0, "label": "No impact quantification; engineers focus on technical metrics only"},
                    {"value": 1, "label": "Post-incident report estimates affected subscriber-hours; reviewed weekly"},
                    {"value": 2, "label": "Real-time impacted subscriber count visible during incidents"},
                    {"value": 3, "label": "Automated churn-risk scoring per subscriber during degradation events"},
                    {"value": 4, "label": "Revenue impact and churn probability continuously updated and used to prioritise automation actions"},
                    {"value": 5, "label": "Predictive churn prevention: network self-optimises to maximise subscriber lifetime value autonomously"},
                ],
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # 4. DECISION — Can the system generate and validate remediation?     #
    # IG1252 §4.4 Cognitive Dimension: Decision                           #
    # ------------------------------------------------------------------ #
    {
        "id": "decision",
        "title": "Decision — Autonomous Remediation and Governance",
        "description": (
            "This dimension assesses how optimisation decisions are made, approved, "
            "and audited — and the degree to which your governance framework permits "
            "autonomous action vs. requiring human approval."
        ),
        "tmf_ref": "TM Forum IG1252 §4.4 · Decision Cognitive Dimension",
        "questions": [
            {
                "id": "decision_approval",
                "text": "How are optimisation actions decided and approved in your operations?",
                "type": "radio",
                "domain": "decision",
                "required": True,
                "options": [
                    {"value": 0, "label": "Senior engineer makes all decisions manually; no automation"},
                    {"value": 1, "label": "NOC analyst selects from a list of recommended actions and approves each one"},
                    {"value": 2, "label": "Automation proposes actions with risk score; team lead must approve before execution"},
                    {"value": 3, "label": "Tiered governance: low-risk auto-approved (green), medium-risk NOC approval (amber), high-risk engineering review (red)"},
                    {"value": 4, "label": "Policy-bounded autonomy: system executes within a pre-approved envelope; humans monitor outcomes only"},
                    {"value": 5, "label": "Fully autonomous: system adapts its own decision boundaries based on outcome learning within regulatory limits"},
                ],
            },
            {
                "id": "decision_rollback",
                "text": "How is rollback handled when an automated change degrades performance?",
                "type": "radio",
                "domain": "decision",
                "required": True,
                "options": [
                    {"value": 0, "label": "Manual rollback requires engineering effort; no automated capability"},
                    {"value": 1, "label": "Rollback scripts are available but must be manually triggered by an engineer"},
                    {"value": 2, "label": "Automated rollback triggered by threshold breach within a defined time window"},
                    {"value": 3, "label": "Instant rollback with root-cause analysis explaining why the change failed"},
                    {"value": 4, "label": "Predictive rollback: system detects degradation trajectory and reverts before the threshold is breached"},
                    {"value": 5, "label": "No rollback needed: digital twin pre-validates every change before execution; bad changes never reach production"},
                ],
            },
            {
                "id": "decision_audit",
                "text": "Can your team track and audit every automated decision with its full rationale?",
                "type": "radio",
                "domain": "decision",
                "required": True,
                "options": [
                    {"value": 0, "label": "No audit trail; decisions are undocumented"},
                    {"value": 1, "label": "Change logs with engineer notes; rationale is informal"},
                    {"value": 2, "label": "Automated change log; trigger conditions recorded but no decision rationale captured"},
                    {"value": 3, "label": "Each automated action logged with trigger condition, expected outcome, and approver"},
                    {"value": 4, "label": "Full explainable AI audit trail: every decision traceable to input data, rule fired, and confidence score"},
                    {"value": 5, "label": "Decision audit fed into continuous learning; model improves measurably from every action taken"},
                ],
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # 5. EXECUTION — Can the system apply changes with zero-touch?        #
    # IG1252 §4.5 Cognitive Dimension: Execution                          #
    # ------------------------------------------------------------------ #
    {
        "id": "execution",
        "title": "Execution — Zero-Touch Multi-Vendor Orchestration",
        "description": (
            "This dimension assesses your ability to apply configuration changes "
            "across a multi-vendor, multi-technology fleet with zero or minimal human "
            "intervention — from routine optimisation through to zero-touch service activation."
        ),
        "tmf_ref": "TM Forum IG1252 §4.5 · Execution Cognitive Dimension",
        "questions": [
            {
                "id": "execution_config_push",
                "text": "How are configuration changes applied across your network element fleet (RAN, core, transport)?",
                "type": "radio",
                "domain": "execution",
                "required": True,
                "options": [
                    {"value": 0, "label": "Manual CLI per element; engineer logs in to each device individually"},
                    {"value": 1, "label": "Scripted mass change; engineer reviews the full change list and approves before execution"},
                    {"value": 2, "label": "Template-based push via NMS/OSS; automated for standard operations, manual for edge cases"},
                    {"value": 3, "label": "Intent-driven config push across multi-vendor, multi-technology fleet; vendor translation handled automatically"},
                    {"value": 4, "label": "Continuous autonomous optimisation across the full estate; no human intervention for routine changes"},
                    {"value": 5, "label": "Network elements receive abstract policy objectives directly; no per-element orchestration needed"},
                ],
            },
            {
                "id": "execution_multivendor",
                "text": "How do you manage configuration across multiple vendors and network domains?",
                "type": "radio",
                "domain": "execution",
                "required": True,
                "options": [
                    {"value": 0, "label": "Separate domain/vendor teams; manual coordination and separate change windows per domain"},
                    {"value": 1, "label": "Centralised OSS provides multi-vendor view; changes still vendor-specific and sequential"},
                    {"value": 2, "label": "Multi-vendor orchestration layer exists; some automation but vendor-specific scripts required"},
                    {"value": 3, "label": "Vendor-agnostic configuration layer with single policy engine translating to all vendor interfaces"},
                    {"value": 4, "label": "Full multi-vendor, multi-domain closed-loop: changes executed simultaneously with automated verification"},
                    {"value": 5, "label": "Self-integrating: system automatically discovers new vendor equipment or domain and builds adapters without engineering effort"},
                ],
            },
            {
                "id": "execution_zerotouch",
                "text": "How do you activate new network elements or services (manual commissioning vs. zero-touch)?",
                "type": "radio",
                "domain": "execution",
                "required": True,
                "options": [
                    {"value": 0, "label": "Full manual commissioning on-site; engineer configures each element individually"},
                    {"value": 1, "label": "Partial automation: basic provisioning scripted but site-specific parameters done on-site"},
                    {"value": 2, "label": "Remote provisioning for most elements; some on-site optimisation still required"},
                    {"value": 3, "label": "Zero-touch activation: element auto-provisions and self-configures via standard protocol (ZTP, TR-369, NETCONF) in under 10 minutes"},
                    {"value": 4, "label": "Predictive provisioning: optimal configuration pre-computed before the element is installed; engineer just powers it on"},
                    {"value": 5, "label": "Fully self-commissioning: element learns from neighbours and network context; zero engineer interaction required"},
                ],
            },
        ],
    },

    # ------------------------------------------------------------------ #
    # 6. Contact                                                          #
    # ------------------------------------------------------------------ #
    {
        "id": "contact",
        "title": "Get Your Results",
        "description": "We'll show your results immediately and send a PDF copy.",
        "tmf_ref": None,
        "questions": [
            {"id": "contact_name", "text": "Your name",    "type": "text",  "domain": None, "placeholder": "Jane Smith"},
            {"id": "company",      "text": "Company",      "type": "text",  "domain": None, "placeholder": "ACME Networks"},
            {"id": "email",        "text": "Work email",   "type": "email", "domain": None, "placeholder": "jane@acmenetworks.com"},
            {"id": "phone",        "text": "Phone number", "type": "text",  "domain": None, "placeholder": "+44 7700 000000"},
        ],
    },
]


# ---------------------------------------------------------------------------
# Benchmark data (based on TM Forum IG1218 industry surveys & Bain 2024)
# Scale: 0.0 – 5.0  (L0 – L5)
# ---------------------------------------------------------------------------

BENCHMARKS = {
    "intent":     {"avg": 0.9,  "top_quartile": 2.0},
    "awareness":  {"avg": 1.5,  "top_quartile": 2.5},
    "analysis":   {"avg": 1.0,  "top_quartile": 2.2},
    "decision":   {"avg": 0.8,  "top_quartile": 1.8},
    "execution":  {"avg": 1.3,  "top_quartile": 2.3},
}

DOMAIN_LABELS = {
    "intent":    "Intent",
    "awareness": "Awareness",
    "analysis":  "Analysis",
    "decision":  "Decision",
    "execution": "Execution",
}

LEVEL_LABELS = {
    0: "L0 — Manual",
    1: "L1 — Assisted",
    2: "L2 — Partial Automation",
    3: "L3 — Conditional Autonomy",
    4: "L4 — Highly Autonomous",
    5: "L5 — Cognitive Autonomous",
}

LEVEL_COLORS = {
    0: "#94a3b8",
    1: "#ef4444",
    2: "#f97316",
    3: "#eab308",
    4: "#3b82f6",
    5: "#7c3aed",
}

# ---------------------------------------------------------------------------
# Svaya capability mapping per cognitive dimension
# ---------------------------------------------------------------------------

SVAYA_CAPABILITIES = {
    "intent": {
        "name": "Svaya Intent & Policy Engine",
        "description": (
            "Translates high-level business objectives — QoE targets, energy limits, "
            "churn-risk thresholds — into vendor-specific network parameters across "
            "Ericsson, Nokia, Samsung, and Huawei simultaneously. Intent is expressed "
            "once and continuously enforced via closed-loop feedback."
        ),
        "outcome": "Eliminate per-vendor policy scripting. Reduce intent-to-execution lag from days to seconds.",
        "threshold": 3.0,
    },
    "awareness": {
        "name": "Multi-Domain Telemetry + TypeDB Knowledge Graph",
        "description": (
            "Unifies telemetry from 2G/3G/4G/5G RAN PM counters, core network KPIs "
            "(EPC/5GC/IMS), transport OAM data, and access/CPE telemetry (TR-369 USP) "
            "into a single real-time topology graph. The TypeDB knowledge graph provides "
            "instant cross-domain correlation — linking RAN conditions to core load "
            "and transport health across any vendor mix."
        ),
        "outcome": "Achieve sub-minute, full-estate awareness across RAN, core, and transport — from any vendor and any generation.",
        "threshold": 2.5,
    },
    "analysis": {
        "name": "Cross-Domain RCA Engine (Datalog Deterministic Reasoning)",
        "description": (
            "Svaya's reasoning engine uses Datalog inference rules (TypeDB) to trace "
            "root cause across RAN, core, and transport without LLM uncertainty. "
            "Covers 2G/3G/4G/5G failure modes, core session drop analysis, transport "
            "path degradation, and cross-domain cascading faults. Every decision is "
            "auditable and explainable."
        ),
        "outcome": "Reduce MTTR from hours to under 5 minutes for 70–85% of multi-domain fault categories.",
        "threshold": 2.5,
    },
    "decision": {
        "name": "Graduated Autonomy Engine (Green / Amber / Red)",
        "description": (
            "A risk-tiered decision framework applicable to all network domains: "
            "Green actions execute autonomously, Amber requires NOC approval, Red "
            "requires engineering review. Boundaries are operator-configurable per "
            "domain and technology generation — providing a governance-safe path "
            "from L2 to L4 across RAN, core, and transport."
        ),
        "outcome": "Safe path to L4: start with 20% green actions, reach 80% in 90 days with zero adverse incidents across all domains.",
        "threshold": 2.0,
    },
    "execution": {
        "name": "Multi-Vendor Normalisation Layer + Zero-Touch Orchestration",
        "description": (
            "Svaya's MVNL provides vendor-agnostic execution adapters for Ericsson ENM, "
            "Nokia NetAct, Samsung OSS, Huawei iMaster NCE, and open-source OSS/BSS. "
            "Zero-touch provisioning via ZTP, NETCONF/YANG, and TR-369 USP covers "
            "2G/3G/4G/5G RAN, core VNFs/CNFs, and transport elements equally."
        ),
        "outcome": "Eliminate per-vendor, per-domain scripting. Reduce service activation time from days to minutes across all network layers.",
        "threshold": 2.5,
    },
}


# ---------------------------------------------------------------------------
# Scoring logic
# ---------------------------------------------------------------------------

@dataclass
class MaturityScore:
    domains: dict = field(default_factory=dict)   # {domain: float L0–L5}
    overall: float = 0.0
    level: str = "L0"
    gaps: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)


def score_answers(answers: dict) -> MaturityScore:
    """
    Calculate TM Forum L0–L5 maturity score from survey answers.
    answers: {question_id: value}  (value is 0–5 int for scored questions)
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
    level_int = min(5, int(overall))
    level = LEVEL_LABELS.get(level_int, "L0 — Manual")

    # Identify gaps and map to Svaya capabilities
    gaps = []
    recommendations = []
    for domain, cap in SVAYA_CAPABILITIES.items():
        score = domain_scores.get(domain, 0.0)
        bench = BENCHMARKS.get(domain, {})
        if score < cap["threshold"]:
            gaps.append(domain)
            recommendations.append({
                "domain":          DOMAIN_LABELS.get(domain, domain),
                "domain_key":      domain,
                "current_score":   score,
                "target_score":    int(cap["threshold"]) + 1,
                "benchmark_avg":   bench.get("avg", 0),
                "benchmark_top":   bench.get("top_quartile", 0),
                "gap_to_benchmark": round(bench.get("avg", 0) - score, 2),
                "capability":      cap["name"],
                "description":     cap["description"],
                "outcome":         cap["outcome"],
            })

    # Sort by biggest gap to benchmark first
    recommendations.sort(key=lambda r: r["gap_to_benchmark"], reverse=True)

    return MaturityScore(
        domains=domain_scores,
        overall=overall,
        level=level,
        gaps=gaps,
        recommendations=recommendations,
    )


def level_label(score: float) -> str:
    return LEVEL_LABELS.get(min(5, int(score)), "L0 — Manual")


def bar_pct(score: float, max_score: float = 5.0) -> int:
    return int((score / max_score) * 100)


def benchmark_pct(domain: str, key: str = "avg", max_score: float = 5.0) -> int:
    val = BENCHMARKS.get(domain, {}).get(key, 0)
    return int((val / max_score) * 100)
