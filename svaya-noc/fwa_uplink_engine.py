"""
ASTRA Layer 3: Uplink Intelligence Engine
Solves the four core FWA uplink challenges using normalized data from Layer 1.
Tier-aware: adapts decision path based on CPE intelligence tier (1/2/3).
Graduated autonomy: every recommendation is tagged Green / Amber / Red.

Spec ref: ASTRA Architecture Spec v1.1, Section 4.4
"""

from dataclasses import dataclass, field
from typing import Optional
from fwa_mvnl import CanonicalUplinkMetrics

# ---------------------------------------------------------------------------
# Autonomy tier constants
# ---------------------------------------------------------------------------
GREEN = "green"    # Execute autonomously without operator approval
AMBER = "amber"    # Requires NOC approval before execution
RED = "red"        # Requires engineering review + change control

# ---------------------------------------------------------------------------
# Decision output types
# ---------------------------------------------------------------------------

@dataclass
class UplinkDecision:
    cpe_id: str
    module: str                    # Which engine module produced this
    action: str                    # Human-readable action description
    autonomy_tier: str             # GREEN | AMBER | RED
    vendor_command: Optional[dict] = None  # Filled by Layer 4 orchestration
    rationale: str = ""
    confidence: float = 0.0
    rollback_window_min: int = 15
    impact_scope: str = "cpe"      # cpe | cell | multi-site

    def is_auto_eligible(self) -> bool:
        return self.autonomy_tier == GREEN


# ---------------------------------------------------------------------------
# Module 1: Predictive Rank Orchestrator
# Solves: Power Splitting / Rank Dilemma
# Tier 1/2: Network-side prediction via gNB-reported CQI, RI, PHR, BLER
# Spec ref: Section 4.4, Table row "Power Splitting (Rank Dilemma)"
# ---------------------------------------------------------------------------

# SINR thresholds for rank selection (derived from 3GPP link budget analysis)
_RANK2_MIN_SINR = 5.0      # Below this, Rank 2 degrades UL performance
_RANK1_BENEFIT_SINR = 3.0  # Below this, force Rank 1 immediately
_PHR_HEADROOM_MIN = 0.0    # Negative PHR = at power limit; Rank 1 mandatory


def rank_orchestrator(m: CanonicalUplinkMetrics) -> Optional[UplinkDecision]:
    """
    Determines optimal MIMO rank for a CPE's uplink.
    Returns a decision only when the current rank is suboptimal.
    Decision latency at Tier 1/2: ~100ms via RAN API.
    """
    if m.sinr_db is None or m.rank_indicator is None:
        return None

    current_rank = m.mimo_rank_active or m.rank_indicator
    recommended_rank = current_rank
    reason = ""

    if m.sinr_db < _RANK1_BENEFIT_SINR:
        recommended_rank = 1
        reason = (
            f"SINR {m.sinr_db:.1f}dB is below rank-1 benefit threshold ({_RANK1_BENEFIT_SINR}dB). "
            "Rank 2 is adding interference overhead without MIMO gain."
        )
    elif m.sinr_db < _RANK2_MIN_SINR and current_rank == 2:
        recommended_rank = 1
        reason = (
            f"SINR {m.sinr_db:.1f}dB below rank-2 minimum ({_RANK2_MIN_SINR}dB). "
            "Switching to Rank 1 recovers uplink throughput."
        )
    elif m.power_headroom_db is not None and m.power_headroom_db < _PHR_HEADROOM_MIN and current_rank == 2:
        recommended_rank = 1
        reason = (
            f"PHR {m.power_headroom_db:.1f}dB — CPE at power limit. "
            "Rank 1 reduces power spreading across layers."
        )
    elif m.ul_bler_pct is not None and m.ul_bler_pct > 10.0 and current_rank == 2:
        recommended_rank = 1
        reason = (
            f"UL BLER {m.ul_bler_pct:.1f}% exceeds 10% threshold. "
            "High error rate with Rank 2 suggests channel cannot support spatial multiplexing."
        )

    if recommended_rank == current_rank:
        return None  # No action needed

    # Tier 1/2: command is sent to gNB via RAN NMS API
    vendor_cmd = {
        "interface": f"RAN-NMS-API-{m.vendor}",
        "operation": "set_ue_rank",
        "parameters": {
            "ue_id": m.cpe_id,
            "cell_id": m.cell_id,
            "rank": recommended_rank,
        },
    }

    return UplinkDecision(
        cpe_id=m.cpe_id,
        module="PredictiveRankOrchestrator",
        action=f"Change MIMO rank {current_rank}→{recommended_rank} via {m.vendor} RAN API",
        autonomy_tier=GREEN,
        vendor_command=vendor_cmd,
        rationale=reason,
        confidence=m.confidence_score,
        rollback_window_min=15,
        impact_scope="cpe",
    )


# ---------------------------------------------------------------------------
# Module 2: CPE Thermal Guardian
# Solves: High PAPR / Thermal Stress
# Tier 1: Reactive (TR-369 thermal polling → Tx power reduction)
# Tier 2: Predictive (Probe detects consumption trend before threshold)
# Spec ref: Section 4.4, Table row "High PAPR / Thermal Stress"
# ---------------------------------------------------------------------------

_THERMAL_THROTTLE_TX_REDUCTION_DBM = 3.0  # Reduce Tx power by 3dB when throttling


def thermal_guardian(m: CanonicalUplinkMetrics) -> Optional[UplinkDecision]:
    """
    Detects CPE thermal stress and triggers gNB-side Tx power cap reduction.
    Tier 1: reactive (responds when THROTTLING detected via TR-369).
    Tier 2: predictive (probe detects thermal trend before threshold hit).
    """
    if not m.thermal_state or m.thermal_state == "NORMAL":
        return None
    if m.tx_power_dbm is None:
        return None

    new_tx = round(m.tx_power_dbm - _THERMAL_THROTTLE_TX_REDUCTION_DBM, 1)
    tier_note = "reactive" if m.intelligence_tier == 1 else "predictive"

    vendor_cmd = {
        "interface": f"RAN-NMS-API-{m.vendor}",
        "operation": "set_ue_max_tx_power",
        "parameters": {
            "ue_id": m.cpe_id,
            "cell_id": m.cell_id,
            "max_tx_power_dbm": new_tx,
        },
    }

    return UplinkDecision(
        cpe_id=m.cpe_id,
        module="CPEThermalGuardian",
        action=(
            f"Reduce gNB-assigned max Tx power {m.tx_power_dbm}dBm → {new_tx}dBm "
            f"({tier_note}, thermal_state={m.thermal_state})"
        ),
        autonomy_tier=GREEN,
        vendor_command=vendor_cmd,
        rationale=(
            f"CPE thermal state is {m.thermal_state}. "
            "Reducing assigned Tx power headroom to relieve PAPR-driven heating. "
            "ASTRA will monitor thermal recovery over 15-minute window."
        ),
        confidence=m.confidence_score,
        rollback_window_min=15,
        impact_scope="cpe",
    )


# ---------------------------------------------------------------------------
# Module 3: Cross-Band UL/DL Decoupler
# Solves: UL/DL Coverage Asymmetry (Silent Zone households)
# Tier-independent: entirely network-side decision.
# Requires engineering review (RED) — fundamental architecture change.
# Spec ref: Section 4.4, Table row "UL/DL Coverage Asymmetry"
# ---------------------------------------------------------------------------

_SILENT_ZONE_PHR_THRESHOLD = -5.0     # PHR below -5dB = at absolute power limit
_SILENT_ZONE_RSRP_THRESHOLD = -110.0  # RSRP below -110dBm = cell-edge scenario
_SILENT_ZONE_CLUSTER_MIN = 3          # Need >= 3 CPEs in silent zone to trigger


def detect_silent_zone_cluster(metrics_list: list[CanonicalUplinkMetrics]) -> Optional[UplinkDecision]:
    """
    Identifies a cluster of cell-edge CPEs that are uplink-constrained
    (Silent Zone) and recommends Cross-Band UL/DL Decoupling via RIC.
    Groups CPEs by cell_id and checks for Silent Zone cluster size.
    Returns one RED decision per cell where cluster threshold is met.
    """
    from collections import defaultdict
    cells: dict[str, list[CanonicalUplinkMetrics]] = defaultdict(list)
    for m in metrics_list:
        if m.power_headroom_db is not None and m.rsrp_dbm is not None:
            if m.power_headroom_db < _SILENT_ZONE_PHR_THRESHOLD and m.rsrp_dbm < _SILENT_ZONE_RSRP_THRESHOLD:
                cells[m.cell_id].append(m)

    decisions = []
    for cell_id, silent_cpes in cells.items():
        if len(silent_cpes) < _SILENT_ZONE_CLUSTER_MIN:
            continue
        cpe_ids = [m.cpe_id for m in silent_cpes]
        avg_phr = sum(m.power_headroom_db for m in silent_cpes) / len(silent_cpes)
        avg_rsrp = sum(m.rsrp_dbm for m in silent_cpes) / len(silent_cpes)

        decisions.append(UplinkDecision(
            cpe_id=",".join(cpe_ids[:5]),
            module="CrossBandULDLDecoupler",
            action=(
                f"Recommend UL/DL decoupling for cell {cell_id}: "
                f"route UL traffic of {len(silent_cpes)} Silent Zone CPEs to lower-freq band via RIC"
            ),
            autonomy_tier=RED,
            vendor_command={
                "interface": "RIC-E2-xApp",
                "operation": "ul_dl_decoupling_recommendation",
                "parameters": {
                    "cell_id": cell_id,
                    "affected_cpe_count": len(silent_cpes),
                    "avg_phr_db": round(avg_phr, 1),
                    "avg_rsrp_dbm": round(avg_rsrp, 1),
                },
            },
            rationale=(
                f"{len(silent_cpes)} CPEs on cell {cell_id} are in Silent Zone "
                f"(avg PHR={avg_phr:.1f}dB, avg RSRP={avg_rsrp:.1f}dBm). "
                "UL/DL decoupling routes uplink to a lower-frequency band with better UL coverage. "
                "Requires engineering review — this is a fundamental band architecture change."
            ),
            confidence=min(m.confidence_score for m in silent_cpes),
            rollback_window_min=60,
            impact_scope="cell",
        ))
    return decisions


# ---------------------------------------------------------------------------
# Module 4: Interference Nulling Coordinator
# Solves: Static Inter-Cell Interference
# Tier-independent: uses TypeDB interference graph.
# Requires NOC approval (AMBER) — affects multiple households.
# Spec ref: Section 4.4, Table row "Static Inter-Cell Interference"
# ---------------------------------------------------------------------------

@dataclass
class InterferencePair:
    interferer_cpe: str
    victim_cpe: str
    cell_interferer: str
    cell_victim: str
    interference_db: float
    persistence_hours: float
    vendor_interferer: str
    vendor_victim: str


def interference_nulling_coordinator(pairs: list[InterferencePair]) -> list[UplinkDecision]:
    """
    Recommends beam nulling CoMP coordination for persistent static interference pairs.
    Persistence > 24h triggers AMBER recommendation for NOC approval.
    Cross-site (different cell IDs) requires multi-vendor coordination.
    """
    decisions = []
    for pair in pairs:
        if pair.persistence_hours < 24.0:
            continue

        cross_site = pair.cell_interferer != pair.cell_victim
        cross_vendor = pair.vendor_interferer != pair.vendor_victim
        autonomy = AMBER

        action_detail = (
            f"Coordinate beam nulling CoMP between {pair.cell_interferer} and {pair.cell_victim} "
            f"to null interference from CPE {pair.interferer_cpe} onto CPE {pair.victim_cpe}"
        )

        vendor_cmd = {
            "interface": "CoMP-Coordination-API",
            "operation": "beam_null_request",
            "parameters": {
                "interferer_cell": pair.cell_interferer,
                "victim_cell": pair.cell_victim,
                "interferer_cpe": pair.interferer_cpe,
                "victim_cpe": pair.victim_cpe,
                "target_null_direction": "uplink",
                "cross_vendor": cross_vendor,
            },
        }

        decisions.append(UplinkDecision(
            cpe_id=pair.victim_cpe,
            module="InterferenceNullingCoordinator",
            action=action_detail,
            autonomy_tier=autonomy,
            vendor_command=vendor_cmd,
            rationale=(
                f"Static interference {pair.interference_db:.1f}dB persisting for "
                f"{pair.persistence_hours:.0f}h between CPE {pair.interferer_cpe} "
                f"and CPE {pair.victim_cpe}. FWA CPEs are static — this pattern will not "
                "self-resolve. CoMP beam nulling eliminates it permanently. "
                + ("Cross-vendor coordination required. " if cross_vendor else "")
                + "NOC approval required before execution."
            ),
            confidence=0.92,
            rollback_window_min=30,
            impact_scope="multi-site" if cross_site else "cell",
        ))

    return decisions


# ---------------------------------------------------------------------------
# Top-level engine: run all modules against a batch of normalized metrics
# ---------------------------------------------------------------------------

def run_uplink_engine(
    metrics_list: list[CanonicalUplinkMetrics],
    interference_pairs: list[InterferencePair] | None = None,
) -> dict:
    """
    Runs all four uplink intelligence modules against the normalized metric batch.
    Returns a summary dict with decisions, autonomy breakdown, and execution plan.
    """
    decisions: list[UplinkDecision] = []

    for m in metrics_list:
        rank_dec = rank_orchestrator(m)
        if rank_dec:
            decisions.append(rank_dec)

        thermal_dec = thermal_guardian(m)
        if thermal_dec:
            decisions.append(thermal_dec)

    # Silent zone detection operates on the full batch
    silent_zone_decisions = detect_silent_zone_cluster(metrics_list)
    if silent_zone_decisions:
        decisions.extend(silent_zone_decisions)

    # Interference nulling
    if interference_pairs:
        nulling_decisions = interference_nulling_coordinator(interference_pairs)
        decisions.extend(nulling_decisions)

    green = [d for d in decisions if d.autonomy_tier == GREEN]
    amber = [d for d in decisions if d.autonomy_tier == AMBER]
    red = [d for d in decisions if d.autonomy_tier == RED]

    return {
        "total_decisions": len(decisions),
        "green_auto": len(green),
        "amber_noc": len(amber),
        "red_engineering": len(red),
        "decisions": [_decision_to_dict(d) for d in decisions],
        "execution_plan": {
            "auto_execute": [_decision_to_dict(d) for d in green],
            "pending_noc_approval": [_decision_to_dict(d) for d in amber],
            "pending_engineering_review": [_decision_to_dict(d) for d in red],
        },
    }


def _decision_to_dict(d: UplinkDecision) -> dict:
    return {
        "cpe_id": d.cpe_id,
        "module": d.module,
        "action": d.action,
        "autonomy_tier": d.autonomy_tier,
        "rationale": d.rationale,
        "confidence": d.confidence,
        "rollback_window_min": d.rollback_window_min,
        "impact_scope": d.impact_scope,
        "vendor_command": d.vendor_command,
    }
