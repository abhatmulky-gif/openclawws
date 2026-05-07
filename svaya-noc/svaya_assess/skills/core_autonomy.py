"""
Multi-Generation Core Network Automation Assessment skill.
Covers autonomous operation across Legacy Core, EPC (4G), 5G Core, and IMS.
Sub-scenarios reflect a typical MNO core estate in transition.
Aligned with TM Forum IG1252 cognitive dimension methodology.
"""

from .base import BaseSkill, SubScenario, Criterion, CriterionOption

_O = CriterionOption


class CoreAutonomySkill(BaseSkill):

    id          = "core_autonomy"
    name        = "Core Network Automation"
    description = (
        "Assesses autonomous operation capability across your full core network estate — "
        "Legacy CS/PS core (MSC, SGSN, HLR), 4G EPC (MME, SGW, PGW, HSS, PCRF), "
        "5G Core (AMF, SMF, UPF, PCF, UDM), and IMS/VoLTE/VoNR. "
        "Covers intent translation, session-level awareness, cross-domain RCA, "
        "traffic steering decisions, and zero-touch CNF/VNF lifecycle execution."
    )
    icon = "🖧"

    scenarios = [
        SubScenario(
            id="legacy_core",
            name="Legacy CS/PS Core",
            description="MSC, SGSN, GGSN, HLR — 2G/3G circuit and packet core",
            weight=0.20,
        ),
        SubScenario(
            id="epc",
            name="4G EPC",
            description="MME, SGW, PGW, HSS, PCRF — LTE evolved packet core",
            weight=0.35,
        ),
        SubScenario(
            id="gc_5g",
            name="5G Core + IMS",
            description="AMF, SMF, UPF, PCF, UDM — service-based 5GC; IMS/VoLTE/VoNR",
            weight=0.45,
        ),
    ]

    criteria = [

        # ---------------------------------------------------------------- #
        # INTENT                                                            #
        # ---------------------------------------------------------------- #

        Criterion(
            id="core_intent_slicing",
            name="Network Slice / QoS Intent Translation",
            cognitive_activity="Intent",
            weight=0.15,
            question=(
                "How does your system translate operator-defined service intents "
                "(e.g., eMBB slice with 10 ms latency, URLLC slice with 1 ms, "
                "VoLTE QoS targets) into core network configuration?"
            ),
            evidence_prompt=(
                "Describe how a new service SLA (e.g., launch an enterprise URLLC slice) "
                "gets turned into AMF/SMF/PCF/UPF policies — manual, scripted, or automated?"
            ),
            options=[
                _O(0, "L0 Manual",       "Engineers manually configure each core NF individually per service launch",
                   ["manual", "engineer", "per nf"]),
                _O(1, "L1 Templates",    "Pre-built slice/QoS templates applied by operations team; human selects and approves",
                   ["templates", "human selects", "operations"]),
                _O(2, "L2 Orchestrated", "NFVO/MANO orchestrator instantiates slice from template; human triggers launch",
                   ["orchestrator", "mano", "human triggers"]),
                _O(3, "L3 Policy-driven","Policy engine translates service intent to 5GC/EPC configuration across all NFs automatically",
                   ["policy-driven", "intent", "all nfs", "automatic"]),
                _O(4, "L4 Closed-loop",  "Closed-loop: SLA breach auto-triggers slice parameter adjustment or scale-out without human approval",
                   ["closed-loop", "sla breach", "auto-trigger"]),
                _O(5, "L5 Cognitive",    "System derives optimal slice topology and NF placement from business objectives; self-adapts to demand",
                   ["cognitive", "self-adapts", "business objectives"]),
            ],
        ),

        Criterion(
            id="core_intent_migration",
            name="Core Migration / Sunset Planning",
            cognitive_activity="Intent",
            weight=0.10,
            scenario_specific=False,
            question=(
                "How does your system support migration planning from legacy CS/PS core "
                "to EPC and 5GC — including subscriber migration, HLR→HSS→UDM progression, "
                "and decommissioning of legacy NFs?"
            ),
            options=[
                _O(0, "L0 Manual",     "Migration planned manually by architects using spreadsheets and ticketing",
                   ["manual", "spreadsheet", "architect"]),
                _O(1, "L1 Reports",    "OSS/BSS reports show subscriber distribution per core domain; planners decide migration batches",
                   ["reports", "planners", "batches"]),
                _O(2, "L2 Analytics",  "Analytics identifies migration candidates; human validates cut-over plan per batch",
                   ["analytics", "candidates", "human validates"]),
                _O(3, "L3 Automated",  "System automatically migrates subscriber profiles, updates routing, and deactivates legacy NFs meeting criteria",
                   ["automated", "migrates", "deactivates"]),
                _O(4, "L4 Predictive", "System predicts optimal migration sequence minimising call/session drop risk and legacy OPEX",
                   ["predictive", "sequence", "call drop risk"]),
                _O(5, "L5 Autonomous", "Fully autonomous core evolution: system orchestrates parallel 5GC build-out and legacy decommission end-to-end",
                   ["autonomous", "5gc", "decommission"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # AWARENESS                                                         #
        # ---------------------------------------------------------------- #

        Criterion(
            id="core_awareness_kpi",
            name="Cross-Core KPI Visibility",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "How does your system collect and unify core KPIs across legacy, EPC, "
                "and 5GC simultaneously — CSFB/VoLTE/VoNR call completion, "
                "session attach rates, PDU session success, UPF throughput?"
            ),
            evidence_prompt=(
                "What OSS/EMS tools monitor your core per domain? Are KPIs "
                "normalised into a common dashboard or data lake?"
            ),
            options=[
                _O(0, "L0 Siloed",      "Separate EMS per core domain (MSC-EMS, MME dashboard, 5GC UI); no unified view",
                   ["siloed", "separate ems", "no unified"]),
                _O(1, "L1 Manual-merge","KPIs exported from each domain and merged manually in spreadsheets or BI tools",
                   ["exported", "manual", "spreadsheet"]),
                _O(2, "L2 Partial",     "Unified NOC dashboard covers EPC and 5GC; legacy core still separate",
                   ["partial", "epc 5gc", "legacy separate"]),
                _O(3, "L3 Unified",     "Single OSS/analytics platform collects all core KPIs with common naming convention",
                   ["single", "all core", "common naming"]),
                _O(4, "L4 Real-time",   "Real-time streaming KPIs across all core domains; automated anomaly detection and baselining",
                   ["real-time", "streaming", "anomaly detection"]),
                _O(5, "L5 Predictive",  "Digital twin of full core estate; predicts KPI degradation before subscribers are affected",
                   ["digital twin", "predictive", "full core"]),
            ],
        ),

        Criterion(
            id="core_awareness_sessions",
            name="Session and Subscriber State Awareness",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "How does your system maintain real-time awareness of active subscriber sessions, "
                "attach states, and handover/CSFB events across core domains?"
            ),
            options=[
                _O(0, "L0 Passive",     "No real-time session visibility; faults detected only via subscriber complaints",
                   ["passive", "complaints", "no real-time"]),
                _O(1, "L1 Polling",     "Core NF statistics polled every 15 minutes; session-level data not visible in real time",
                   ["polling", "15 minutes", "no session-level"]),
                _O(2, "L2 Near-real",   "Near-real-time session counts per NF; drill-down to individual sessions requires manual EMS query",
                   ["near-real", "session counts", "manual query"]),
                _O(3, "L3 Streaming",   "Streaming session state across all core domains; CSFB/VoLTE/handover events correlated automatically",
                   ["streaming", "csfb", "volte", "correlated"]),
                _O(4, "L4 Contextual",  "Session-level context enriched with UE history, policy state, RAN anchor cell; used to pre-empt drops",
                   ["contextual", "ue history", "pre-empt"]),
                _O(5, "L5 Predictive",  "Predicts subscriber experience degradation before session drop; proactively re-routes or re-anchors",
                   ["predictive", "re-routes", "pre-emptive"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # ANALYSIS                                                          #
        # ---------------------------------------------------------------- #

        Criterion(
            id="core_analysis_rca",
            name="Core Fault Root Cause Analysis",
            cognitive_activity="Analysis",
            weight=0.15,
            question=(
                "How do you identify root cause when a core fault spans multiple NFs or "
                "domains — e.g., an MME overload causing CSFB failures, or a UPF issue "
                "affecting both VoLTE and data sessions?"
            ),
            evidence_prompt=(
                "Describe the last major core fault: which NFs were involved, "
                "how long to identify root cause, and what process was used?"
            ),
            options=[
                _O(0, "L0 Manual",      "Each NF team investigates independently; cross-NF correlation is ad-hoc via bridge call",
                   ["manual", "independent", "bridge call"]),
                _O(1, "L1 Log-mining",  "NOC engineers mine EMS logs and alarms from multiple NFs; root cause takes 30+ minutes",
                   ["log-mining", "30 minutes", "manual correlation"]),
                _O(2, "L2 Tool-aided",  "Alarm correlation tool groups related NF alarms; engineer identifies causal chain manually",
                   ["tool-aided", "alarm correlation", "engineer validates"]),
                _O(3, "L3 AI-RCA",      "AI engine automatically identifies cross-NF root cause with 70–85% confidence in <5 minutes",
                   ["ai", "5 minutes", "cross-nf", "automatic"]),
                _O(4, "L4 Deterministic","Deterministic reasoning traces root cause across core, RAN, and transport in <60 seconds",
                   ["deterministic", "60 seconds", "cross-domain"]),
                _O(5, "L5 Proactive",   "Root cause identified and resolved before fault manifests at subscriber or service level",
                   ["proactive", "before manifest", "self-resolves"]),
            ],
        ),

        Criterion(
            id="core_analysis_capacity",
            name="Core Capacity and Dimensioning",
            cognitive_activity="Analysis",
            weight=0.10,
            question=(
                "How does your system analyse core capacity headroom — signalling load on AMF/MME, "
                "PDU session capacity on SMF/PGW, UPF throughput vs. licensed limits — "
                "and recommend dimensioning changes?"
            ),
            options=[
                _O(0, "L0 Manual",     "Capacity dimensioned annually by planning team using peak-hour traffic reports",
                   ["manual", "annual", "planning team"]),
                _O(1, "L1 Reports",    "Monthly NF utilisation reports; team escalates when thresholds breached",
                   ["monthly", "utilisation", "threshold"]),
                _O(2, "L2 Analytics",  "Analytics tracks growth trends; team manually projects capacity exhaustion dates",
                   ["analytics", "trends", "manual projection"]),
                _O(3, "L3 Auto-model", "System automatically models capacity growth and generates scale recommendations per NF",
                   ["automated model", "scale recommendations", "per nf"]),
                _O(4, "L4 Continuous", "Continuous capacity optimisation: VNF/CNF scale-out triggered automatically before NF saturation",
                   ["continuous", "scale-out", "automatic"]),
                _O(5, "L5 Predictive", "Predicts capacity needs 6–12 months out; drives autonomous infrastructure provisioning decisions",
                   ["predictive", "6 months", "autonomous provisioning"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # DECISION                                                          #
        # ---------------------------------------------------------------- #

        Criterion(
            id="core_decision_steering",
            name="Traffic Steering and Load Balancing",
            cognitive_activity="Decision",
            weight=0.15,
            question=(
                "How does your system decide on traffic steering across core NFs — "
                "load balancing across MME/AMF pools, PGW/UPF selection, "
                "and CSFB vs. VoLTE routing decisions?"
            ),
            options=[
                _O(0, "L0 Static",      "Static routing rules configured per vendor; no dynamic steering",
                   ["static", "no dynamic", "vendor rules"]),
                _O(1, "L1 Threshold",   "Threshold-based load alerts trigger manual steering configuration changes",
                   ["threshold", "manual", "alerts"]),
                _O(2, "L2 Rule-based",  "Rule-based PCF/PCRF policies distribute load; human adjusts weights when imbalanced",
                   ["rule-based", "pcf", "human adjusts"]),
                _O(3, "L3 Dynamic",     "Dynamic load balancing across NF pools based on real-time utilisation; no human needed",
                   ["dynamic", "real-time", "automated"]),
                _O(4, "L4 Intent-driven","Intent-driven steering: policy goals (minimise latency, maximise capacity) drive NF selection automatically",
                   ["intent-driven", "policy goals", "automatic"]),
                _O(5, "L5 Predictive",  "Predicts load shifts and pre-positions traffic steering before congestion occurs",
                   ["predictive", "pre-positions", "before congestion"]),
            ],
        ),

        Criterion(
            id="core_decision_swupgrade",
            name="Core NF Software Lifecycle Automation",
            cognitive_activity="Decision",
            weight=0.10,
            question=(
                "How are core NF software upgrades (MME, AMF, SMF, UPF, IMS NFs) "
                "risk-assessed, scheduled, and rolled out across your estate?"
            ),
            options=[
                _O(0, "L0 Manual",       "Manual upgrade scheduling; vendor-executed during maintenance windows",
                   ["manual", "vendor-executed", "maintenance window"]),
                _O(1, "L1 Planned",      "Planned rollout schedule; ops team risk-assesses each NF upgrade individually",
                   ["planned", "ops team", "individual"]),
                _O(2, "L2 Staged-deploy","Staged deployment to lab then pilot then production; human approves each stage",
                   ["staged", "lab pilot", "human approves"]),
                _O(3, "L3 Risk-gated",   "Automated risk scoring per NF (session load, criticality, patch severity); tiered approval gates",
                   ["risk-gated", "automated scoring", "tiered gates"]),
                _O(4, "L4 Closed-loop",  "Closed-loop upgrade: system deploys, monitors KPIs, auto-rolls back if degradation detected",
                   ["closed-loop", "auto-rollback", "kpi monitoring"]),
                _O(5, "L5 Autonomous",   "Fully autonomous lifecycle: system selects upgrade window, deploys, verifies, and decommissions old NF instances",
                   ["autonomous", "lifecycle", "decommissions"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # EXECUTION                                                         #
        # ---------------------------------------------------------------- #

        Criterion(
            id="core_execution_scaling",
            name="CNF/VNF Scaling and Healing Execution",
            cognitive_activity="Execution",
            weight=0.15,
            question=(
                "How are core NF scale-out/in operations and self-healing actions "
                "executed when capacity or fault conditions are detected?"
            ),
            evidence_prompt=(
                "Describe the last time a core NF was scaled: what triggered it, "
                "who or what performed the scale action, and how long did it take?"
            ),
            options=[
                _O(0, "L0 Manual",       "Engineers manually provision additional NF instances via vendor EMS or CLI",
                   ["manual", "engineer", "cli"]),
                _O(1, "L1 Ticketed",     "Ops team raises ITSM ticket; NF vendor or cloud team provisions capacity on request",
                   ["ticketed", "itsm", "on request"]),
                _O(2, "L2 Semi-auto",    "NFVO/Kubernetes operator scales NF pods; human triggers scale job",
                   ["semi-auto", "kubernetes", "human triggers"]),
                _O(3, "L3 Policy-auto",  "Policy-driven auto-scaling: NFVO/MANO scales CNFs based on utilisation thresholds without human action",
                   ["policy-auto", "mano", "without human"]),
                _O(4, "L4 Closed-loop",  "Closed-loop healing: scale-out + traffic re-steering + root-cause isolation executed as atomic operation",
                   ["closed-loop", "atomic", "healing"]),
                _O(5, "L5 Cognitive",    "System learns optimal NF placement and scaling strategies from traffic patterns; zero-touch operations",
                   ["cognitive", "learns", "zero-touch"]),
            ],
        ),
    ]


skill = CoreAutonomySkill()
