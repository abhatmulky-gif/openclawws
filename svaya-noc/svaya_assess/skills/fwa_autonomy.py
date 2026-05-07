"""
FWA Network Autonomy Assessment skill.
Covers all five IG1252 cognitive dimensions across two FWA sub-scenarios.
Aligned with TM Forum IG1218 v2.2.0 / IG1252 v1.2.0.
"""

from .base import BaseSkill, SubScenario, Criterion, CriterionOption

_O = CriterionOption  # shorthand


class FWAAutonomySkill(BaseSkill):

    id          = "fwa_autonomy"
    name        = "FWA Network Autonomy Assessment"
    description = (
        "Benchmarks your Fixed Wireless Access network operations against the "
        "TM Forum IG1252 cognitive dimension framework. Covers Intent, Awareness, "
        "Analysis, Decision, and Execution — scored L0–L5."
    )
    icon = "📡"

    scenarios = [
        SubScenario(
            id="single_vendor",
            name="Single-vendor FWA",
            description="All RAN and CPE from one vendor",
            weight=0.35,
        ),
        SubScenario(
            id="multi_vendor",
            name="Multi-vendor FWA",
            description="Mixed RAN (e.g., Ericsson + Nokia) or mixed CPE fleet",
            weight=0.65,
        ),
    ]

    criteria = [

        # ---------------------------------------------------------------- #
        # INTENT                                                            #
        # ---------------------------------------------------------------- #

        Criterion(
            id="intent_translation",
            name="Intent Translation",
            cognitive_activity="Intent",
            weight=0.15,
            question=(
                "How does your system translate business objectives (QoE targets, "
                "SLAs, energy limits) into network parameters?"
            ),
            evidence_prompt=(
                "Briefly describe how your system translates a QoE target "
                "into CPE or RAN configuration — e.g., manual CLI, template system, "
                "intent API."
            ),
            options=[
                _O(0, "L0 Manual",       "No translation; engineer issues CLI commands per CPE/cell",
                   ["manual", "cli", "ssh", "no automation"]),
                _O(1, "L1 Script-aided", "Script-assisted bulk changes; engineer reviews each batch",
                   ["script", "batch", "engineer review", "approval"]),
                _O(2, "L2 Templates",    "Template-based config push with approval gate before execution",
                   ["template", "approval", "push", "review"]),
                _O(3, "L3 Policy-based", "Automated parameter mapping from objectives to vendor-specific settings",
                   ["automated", "policy", "mapping", "vendor"]),
                _O(4, "L4 Closed-loop",  "Continuous closed-loop: objective breach auto-triggers reconfiguration",
                   ["closed-loop", "automatic", "no human", "continuous"]),
                _O(5, "L5 Self-learning","Self-learning engine pre-adapts config before subscriber impact",
                   ["self-learning", "predictive", "AI", "autonomous"]),
            ],
        ),

        Criterion(
            id="intent_fulfillment",
            name="Intent Fulfilment Evaluation",
            cognitive_activity="Intent",
            weight=0.10,
            question=(
                "How does your system evaluate whether QoE/SLA intent has been fulfilled?"
            ),
            options=[
                _O(0, "L0 Manual",      "No evaluation; performance issues discovered via complaints",
                   ["complaint", "no evaluation", "manual"]),
                _O(1, "L1 Periodic",    "Periodic manual KPI reviews against SLA documents",
                   ["periodic", "manual", "weekly", "monthly"]),
                _O(2, "L2 Dashboard",   "Dashboard with threshold alerts; operator reviews breaches",
                   ["dashboard", "alert", "threshold", "review"]),
                _O(3, "L3 Auto-report", "System auto-generates intent fulfilment report per subscriber segment",
                   ["auto", "report", "fulfillment", "segment"]),
                _O(4, "L4 Continuous",  "Continuous scoring; intent fulfilment drives further closed-loop action",
                   ["continuous", "closed-loop", "drive", "action"]),
                _O(5, "L5 Predictive",  "System predicts fulfilment risk and pre-emptively adjusts",
                   ["predict", "pre-emptive", "self-adjust"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # AWARENESS                                                         #
        # ---------------------------------------------------------------- #

        Criterion(
            id="awareness_telemetry",
            name="CPE Telemetry Coverage",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "What is your real-time telemetry coverage across your FWA CPE fleet?"
            ),
            evidence_prompt=(
                "What protocol provides CPE telemetry — TR-369 USP, TR-069, SNMP, "
                "proprietary? What is the polling/streaming interval?"
            ),
            options=[
                _O(0, "L0 None",        "No real-time data; customer complaints or drive tests only",
                   ["no data", "complaint", "drive test"]),
                _O(1, "L1 SNMP/TR-069", "SNMP traps or TR-069 polling; <50% fleet; 15-min granularity",
                   ["snmp", "tr-069", "polling", "15 min"]),
                _O(2, "L2 Streaming",   "TR-069/TR-369 streaming; 5-min granularity; most fleet covered",
                   ["streaming", "5 min", "tr-369", "most fleet"]),
                _O(3, "L3 Full fleet",  "TR-369 USP + NMS PM counters; 1-min; full fleet; cross-domain corr.",
                   ["full fleet", "1 min", "cross-domain", "correlation"]),
                _O(4, "L4 Sub-minute",  "Sub-minute telemetry correlated across CPE + RAN + backhaul",
                   ["sub-minute", "correlated", "backhaul", "ran"]),
                _O(5, "L5 Digital twin","Predictive awareness via digital twin before network events occur",
                   ["digital twin", "predictive", "before impact"]),
            ],
        ),

        Criterion(
            id="awareness_correlation",
            name="Cross-Domain Correlation",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "How do you correlate CPE performance with RAN conditions "
                "and backhaul health?"
            ),
            options=[
                _O(0, "L0 Manual",     "Manual correlation by engineers; ad-hoc and slow",
                   ["manual", "engineer", "ad-hoc"]),
                _O(1, "L1 Siloed",     "Separate dashboards per domain; operator manually correlates",
                   ["separate", "siloed", "dashboards", "manually"]),
                _O(2, "L2 Basic",      "Basic cross-domain view in NMS; limited automation",
                   ["basic", "cross-domain", "view", "nms"]),
                _O(3, "L3 Automated",  "Automated cross-domain correlation; root-cause hypotheses generated",
                   ["automated", "correlation", "root cause", "hypothesis"]),
                _O(4, "L4 Real-time",  "Real-time topology-aware correlation across CPE + RAN + backhaul",
                   ["real-time", "topology", "topology-aware"]),
                _O(5, "L5 Self-learning","Self-learning model discovers new failure patterns autonomously",
                   ["self-learning", "new patterns", "autonomous"]),
            ],
        ),

        Criterion(
            id="awareness_detection",
            name="Subscriber Impact Detection Speed",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "How quickly do you become aware of subscriber-impacting degradation?"
            ),
            options=[
                _O(0, "L0 >24h",       "Customer complaint driven; often 24h+ after impact begins",
                   ["24h", "complaint", "customer call"]),
                _O(1, "L1 15 min",     "NMS alarm within 15 min; NOC analyst must review",
                   ["15 min", "nms", "analyst", "review"]),
                _O(2, "L2 5 min",      "Automated alert within 5 min with estimated subscriber count",
                   ["5 min", "automated alert", "subscriber count"]),
                _O(3, "L3 <1 min",     "Pre-emptive detection <1 min; subscribers not yet impacted",
                   ["1 min", "pre-emptive", "before impact"]),
                _O(4, "L4 Predictive", "Degradation predicted minutes ahead; remediation pre-positioned",
                   ["predictive", "minutes ahead", "remediation"]),
                _O(5, "L5 Self-heal",  "Predicted hours ahead; network self-heals, subscribers never aware",
                   ["hours ahead", "self-heal", "never aware"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # ANALYSIS                                                          #
        # ---------------------------------------------------------------- #

        Criterion(
            id="analysis_rca",
            name="Root Cause Analysis",
            cognitive_activity="Analysis",
            weight=0.10,
            question=(
                "How do you diagnose the root cause of FWA performance degradation?"
            ),
            evidence_prompt=(
                "Describe a recent example: how was root cause identified, "
                "and how long did it take?"
            ),
            options=[
                _O(0, "L0 Manual",     "Engineer manually inspects logs; diagnosis takes hours–days",
                   ["manual", "logs", "hours", "days"]),
                _O(1, "L1 Rule-based", "Rule-based alarm correlation; engineer picks from checklist",
                   ["rule-based", "checklist", "engineer picks"]),
                _O(2, "L2 Pattern",    "Pattern-matching system suggests probable causes; engineer validates",
                   ["pattern", "suggests", "validates"]),
                _O(3, "L3 AI-assisted","AI-assisted RCA 70–85% confidence; auditable reasoning",
                   ["ai", "70%", "auditable", "reasoning"]),
                _O(4, "L4 Deterministic","Deterministic reasoning traces root cause in <60s with full audit trail",
                   ["deterministic", "60s", "audit trail", "full"]),
                _O(5, "L5 Proactive",  "Proactive analysis resolves root cause before first subscriber impact",
                   ["proactive", "before impact", "self-resolves"]),
            ],
        ),

        Criterion(
            id="analysis_alarm_storms",
            name="Alarm Storm Management",
            cognitive_activity="Analysis",
            weight=0.10,
            question=(
                "How do you manage alarm storms (mass simultaneous events "
                "from a single root cause)?"
            ),
            options=[
                _O(0, "L0 Overwhelmed","Each alarm handled individually; NOC overwhelmed",
                   ["overwhelmed", "individual", "flood"]),
                _O(1, "L1 Dedup",      "Basic deduplication; engineers manually group alarms",
                   ["dedup", "manual", "group"]),
                _O(2, "L2 Grouping",   "Automated grouping by topology; root-cause hypothesis to NOC",
                   ["grouped", "automated", "topology", "hypothesis"]),
                _O(3, "L3 Suppressed", "Single root-cause alarm + subscriber count surfaced to NOC",
                   ["single alarm", "suppressed", "subscriber count"]),
                _O(4, "L4 Zero storm", "Zero alarm storm to NOC; root cause identified and actioned first",
                   ["zero", "no storm", "actioned first"]),
                _O(5, "L5 Pre-emptive","Root cause resolved before any alarms fire",
                   ["pre-emptive", "before alarms", "self-resolves"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # DECISION                                                          #
        # ---------------------------------------------------------------- #

        Criterion(
            id="decision_approval",
            name="Decision Governance",
            cognitive_activity="Decision",
            weight=0.15,
            question=(
                "How are optimisation actions decided and approved in your operations?"
            ),
            evidence_prompt=(
                "Describe your current approval workflow for a routine "
                "change — e.g., who approves, what is the SLA for approval?"
            ),
            options=[
                _O(0, "L0 Manual",     "Senior engineer makes all decisions; no automation",
                   ["manual", "senior engineer", "no automation"]),
                _O(1, "L1 Recommend",  "NOC analyst selects from recommended actions and approves each",
                   ["recommend", "select", "approve"]),
                _O(2, "L2 Risk-gated", "Automation proposes with risk score; team lead approves",
                   ["risk score", "team lead", "proposes"]),
                _O(3, "L3 Tiered",     "Tiered: low-risk auto (green), medium NOC (amber), high engineering (red)",
                   ["tiered", "green", "amber", "red", "graduated"]),
                _O(4, "L4 Policy-bounded","System executes within pre-approved policy envelope; humans monitor",
                   ["policy", "envelope", "autonomous", "monitor"]),
                _O(5, "L5 Self-adapting","Fully autonomous; adapts own decision boundaries from outcomes",
                   ["self-adapting", "fully autonomous", "boundaries"]),
            ],
        ),

        Criterion(
            id="decision_rollback",
            name="Rollback Capability",
            cognitive_activity="Decision",
            weight=0.10,
            question=(
                "How is rollback handled when an automated change degrades performance?"
            ),
            options=[
                _O(0, "L0 Manual",     "Manual rollback; requires engineering effort",
                   ["manual rollback", "engineer"]),
                _O(1, "L1 Scripts",    "Rollback scripts available but manually triggered",
                   ["scripts", "manual trigger"]),
                _O(2, "L2 Auto",       "Automated rollback triggered by threshold breach",
                   ["automated", "threshold", "breach"]),
                _O(3, "L3 With RCA",   "Instant rollback plus root-cause analysis of the failure",
                   ["instant", "root cause", "analysis"]),
                _O(4, "L4 Predictive", "Predictive rollback before threshold breach",
                   ["predictive", "before breach"]),
                _O(5, "L5 No rollback","Digital twin validates changes; no rollbacks needed",
                   ["digital twin", "no rollback", "pre-validated"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # EXECUTION                                                         #
        # ---------------------------------------------------------------- #

        Criterion(
            id="execution_config",
            name="Configuration Execution",
            cognitive_activity="Execution",
            weight=0.10,
            question=(
                "How are configuration changes pushed to your FWA CPE fleet?"
            ),
            evidence_prompt=(
                "What is your primary method for fleet-wide configuration changes? "
                "Approximate fleet size and typical change frequency?"
            ),
            options=[
                _O(0, "L0 CLI",        "Manual CLI per CPE via SSH; engineer per device",
                   ["cli", "ssh", "manual", "per device"]),
                _O(1, "L1 Scripts",    "Scripted mass change; engineer reviews list and approves",
                   ["scripted", "mass change", "engineer reviews"]),
                _O(2, "L2 NMS push",   "Template-based push via NMS; automated for standard ops",
                   ["template", "nms", "automated standard"]),
                _O(3, "L3 Vendor-agnostic","Intent-driven config push; vendor translation automatic",
                   ["vendor-agnostic", "intent", "translation automatic"]),
                _O(4, "L4 Continuous", "Continuous autonomous config optimisation; no human intervention",
                   ["continuous", "autonomous", "no human"]),
                _O(5, "L5 Self-config","CPEs receive abstract policy; no per-device orchestration",
                   ["self-config", "abstract policy", "no orchestration"]),
            ],
        ),

        Criterion(
            id="execution_zerotouch",
            name="Zero-Touch CPE Activation",
            cognitive_activity="Execution",
            weight=0.10,
            scenario_specific=False,  # same answer regardless of vendor split
            question=(
                "How do you activate new FWA CPEs — full truck roll vs. zero-touch?"
            ),
            options=[
                _O(0, "L0 Truck roll", "Full truck roll; engineer configures each CPE on-site",
                   ["truck roll", "on-site", "engineer"]),
                _O(1, "L1 Minimal",    "Basic provisioning automated; beam optimisation done on-site",
                   ["minimal", "basic provisioning", "beam on-site"]),
                _O(2, "L2 Remote",     "Remote provisioning for most CPEs; some site visits remain",
                   ["remote", "most cpes", "some visits"]),
                _O(3, "L3 Zero-touch", "Zero-touch: CPE auto-provisions via TR-369 in <60 seconds",
                   ["zero-touch", "tr-369", "auto", "60 seconds"]),
                _O(4, "L4 Predictive", "Optimal config pre-computed before CPE is installed",
                   ["pre-computed", "predictive", "before install"]),
                _O(5, "L5 Self-install","CPE learns from neighbours; zero engineer interaction",
                   ["self-install", "neighbours", "zero interaction"]),
            ],
        ),
    ]


skill = FWAAutonomySkill()
