"""
Multi-Technology RAN Automation Assessment skill.
Covers autonomous network operations across 2G, 3G, 4G LTE, and 5G NR.
Sub-scenarios reflect a typical mixed-generation MNO estate.
Aligned with TM Forum IG1252 cognitive dimension methodology.
"""

from .base import BaseSkill, SubScenario, Criterion, CriterionOption

_O = CriterionOption


class RANAutonomySkill(BaseSkill):

    id          = "ran_autonomy"
    name        = "Multi-Technology RAN Automation"
    description = (
        "Assesses autonomous operation capability across your full RAN estate — "
        "2G GSM/EDGE, 3G UMTS/HSPA, 4G LTE, and 5G NR (SA/NSA). "
        "Covers intent translation, multi-RAT awareness, cross-generation RCA, "
        "SON/ANR automation, and zero-touch RAN configuration."
    )
    icon = "📶"

    scenarios = [
        SubScenario(
            id="legacy_ran",
            name="2G/3G Legacy RAN",
            description="GSM/GPRS/EDGE, UMTS/HSPA/HSPA+",
            weight=0.20,
        ),
        SubScenario(
            id="lte_ran",
            name="4G LTE RAN",
            description="LTE / LTE-A / LTE-A Pro (cat-M, NB-IoT included)",
            weight=0.40,
        ),
        SubScenario(
            id="nr_ran",
            name="5G NR RAN",
            description="5G NR SA and NSA; mmWave and sub-6 GHz",
            weight=0.40,
        ),
    ]

    criteria = [

        # ---------------------------------------------------------------- #
        # INTENT                                                            #
        # ---------------------------------------------------------------- #

        Criterion(
            id="ran_intent_kpi",
            name="RAN KPI Intent Translation",
            cognitive_activity="Intent",
            weight=0.15,
            question=(
                "How does your system translate operator-defined RAN KPI targets "
                "(throughput, availability, handover success rate) into RAN "
                "parameter policies across your multi-generation estate?"
            ),
            evidence_prompt=(
                "Describe how a KPI target (e.g., raise LTE handover success to 99.5%) "
                "gets translated into RAN configuration — manual, scripted, or automated?"
            ),
            options=[
                _O(0, "L0 Manual",        "RF engineers manually define parameters per site and generation",
                   ["manual", "rf engineer", "per site"]),
                _O(1, "L1 Generation-siloed", "Separate tools per generation (2G/3G/4G/5G); human coordinates",
                   ["separate tools", "siloed", "human coordinates"]),
                _O(2, "L2 Template-push", "NMS templates pushed per generation; engineer selects and approves",
                   ["template", "nms", "approve"]),
                _O(3, "L3 Policy-mapped", "Unified policy layer maps KPI intent to parameters across all generations automatically",
                   ["unified", "policy", "all generations", "automatic"]),
                _O(4, "L4 Closed-loop",   "Closed-loop: KPI breach auto-triggers parameter adjustment across all affected RAN generations",
                   ["closed-loop", "auto-trigger", "all generations"]),
                _O(5, "L5 Self-optimising","Self-learning model derives optimal cross-generation policy from observed QoE outcomes",
                   ["self-learning", "cross-generation", "outcomes"]),
            ],
        ),

        Criterion(
            id="ran_intent_sunset",
            name="Legacy Technology Lifecycle Management",
            cognitive_activity="Intent",
            weight=0.10,
            scenario_specific=False,
            question=(
                "How does your system support 2G/3G network rationalisation decisions "
                "(traffic migration, sunset planning, spectrum refarming)?"
            ),
            options=[
                _O(0, "L0 Manual",     "No automated support; decisions made by planners using spreadsheets",
                   ["manual", "spreadsheet", "planner"]),
                _O(1, "L1 Reports",    "NMS reports show traffic per generation; human decides migration candidates",
                   ["reports", "human decides", "migration"]),
                _O(2, "L2 Analytics",  "Analytics tool identifies candidates for shutdown; human validates each",
                   ["analytics", "candidates", "human validates"]),
                _O(3, "L3 Automated",  "System automatically identifies, traffic-migrates, and deactivates 2G/3G cells meeting shutdown criteria",
                   ["automated", "identifies", "deactivates"]),
                _O(4, "L4 Predictive", "System predicts optimal sunset sequence minimising subscriber impact and maximising spectrum reuse",
                   ["predictive", "sunset", "spectrum reuse"]),
                _O(5, "L5 Autonomous", "System autonomously executes full spectrum refarming including 5G redeployment",
                   ["autonomous", "refarming", "5g redeployment"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # AWARENESS                                                         #
        # ---------------------------------------------------------------- #

        Criterion(
            id="ran_awareness_multirat",
            name="Multi-RAT KPI Collection",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "How does your system collect and unify performance data "
                "across 2G/3G/4G/5G simultaneously?"
            ),
            evidence_prompt=(
                "What NMS/OSS systems do you use per generation? Are KPIs "
                "normalised into a common data model?"
            ),
            options=[
                _O(0, "L0 Siloed",     "Separate OSS/NMS per generation; no unified view",
                   ["separate", "siloed", "different systems"]),
                _O(1, "L1 Manual-merge","Data exported from each OSS and manually correlated in spreadsheets",
                   ["exported", "spreadsheet", "manual"]),
                _O(2, "L2 Partial-unified","Unified NMS covers most generations; 5G or legacy may be separate",
                   ["partial", "unified", "most generations"]),
                _O(3, "L3 Full-unified", "Single OSS/NMS collects 2G–5G KPIs with common naming and granularity",
                   ["single", "all generations", "common naming"]),
                _O(4, "L4 Real-time",   "Real-time streaming KPIs across all generations; sub-minute granularity; automated quality checks",
                   ["real-time", "sub-minute", "all generations", "streaming"]),
                _O(5, "L5 Predictive",  "Digital twin of full multi-generation RAN; predictive awareness before live events",
                   ["digital twin", "predictive", "full ran"]),
            ],
        ),

        Criterion(
            id="ran_awareness_intergen",
            name="Inter-Generation Correlation",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "Can your system automatically correlate events across generations — "
                "e.g., a 4G site issue causing 2G/3G fallback traffic spikes?"
            ),
            options=[
                _O(0, "L0 None",       "No cross-generation correlation; teams work in domain silos",
                   ["none", "silos", "separate teams"]),
                _O(1, "L1 Manual",     "Engineers manually check other-generation dashboards when alerted to an issue",
                   ["manual", "engineer", "checks other"]),
                _O(2, "L2 Basic",      "NMS shows coloured topology per generation; operator navigates between views",
                   ["topology", "coloured", "operator navigates"]),
                _O(3, "L3 Auto-corr",  "System automatically correlates inter-generation events and surfaces cascading impact",
                   ["automated", "correlates", "cascading"]),
                _O(4, "L4 Real-time",  "Real-time cross-generation topology graph; root cause spans all RATs; confidence-scored",
                   ["real-time", "cross-generation", "confidence"]),
                _O(5, "L5 Predictive", "Predicts cross-generation cascade before it occurs; pre-positions remediation",
                   ["predictive", "cascade", "pre-positions"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # ANALYSIS                                                          #
        # ---------------------------------------------------------------- #

        Criterion(
            id="ran_analysis_rca",
            name="Multi-RAT Root Cause Analysis",
            cognitive_activity="Analysis",
            weight=0.15,
            question=(
                "How do you identify root cause when a fault spans multiple RAN "
                "generations or involves a shared element (e.g., shared backhaul, "
                "common BBU, or multi-RAT antenna)?"
            ),
            evidence_prompt=(
                "Describe the last cross-generation fault your team handled — "
                "how was root cause identified and how long did it take?"
            ),
            options=[
                _O(0, "L0 Manual",     "Each generation team investigates independently; root cause coordination is ad-hoc",
                   ["manual", "independent", "ad-hoc"]),
                _O(1, "L1 Bridge",     "NOC bridge call assembles 2G/3G/4G/5G engineers; root cause determined collaboratively",
                   ["bridge call", "multiple engineers", "collaborative"]),
                _O(2, "L2 Tool-aided", "Cross-generation RCA tool correlates alarms; engineer validates root cause hypothesis",
                   ["tool-aided", "correlates", "validates"]),
                _O(3, "L3 AI-RCA",     "AI engine automatically identifies cross-generation root cause with 70–85% confidence in <5 minutes",
                   ["ai", "5 minutes", "cross-generation", "automatic"]),
                _O(4, "L4 Deterministic","Deterministic reasoning traces root cause across all RATs and shared infrastructure in <60 seconds",
                   ["deterministic", "60 seconds", "shared infrastructure"]),
                _O(5, "L5 Proactive",  "Root cause identified and resolved before multi-RAT fault manifests at subscriber level",
                   ["proactive", "before manifest", "self-resolves"]),
            ],
        ),

        Criterion(
            id="ran_analysis_capacity",
            name="Capacity and Coverage Analysis",
            cognitive_activity="Analysis",
            weight=0.10,
            question=(
                "How does your system analyse RAN capacity and coverage evolution "
                "across generations — including 5G rollout impact on 4G load?"
            ),
            options=[
                _O(0, "L0 Manual",     "Capacity planning done manually by planning team quarterly",
                   ["manual", "quarterly", "planning team"]),
                _O(1, "L1 Reports",    "Monthly NMS capacity reports; planning team decides on expansions",
                   ["monthly", "reports", "planning decides"]),
                _O(2, "L2 Analytics",  "Analytics shows cell congestion trends; 5G offload impact manually estimated",
                   ["analytics", "trends", "manually estimated"]),
                _O(3, "L3 Auto-model", "System automatically models 5G offload impact on 4G cells and recommends actions",
                   ["automated", "model", "5g offload", "recommends"]),
                _O(4, "L4 Continuous", "Continuous cross-generation capacity optimisation; 5G rollout automatically rebalances 4G/3G/2G load",
                   ["continuous", "rebalances", "all generations"]),
                _O(5, "L5 Predictive", "Predicts capacity needs 6–12 months out; drives autonomous infrastructure investment recommendations",
                   ["predictive", "6 months", "infrastructure recommendations"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # DECISION                                                          #
        # ---------------------------------------------------------------- #

        Criterion(
            id="ran_decision_son",
            name="SON / Self-Optimising Network Functions",
            cognitive_activity="Decision",
            weight=0.15,
            question=(
                "To what degree are SON functions (ANR, MRO, MLB, MEC) deployed "
                "and autonomously active across your RAN generations?"
            ),
            options=[
                _O(0, "L0 None",       "No SON features deployed; all neighbour/handover/load management is manual",
                   ["no son", "manual", "no features"]),
                _O(1, "L1 Partial-4G", "SON active on 4G only; 2G/3G and 5G still manually managed",
                   ["4g only", "partial", "2g 3g manual"]),
                _O(2, "L2 Multi-RAT",  "SON deployed across 4G and 5G; 2G/3G sunset reducing need",
                   ["4g 5g", "multi-rat", "son deployed"]),
                _O(3, "L3 Coordinated","Cross-generation SON coordination: ANR and MRO decisions consider full multi-RAT topology",
                   ["coordinated", "cross-generation", "anr mro"]),
                _O(4, "L4 Closed-loop","Full closed-loop SON across all active generations; changes applied without human approval",
                   ["closed-loop", "all generations", "no approval"]),
                _O(5, "L5 Cognitive",  "Cognitive SON: system discovers new optimisation strategies beyond vendor-defined SON functions",
                   ["cognitive", "discovers", "beyond vendor"]),
            ],
        ),

        Criterion(
            id="ran_decision_swupgrade",
            name="Software Upgrade Decision Automation",
            cognitive_activity="Decision",
            weight=0.10,
            question=(
                "How are RAN software upgrades (BTS/eNB/gNB) scheduled, "
                "risk-assessed, and executed across your estate?"
            ),
            options=[
                _O(0, "L0 Manual",     "Manual upgrade scheduling; engineer assesses each site individually",
                   ["manual", "engineer", "each site"]),
                _O(1, "L1 Planned",    "Scheduled maintenance windows; human risk-assesses upgrade batches",
                   ["scheduled", "maintenance window", "human risk"]),
                _O(2, "L2 Automated-deploy","Automated deployment to approved batches; rollback triggered manually if issues arise",
                   ["automated deploy", "manual rollback"]),
                _O(3, "L3 Risk-gated", "System auto-assesses upgrade risk per site; applies tiered governance (green/amber/red) per site",
                   ["risk-gated", "tiered", "per site"]),
                _O(4, "L4 Closed-loop","Closed-loop upgrade: system deploys, verifies KPIs, and auto-rolls back failures across all generations",
                   ["closed-loop upgrade", "auto-rollback", "verifies kpi"]),
                _O(5, "L5 Predictive", "Predicts optimal upgrade timing per site based on traffic patterns; zero-impact deployments",
                   ["predictive", "zero impact", "optimal timing"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # EXECUTION                                                         #
        # ---------------------------------------------------------------- #

        Criterion(
            id="ran_execution_multivendor",
            name="Multi-Vendor RAN Configuration Execution",
            cognitive_activity="Execution",
            weight=0.15,
            question=(
                "How are configuration changes executed across a multi-vendor RAN "
                "(e.g., Ericsson ENM + Nokia NetAct + Huawei iMaster) simultaneously?"
            ),
            evidence_prompt=(
                "Describe a recent multi-vendor change: how many vendor systems "
                "were touched, and how was coordination handled?"
            ),
            options=[
                _O(0, "L0 Siloed",     "Separate change processes per vendor; manual coordination; changes applied sequentially",
                   ["siloed", "sequential", "manual coordination"]),
                _O(1, "L1 Orchestrated","Change orchestration tool coordinates sequence; engineers execute per-vendor",
                   ["orchestrated", "coordinates", "engineers execute"]),
                _O(2, "L2 Semi-auto",  "Vendor adapters automate individual vendor changes; human triggers and monitors",
                   ["adapters", "semi-auto", "human triggers"]),
                _O(3, "L3 Vendor-agnostic","Single policy engine translates changes to all vendor CLIs/APIs simultaneously",
                   ["vendor-agnostic", "single policy", "simultaneously"]),
                _O(4, "L4 Full-auto",  "Fully automated multi-vendor execution with parallel rollout, verification, and rollback",
                   ["full auto", "parallel", "verification", "rollback"]),
                _O(5, "L5 Self-adapting","System automatically builds new vendor adapters when new equipment is detected",
                   ["self-adapting", "new adapters", "new equipment"]),
            ],
        ),
    ]


skill = RANAutonomySkill()
