"""
Transport and Backhaul Network Automation Assessment skill.
Covers autonomous operation across microwave backhaul, fiber/OTN, and IP/MPLS + SD-WAN.
Sub-scenarios reflect a typical MNO transport estate.
Aligned with TM Forum IG1252 cognitive dimension methodology.
"""

from .base import BaseSkill, SubScenario, Criterion, CriterionOption

_O = CriterionOption


class TransportAutonomySkill(BaseSkill):

    id          = "transport_autonomy"
    name        = "Transport & Backhaul Automation"
    description = (
        "Assesses autonomous operation capability across your transport network — "
        "microwave/mmWave backhaul, fiber/OTN (SDH, WDM, OTN switching), "
        "and IP/MPLS packet transport with SD-WAN overlay. "
        "Covers SLA intent translation, topology awareness, fault isolation, "
        "path protection decisions, and zero-touch circuit provisioning."
    )
    icon = "🔗"

    scenarios = [
        SubScenario(
            id="microwave",
            name="Microwave / mmWave Backhaul",
            description="PtP and PtMP microwave; E-band and mmWave for 5G fronthaul/backhaul",
            weight=0.30,
        ),
        SubScenario(
            id="fiber_otn",
            name="Fiber / OTN",
            description="SDH/SONET legacy, WDM/DWDM optical, OTN switching (ODU0–ODU4)",
            weight=0.35,
        ),
        SubScenario(
            id="ip_mpls",
            name="IP/MPLS + SD-WAN",
            description="IP/MPLS packet core, Carrier Ethernet, SD-WAN overlay and VPN services",
            weight=0.35,
        ),
    ]

    criteria = [

        # ---------------------------------------------------------------- #
        # INTENT                                                            #
        # ---------------------------------------------------------------- #

        Criterion(
            id="transport_intent_sla",
            name="Transport SLA Intent Translation",
            cognitive_activity="Intent",
            weight=0.15,
            question=(
                "How does your system translate RAN and core transport SLA requirements "
                "(latency, jitter, availability, bandwidth) into transport path configuration "
                "across microwave, OTN, and IP/MPLS layers?"
            ),
            evidence_prompt=(
                "Describe how a new 5G gNB backhaul requirement (e.g., <1 ms latency, "
                "10 Gbps bandwidth, 99.999% availability) gets turned into transport "
                "configuration — manual, scripted, or automated?"
            ),
            options=[
                _O(0, "L0 Manual",        "Transport engineers manually design and configure each link per site",
                   ["manual", "engineer", "per site"]),
                _O(1, "L1 Templates",     "Standard link templates applied per site type; engineer selects and configures",
                   ["templates", "engineer selects"]),
                _O(2, "L2 Orchestrated",  "Transport SDN/NMS provisions paths from templates; human triggers and approves each circuit",
                   ["orchestrated", "sdn", "human approves"]),
                _O(3, "L3 Intent-driven", "Policy engine translates SLA intent to optimal path across all transport layers automatically",
                   ["intent-driven", "policy engine", "all layers", "automatic"]),
                _O(4, "L4 Closed-loop",   "Closed-loop: SLA breach auto-triggers path re-optimisation or capacity increase without approval",
                   ["closed-loop", "sla breach", "re-optimisation"]),
                _O(5, "L5 Cognitive",     "System learns optimal transport topology from traffic patterns and SLA outcomes; self-evolves network design",
                   ["cognitive", "self-evolves", "topology"]),
            ],
        ),

        Criterion(
            id="transport_intent_lifecycle",
            name="Transport Circuit Lifecycle Management",
            cognitive_activity="Intent",
            weight=0.10,
            scenario_specific=False,
            question=(
                "How does your system manage the full lifecycle of transport circuits — "
                "from capacity planning and provisioning through to decommission when "
                "a RAN site is sunset or migrated?"
            ),
            options=[
                _O(0, "L0 Manual",     "Circuit lifecycle managed entirely manually via work orders and ITSM tickets",
                   ["manual", "work orders", "itsm"]),
                _O(1, "L1 Inventory",  "Transport inventory system tracks circuits; provisioning and decommission are separate manual processes",
                   ["inventory", "manual", "separate"]),
                _O(2, "L2 Semi-auto",  "Orchestrator automates provisioning steps; decommission and reclamation still manual",
                   ["semi-auto", "provisioning automated", "decommission manual"]),
                _O(3, "L3 Automated",  "Automated end-to-end lifecycle: provision on RAN site activation, decommission on site sunset",
                   ["automated", "end-to-end", "site activation", "site sunset"]),
                _O(4, "L4 Optimising", "System continuously optimises circuit inventory, reclaims unused capacity, and re-purposes bandwidth",
                   ["optimising", "reclaims", "re-purposes"]),
                _O(5, "L5 Autonomous", "Fully autonomous transport lifecycle aligned to business intents; no human involvement in routine operations",
                   ["autonomous", "no human", "business intent"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # AWARENESS                                                         #
        # ---------------------------------------------------------------- #

        Criterion(
            id="transport_awareness_topology",
            name="Multi-Layer Topology Awareness",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "How does your system maintain real-time awareness of transport topology "
                "across microwave, OTN, and IP/MPLS layers — including physical link state, "
                "logical path routing, and cross-layer dependencies?"
            ),
            evidence_prompt=(
                "Do you have a unified transport topology model? How are cross-layer "
                "dependencies (e.g., which IP LSPs run over which OTN ODUs over which fibers) tracked?"
            ),
            options=[
                _O(0, "L0 Siloed",      "Separate NMS per transport domain; no unified topology view",
                   ["siloed", "separate nms", "no unified"]),
                _O(1, "L1 Manual-map",  "Topology diagrams maintained manually in Visio/Lucidchart; updated periodically",
                   ["manual", "visio", "diagrams"]),
                _O(2, "L2 Partial",     "Unified NMS covers IP/MPLS and microwave; OTN/optical layer is separate",
                   ["partial", "ip mpls microwave", "optical separate"]),
                _O(3, "L3 Multi-layer", "Single transport management platform with correlated multi-layer topology (physical/OTN/IP)",
                   ["multi-layer", "single platform", "correlated"]),
                _O(4, "L4 Real-time",   "Real-time topology with live link state, utilisation, and cross-layer dependency tracking",
                   ["real-time", "live link state", "cross-layer"]),
                _O(5, "L5 Predictive",  "Digital twin of full transport network; predicts topology changes from planned events before they occur",
                   ["digital twin", "predictive", "planned events"]),
            ],
        ),

        Criterion(
            id="transport_awareness_perf",
            name="Transport Performance Monitoring",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "How does your system monitor transport performance — microwave RSL/throughput, "
                "OTN BER/FEC, IP/MPLS delay/jitter/packet-loss — and correlate "
                "degradation to RAN or core service impact?"
            ),
            options=[
                _O(0, "L0 Passive",     "Alarms received from NMS; no continuous performance monitoring or SLA tracking",
                   ["passive", "alarms only", "no continuous"]),
                _O(1, "L1 Polling",     "PM stats polled every 15 minutes per domain; thresholds trigger NOC alerts",
                   ["polling", "15 minutes", "threshold alerts"]),
                _O(2, "L2 Near-real",   "Near-real-time transport KPIs in unified dashboard; correlation to RAN impact is manual",
                   ["near-real", "unified dashboard", "manual correlation"]),
                _O(3, "L3 Correlated",  "Automated correlation between transport degradation and RAN/core service KPI impact",
                   ["automated correlation", "transport", "ran core impact"]),
                _O(4, "L4 Streaming",   "Sub-minute streaming metrics across all layers with automated anomaly detection and baselining",
                   ["streaming", "sub-minute", "anomaly detection"]),
                _O(5, "L5 Predictive",  "Predicts transport degradation from environmental/traffic trends before service impact occurs",
                   ["predictive", "environmental", "before impact"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # ANALYSIS                                                          #
        # ---------------------------------------------------------------- #

        Criterion(
            id="transport_analysis_rca",
            name="Transport Fault Isolation and RCA",
            cognitive_activity="Analysis",
            weight=0.15,
            question=(
                "How do you isolate root cause of transport faults — e.g., a fiber cut "
                "causing multiple OTN ODU failures causing IP RSVP reroutes causing "
                "multiple RAN site degradations?"
            ),
            evidence_prompt=(
                "Describe a recent transport fault cascade: how many layers were affected, "
                "how long to isolate root cause, and what tooling was used?"
            ),
            options=[
                _O(0, "L0 Manual",      "Each domain team investigates independently; cross-layer root cause coordination is ad-hoc",
                   ["manual", "ad-hoc", "domain teams"]),
                _O(1, "L1 Bridge",      "NOC bridge call assembles optical, IP, and RAN teams; root cause determined collaboratively",
                   ["bridge call", "multiple teams", "collaborative"]),
                _O(2, "L2 Tool-aided",  "Alarm correlation tool groups related alarms by probable cause; engineer traces causal chain",
                   ["tool-aided", "alarm correlation", "engineer traces"]),
                _O(3, "L3 AI-RCA",      "AI engine identifies cross-layer root cause from physical → OTN → IP → RAN alarm chain in <5 minutes",
                   ["ai", "5 minutes", "cross-layer", "alarm chain"]),
                _O(4, "L4 Deterministic","Deterministic reasoning isolates root cause to a specific fiber span or NE port in <60 seconds",
                   ["deterministic", "60 seconds", "fiber span", "port"]),
                _O(5, "L5 Proactive",   "Transport fault predicted from RSL/BER trends; remediation pre-positioned before service impact",
                   ["proactive", "predicted", "pre-positioned"]),
            ],
        ),

        Criterion(
            id="transport_analysis_capacity",
            name="Transport Capacity Planning",
            cognitive_activity="Analysis",
            weight=0.10,
            question=(
                "How does your system analyse transport capacity utilisation trends "
                "and plan for 5G backhaul growth, including E-band and fiber capacity evolution?"
            ),
            options=[
                _O(0, "L0 Manual",     "Annual capacity planning by transport planning team using link utilisation reports",
                   ["manual", "annual", "planning team"]),
                _O(1, "L1 Reports",    "Monthly utilisation reports per domain; team escalates high-utilisation links",
                   ["monthly", "utilisation", "per domain"]),
                _O(2, "L2 Analytics",  "Analytics tracks capacity growth; team manually estimates 5G backhaul demand impact",
                   ["analytics", "manual estimation", "5g impact"]),
                _O(3, "L3 Auto-model", "System automatically models 5G rollout backhaul demand and generates capacity upgrade recommendations",
                   ["auto-model", "5g rollout", "recommendations"]),
                _O(4, "L4 Continuous", "Continuous capacity optimisation: re-routes traffic, reclaims headroom, auto-orders capacity expansion",
                   ["continuous", "re-routes", "reclaims", "auto-orders"]),
                _O(5, "L5 Predictive", "Predicts capacity exhaustion 6–12 months out per link; drives autonomous infrastructure investment",
                   ["predictive", "6 months", "infrastructure investment"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # DECISION                                                          #
        # ---------------------------------------------------------------- #

        Criterion(
            id="transport_decision_protection",
            name="Path Protection and Rerouting Decisions",
            cognitive_activity="Decision",
            weight=0.15,
            question=(
                "How does your system decide on path protection switching and traffic "
                "rerouting when transport failures occur — OTN MSP/SNCP, "
                "MPLS FRR, SD-WAN path selection?"
            ),
            options=[
                _O(0, "L0 Static",      "Static protection groups configured; no dynamic rerouting beyond vendor APS/FRR",
                   ["static", "aps", "no dynamic"]),
                _O(1, "L1 Manual",      "Alarms trigger NOC investigation; engineers manually re-route affected traffic",
                   ["manual", "noc", "engineers re-route"]),
                _O(2, "L2 Automated-prot","Hardware-level protection (OTN MSP, MPLS FRR) switches automatically; higher-level re-optimisation is manual",
                   ["hardware protection", "frr", "msp", "re-optimisation manual"]),
                _O(3, "L3 Policy-driven","Policy engine decides optimal re-route across layers considering SLA, capacity, and cost constraints",
                   ["policy-driven", "optimal re-route", "sla cost"]),
                _O(4, "L4 Closed-loop", "Closed-loop rerouting: system detects, re-routes, verifies restoration, and reports — fully automated",
                   ["closed-loop", "detects", "verifies restoration"]),
                _O(5, "L5 Predictive",  "Predicts link failure from degradation trends; pre-positions traffic before failure occurs",
                   ["predictive", "pre-positions", "before failure"]),
            ],
        ),

        Criterion(
            id="transport_decision_optimisation",
            name="Traffic Engineering and Optimisation",
            cognitive_activity="Decision",
            weight=0.10,
            question=(
                "How does your system perform traffic engineering — MPLS TE LSP optimisation, "
                "SD-WAN path selection, microwave adaptive modulation — "
                "to balance load and optimise transport cost?"
            ),
            options=[
                _O(0, "L0 Static",      "Static TE configurations; no dynamic optimisation",
                   ["static", "no optimisation"]),
                _O(1, "L1 Manual",      "Engineers periodically review utilisation and adjust TE weights or LSP paths manually",
                   ["manual", "periodic", "engineer adjusts"]),
                _O(2, "L2 Rule-based",  "Rule-based TE adjustments triggered by utilisation thresholds; human approves major changes",
                   ["rule-based", "threshold", "human approves"]),
                _O(3, "L3 Automated",   "Automated traffic engineering: system continuously optimises LSP paths and SD-WAN routes without human input",
                   ["automated", "continuously", "without human"]),
                _O(4, "L4 Multi-layer", "Cross-layer optimisation: IP/MPLS TE decisions consider OTN and microwave layer state simultaneously",
                   ["multi-layer", "cross-layer", "simultaneously"]),
                _O(5, "L5 Cognitive",   "AI-driven TE learns traffic patterns and proactively optimises topology for cost, capacity, and resilience",
                   ["cognitive", "ai-driven", "proactively"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # EXECUTION                                                         #
        # ---------------------------------------------------------------- #

        Criterion(
            id="transport_execution_provisioning",
            name="Zero-Touch Circuit Provisioning",
            cognitive_activity="Execution",
            weight=0.15,
            question=(
                "How are new transport circuits provisioned — microwave link commissioning, "
                "OTN ODU cross-connects, MPLS L3VPN/L2VPN, SD-WAN tunnels — "
                "when a new RAN site or service is launched?"
            ),
            evidence_prompt=(
                "Describe the last new site backhaul provisioning: which layers were "
                "involved, how many teams, and how long from order to live service?"
            ),
            options=[
                _O(0, "L0 Manual",       "Each layer provisioned manually by specialist team; typical lead time 4–8 weeks",
                   ["manual", "specialist", "4-8 weeks"]),
                _O(1, "L1 Ticketed",     "ITSM-driven workflow triggers separate teams per layer; manual handoffs between steps",
                   ["ticketed", "itsm", "manual handoffs"]),
                _O(2, "L2 Semi-auto",    "Orchestrator automates individual layer provisioning; cross-layer sequencing requires human coordination",
                   ["semi-auto", "orchestrator", "cross-layer manual"]),
                _O(3, "L3 Multi-layer",  "Single provisioning workflow configures all layers (optical → OTN → IP → microwave) from one service order",
                   ["multi-layer", "single workflow", "one service order"]),
                _O(4, "L4 Zero-touch",   "Fully zero-touch: service order triggers end-to-end provisioning across all layers without human action",
                   ["zero-touch", "end-to-end", "no human action"]),
                _O(5, "L5 Self-provisioning","Network self-provisions transport resources in anticipation of demand — before the service order is raised",
                   ["self-provisioning", "anticipation", "before order"]),
            ],
        ),
    ]


skill = TransportAutonomySkill()
