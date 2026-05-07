"""
RAN Energy Efficiency Optimization Assessment skill.
Modelled on the TM Forum ANLET methodology as demonstrated in the
Huawei / AIS RAN Energy Efficiency Optimization assessment document.

Three sub-scenarios (matching TM Forum IG1218 energy management use-case):
  1. Intra-RAT intra-frequency multi-site energy saving    (20%)
  2. Intra-RAT inter-frequency multi-site energy saving    (40%)
  3. Inter-RAT multi-site energy saving / carrier shutdown (40%)

Nine criteria across five cognitive activities, weighted per IG1252.
"""

from .base import BaseSkill, SubScenario, Criterion, CriterionOption

_O = CriterionOption


class EnergyEfficiencySkill(BaseSkill):

    id          = "energy_efficiency"
    name        = "RAN Energy Efficiency Optimization"
    description = (
        "Assesses your RAN's autonomous energy saving capability across three "
        "sub-scenarios: intra-RAT intra-frequency, intra-RAT inter-frequency, "
        "and inter-RAT multi-site carrier shutdown. Directly aligned with the "
        "TM Forum AN energy management use-case and IG1252 evaluation methodology."
    )
    icon = "⚡"

    scenarios = [
        SubScenario(
            id="intra_freq",
            name="Intra-RAT Intra-Frequency",
            description="Energy saving within same RAT and frequency band (e.g., NR n78 → n78)",
            weight=0.20,
        ),
        SubScenario(
            id="inter_freq",
            name="Intra-RAT Inter-Frequency",
            description="Energy saving across frequencies within same RAT (e.g., NR n78 + n41)",
            weight=0.40,
        ),
        SubScenario(
            id="inter_rat",
            name="Inter-RAT / Carrier Shutdown",
            description="Cross-RAT energy saving and LTE/NR carrier shutdown (LNR)",
            weight=0.40,
        ),
    ]

    criteria = [

        # ---------------------------------------------------------------- #
        # INTENT                                                            #
        # ---------------------------------------------------------------- #

        Criterion(
            id="energy_intent_translation",
            name="Energy Saving Intent Translation",
            cognitive_activity="Intent",
            weight=0.15,
            question=(
                "How does your system translate the RAN energy saving intent "
                "(targets and performance constraints) into energy saving control information?"
            ),
            evidence_prompt=(
                "Describe how energy saving targets are set and applied — "
                "e.g., does an operator define a watt reduction target or a "
                "performance floor, and how does the system act on it?"
            ),
            options=[
                _O(0, "L0 Manual",
                   "Energy saving parameters manually defined per cell by RF engineers",
                   ["manual", "engineer", "per cell"]),
                _O(1, "L1 Script-rules",
                   "System applies predefined rule-based energy saving scripts; "
                   "human manually selects candidate cells and confirms parameters",
                   ["rule-based", "manual selection", "confirm"]),
                _O(2, "L2 Template",
                   "System generates control information from templates; "
                   "engineer reviews and approves candidate cell list",
                   ["template", "engineer reviews", "approval"]),
                _O(3, "L3 Auto-candidate",
                   "System automatically selects candidate cells and generates "
                   "energy saving control information based on intent; "
                   "human confirms the output",
                   ["auto-select", "intent", "human confirms"]),
                _O(4, "L4 Fully-auto",
                   "System automatically selects candidates and generates control "
                   "information based on intent, without human intervention; "
                   "can explore optimal energy gain vs. performance trade-off",
                   ["fully automatic", "no human", "explore", "optimal"]),
                _O(5, "L5 Self-optimising",
                   "System continuously adapts energy saving targets and candidate "
                   "selection based on observed outcomes; self-calibrating",
                   ["self-optimising", "continuous", "adapt targets"]),
            ],
        ),

        Criterion(
            id="energy_intent_fulfillment",
            name="Energy Saving Intent Fulfilment Evaluation",
            cognitive_activity="Intent",
            weight=0.10,
            question=(
                "How does your system evaluate whether the RAN energy saving "
                "intent has been fulfilled — including performance constraint adherence?"
            ),
            options=[
                _O(0, "L0 Manual",
                   "Intent fulfilment manually evaluated by engineers post-hoc",
                   ["manual", "post-hoc", "engineer"]),
                _O(1, "L1 Periodic report",
                   "Periodic reports show energy savings achieved vs. baseline; human reviews",
                   ["periodic", "report", "baseline", "human"]),
                _O(2, "L2 Auto alert",
                   "System flags when performance constraints (throughput/coverage) are breached; "
                   "human evaluates intent status",
                   ["alert", "constraint", "human evaluates"]),
                _O(3, "L3 Auto-report",
                   "System automatically evaluates and generates an intent fulfilment report "
                   "including target status; human confirms evaluation result",
                   ["auto-report", "target status", "human confirms"]),
                _O(4, "L4 Continuous",
                   "System continuously evaluates and generates intent fulfilment reports; "
                   "drives closed-loop re-optimisation without human confirmation",
                   ["continuous", "closed-loop", "no confirmation"]),
                _O(5, "L5 Predictive",
                   "System predicts intent fulfilment risk and pre-emptively adjusts "
                   "energy saving parameters",
                   ["predictive", "pre-emptive", "risk"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # AWARENESS                                                         #
        # ---------------------------------------------------------------- #

        Criterion(
            id="energy_data_collection",
            name="Energy Saving Data Collection",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "How does your system collect RAN energy saving related information "
                "(PM counters, CHR/MR data, power consumption measurements)?"
            ),
            evidence_prompt=(
                "What data sources feed your energy optimisation system? "
                "e.g., ENM PM exports, NetAct KPIs, AMOS scripting, "
                "smart meter integration."
            ),
            options=[
                _O(0, "L0 Manual",
                   "Data collected manually from NMS by engineers; ad-hoc",
                   ["manual", "ad-hoc", "engineer"]),
                _O(1, "L1 Scheduled",
                   "Scheduled data collection based on predefined rules; "
                   "human intervention for data quality checks",
                   ["scheduled", "predefined", "human quality"]),
                _O(2, "L2 Continuous+human",
                   "System continuously collects energy data but requires human "
                   "intervention for quality validation",
                   ["continuous", "human validation"]),
                _O(3, "L3 Continuous",
                   "System continuously and automatically collects all required "
                   "energy saving data without human intervention",
                   ["continuous", "automatic", "no human"]),
                _O(4, "L4 Multi-source",
                   "Continuous collection across all sources (PM counters, CHR, "
                   "smart meters, weather/load) with automated quality assurance",
                   ["multi-source", "smart meter", "quality assured"]),
                _O(5, "L5 Predictive",
                   "System identifies and ingests new data sources autonomously "
                   "to improve energy saving models",
                   ["new sources", "autonomous ingestion"]),
            ],
        ),

        Criterion(
            id="energy_issue_identification",
            name="Energy Saving Issue Identification",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "How does your system identify energy saving issues — "
                "i.e., cells or sites with untapped saving potential or "
                "excessive energy consumption?"
            ),
            options=[
                _O(0, "L0 Manual",
                   "Engineers manually identify cells with savings potential through log analysis",
                   ["manual", "log analysis"]),
                _O(1, "L1 Rule-based",
                   "Rule-based threshold comparison flags high-consumption cells; human reviews",
                   ["threshold", "flag", "human review"]),
                _O(2, "L2 Pattern",
                   "System identifies energy issues using historical pattern analysis; "
                   "generates candidate list for human approval",
                   ["pattern", "historical", "candidate list"]),
                _O(3, "L3 AI model",
                   "System uses AI models to identify insufficient energy saving issues "
                   "including CHR-based overlapping coverage analysis",
                   ["ai model", "chr", "overlapping coverage"]),
                _O(4, "L4 Comprehensive",
                   "System continuously identifies all types of energy saving issues "
                   "(insufficient saving, performance risk, new opportunities) without human input",
                   ["comprehensive", "all types", "continuous", "no human"]),
                _O(5, "L5 Predictive",
                   "System predicts future energy saving opportunities based on "
                   "load forecasts before issues become apparent",
                   ["predict future", "load forecast"]),
            ],
        ),

        Criterion(
            id="energy_traffic_prediction",
            name="Traffic & Performance Prediction",
            cognitive_activity="Awareness",
            weight=0.10,
            question=(
                "How does your system predict traffic load and network performance "
                "to support energy saving solution selection?"
            ),
            options=[
                _O(0, "L0 None",
                   "No prediction; energy saving parameters set statically or by schedule",
                   ["no prediction", "static", "schedule"]),
                _O(1, "L1 Historical",
                   "Historical traffic profiles used to set time-of-day energy saving windows",
                   ["historical", "time-of-day", "window"]),
                _O(2, "L2 Simple model",
                   "Simple regression model predicts next-hour traffic; used to pre-configure thresholds",
                   ["regression", "next-hour", "threshold"]),
                _O(3, "L3 AI prediction",
                   "AI model predicts minute-level traffic and KPI changes "
                   "(throughput, coverage, energy) to evaluate saving solutions before deployment",
                   ["ai", "minute-level", "evaluate before"]),
                _O(4, "L4 Multi-KPI",
                   "System predicts multi-KPI impact (DL throughput, coverage ratio, "
                   "energy consumption) per candidate solution with confidence scoring",
                   ["multi-kpi", "candidate", "confidence"]),
                _O(5, "L5 Scenario sim",
                   "Digital twin runs full scenario simulation before any energy saving "
                   "measure is activated in the live network",
                   ["digital twin", "simulation", "before activation"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # ANALYSIS                                                          #
        # ---------------------------------------------------------------- #

        Criterion(
            id="energy_rca",
            name="Energy Issue Demarcation & Root Cause",
            cognitive_activity="Analysis",
            weight=0.10,
            question=(
                "How does your system demarcate energy saving issues from "
                "performance issues and analyse root cause?"
            ),
            options=[
                _O(0, "L0 Manual",
                   "Engineers manually investigate and separate energy vs. performance issues",
                   ["manual", "investigate"]),
                _O(1, "L1 Rule-based",
                   "Rule-based demarcation; human determines root cause from flagged metrics",
                   ["rule-based", "flagged", "human determines"]),
                _O(2, "L2 Automated flag",
                   "System automatically demarcates issues; provides possible root causes "
                   "for human confirmation",
                   ["automated demarcation", "possible causes", "human confirms"]),
                _O(3, "L3 AI RCA",
                   "System automatically demarcates and identifies root cause using AI; "
                   "e.g. coverage simulation to distinguish energy vs. performance",
                   ["ai rca", "coverage simulation", "automatic"]),
                _O(4, "L4 Full auto",
                   "System fully demarcates and root-causes all energy saving issues "
                   "without human intervention; confidence-scored output",
                   ["full auto", "no human", "confidence"]),
                _O(5, "L5 Proactive",
                   "System identifies root causes of future issues before they manifest",
                   ["proactive", "future", "before manifest"]),
            ],
        ),

        Criterion(
            id="energy_solution_generation",
            name="Energy Saving Solution Generation",
            cognitive_activity="Analysis",
            weight=0.15,
            question=(
                "How does your system generate candidate RAN energy saving solutions "
                "to resolve identified issues?"
            ),
            evidence_prompt=(
                "Describe what types of solutions your system generates — "
                "e.g., power reduction, carrier shutdown, antenna tilt, "
                "sleep mode scheduling, parameter tuning."
            ),
            options=[
                _O(0, "L0 Manual",
                   "Solutions manually designed by RF engineers per cell",
                   ["manual", "rf engineer"]),
                _O(1, "L1 Templates",
                   "Pre-defined solution templates applied by engineers",
                   ["template", "pre-defined", "applied"]),
                _O(2, "L2 Rule-based",
                   "System generates solutions based on rules; engineer selects and confirms",
                   ["rule-based", "generate", "engineer selects"]),
                _O(3, "L3 AI generation",
                   "System generates multiple candidate solutions using AI; "
                   "includes simulation of energy savings and KPI impact per candidate",
                   ["ai generation", "multiple candidates", "simulation"]),
                _O(4, "L4 Optimised",
                   "System generates and scores candidate solutions with multi-objective "
                   "optimisation (energy gain vs. throughput vs. coverage trade-off)",
                   ["multi-objective", "optimisation", "trade-off", "scored"]),
                _O(5, "L5 Exploratory",
                   "System autonomously explores and discovers novel energy saving "
                   "strategies beyond pre-defined solution types",
                   ["novel", "exploratory", "beyond pre-defined"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # DECISION                                                          #
        # ---------------------------------------------------------------- #

        Criterion(
            id="energy_decision",
            name="Solution Evaluation & Decision Making",
            cognitive_activity="Decision",
            weight=0.10,
            question=(
                "How does your system evaluate candidate energy saving solutions "
                "and decide which to implement?"
            ),
            options=[
                _O(0, "L0 Manual",
                   "Solutions evaluated and selected based on manual expertise",
                   ["manual", "expertise"]),
                _O(1, "L1 Rule-based",
                   "System evaluates solutions based on predefined rules; human selects",
                   ["rule-based", "predefined", "human selects"]),
                _O(2, "L2 AI + human",
                   "System evaluates solutions using AI simulation and selects best, "
                   "but requires human confirmation before execution",
                   ["ai simulation", "human confirmation"]),
                _O(3, "L3 Auto-select",
                   "System intelligently evaluates and selects best solution "
                   "without human intervention; fitness-based ranking",
                   ["auto-select", "fitness", "no human"]),
                _O(4, "L4 Continuous",
                   "System continuously evaluates solutions in live context, "
                   "self-adjusts selection based on real-time feedback",
                   ["continuous", "self-adjust", "real-time"]),
                _O(5, "L5 Multi-stakeholder",
                   "System balances energy, performance, cost, and regulatory "
                   "objectives autonomously across all cell sites",
                   ["multi-stakeholder", "regulatory", "all sites"]),
            ],
        ),

        # ---------------------------------------------------------------- #
        # EXECUTION                                                         #
        # ---------------------------------------------------------------- #

        Criterion(
            id="energy_execution",
            name="Solution Implementation",
            cognitive_activity="Execution",
            weight=0.10,
            question=(
                "How does your system implement the selected RAN energy "
                "saving solution?"
            ),
            evidence_prompt=(
                "Describe the implementation path — e.g., NMS GUI click, "
                "automated parameter push, TR-069 config, AMOS script execution."
            ),
            options=[
                _O(0, "L0 Manual",
                   "Solution implementation entirely manual; engineer applies changes per cell",
                   ["manual", "engineer", "per cell"]),
                _O(1, "L1 Script",
                   "Implementation via manually triggered scripts after human approval",
                   ["script", "manually triggered", "approval"]),
                _O(2, "L2 Supervised",
                   "System implements solution automatically but under human supervision; "
                   "human can intervene at any point",
                   ["supervised", "human can intervene"]),
                _O(3, "L3 Auto",
                   "System implements solution automatically without human supervision; "
                   "with automated verification and rollback",
                   ["automatic", "no supervision", "rollback"]),
                _O(4, "L4 Continuous",
                   "System continuously implements, monitors, and adjusts energy saving "
                   "parameters in real time across all sites",
                   ["continuous", "real time", "all sites"]),
                _O(5, "L5 Closed-loop",
                   "Fully closed-loop execution: implementation, monitoring, and "
                   "re-optimisation are completely autonomous",
                   ["closed-loop", "fully autonomous", "re-optimisation"]),
            ],
        ),
    ]


skill = EnergyEfficiencySkill()
