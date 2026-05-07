"""
ASTRA Layer 1: Multi-Vendor Normalization Layer (MVNL)
Absorbs vendor-specific data formats into a single canonical data model.
Supports: Ericsson ENM, Nokia NetAct, Samsung OSS, Huawei U2000/iMaster NCE.
CPE side: TR-369 (USP), TR-069 (CWMP fallback), ASTRA Probe JSON.
Spec ref: ASTRA Architecture Spec v1.1, Section 4.2
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class CanonicalUplinkMetrics:
    """Vendor-agnostic uplink metric model. All layers above Layer 1 use this."""
    cpe_id: str
    cell_id: str
    vendor: str
    timestamp_unix: float

    # Radio metrics
    rsrp_dbm: Optional[float] = None
    rsrq_db: Optional[float] = None
    sinr_db: Optional[float] = None
    cqi: Optional[int] = None
    rank_indicator: Optional[int] = None
    power_headroom_db: Optional[float] = None
    ul_mcs: Optional[int] = None
    ul_bler_pct: Optional[float] = None
    ul_throughput_mbps: Optional[float] = None
    dl_throughput_mbps: Optional[float] = None
    timing_advance: Optional[int] = None

    # CPE state (from TR-369 or Probe)
    tx_power_dbm: Optional[float] = None
    thermal_state: Optional[str] = None  # NORMAL | THROTTLING | CRITICAL
    mimo_rank_active: Optional[int] = None
    intelligence_tier: int = 1  # 1=TR-369, 2=Probe, 3=SDK

    # Data quality
    confidence_score: float = 0.5
    reporting_latency_s: float = 30.0
    source_system: str = "unknown"


@dataclass
class CanonicalAlarm:
    """Unified alarm format across all vendors."""
    alarm_id: str
    source_ne: str
    vendor: str
    severity: str          # CRITICAL | MAJOR | MINOR | WARNING
    astra_category: str    # UPLINK_DEGRADATION | THERMAL | INTERFERENCE | CELL_OUTAGE | BACKHAUL
    description: str
    timestamp_unix: float
    raw_code: str = ""
    confidence_score: float = 0.8


# ---------------------------------------------------------------------------
# Vendor adapter functions: translate raw NMS payloads → canonical model
# ---------------------------------------------------------------------------

def normalize_ericsson_pm(raw: dict) -> CanonicalUplinkMetrics:
    """
    Maps Ericsson ENM PM counter names to canonical schema.
    Ericsson key reference (3GPP TS 32.425 + Ericsson ENM PM Dictionary):
      pmRadioThpVolUl → ul_throughput_mbps
      pmRadioThpVolDl → dl_throughput_mbps
      pmCellDownTimeAuto → implicit outage detection
      pmUeUlCqi → cqi
      pmUeRankIndicator → rank_indicator
      pmPhrDistribution → power_headroom_db (bucket center)
    """
    m = raw.get("counters", {})
    ul_vol = m.get("pmRadioThpVolUl", 0)
    dl_vol = m.get("pmRadioThpVolDl", 0)
    interval_s = raw.get("granularity_s", 900)

    metrics = CanonicalUplinkMetrics(
        cpe_id=raw.get("ueId", raw.get("rnti", "unknown")),
        cell_id=raw.get("cellId", ""),
        vendor="Ericsson",
        timestamp_unix=raw.get("ts", time.time()),
        ul_throughput_mbps=round(ul_vol * 8 / interval_s / 1e6, 2) if ul_vol else None,
        dl_throughput_mbps=round(dl_vol * 8 / interval_s / 1e6, 2) if dl_vol else None,
        cqi=m.get("pmUeUlCqi"),
        rank_indicator=m.get("pmUeRankIndicator"),
        power_headroom_db=m.get("pmPhrDistribution"),
        ul_bler_pct=m.get("pmRlcDlPduDrop"),
        rsrp_dbm=m.get("pmRSRPMeas"),
        source_system="Ericsson-ENM",
        reporting_latency_s=interval_s,
    )
    metrics.confidence_score = _score_confidence(metrics, "Ericsson")
    return metrics


def normalize_nokia_pm(raw: dict) -> CanonicalUplinkMetrics:
    """
    Maps Nokia NetAct KPI names to canonical schema.
    Nokia key reference (Nokia NetAct PM Counter Reference):
      UL_USER_THROUGHPUT → ul_throughput_mbps
      DL_USER_THROUGHPUT → dl_throughput_mbps
      PUSCH_SINR_AVG → sinr_db
      CQI_AVG → cqi
      RI_DISTRIBUTION → rank_indicator
      PHR_AVG → power_headroom_db
    """
    kpis = raw.get("kpis", {})
    metrics = CanonicalUplinkMetrics(
        cpe_id=raw.get("ueId", "unknown"),
        cell_id=raw.get("cellDN", ""),
        vendor="Nokia",
        timestamp_unix=raw.get("ts", time.time()),
        ul_throughput_mbps=kpis.get("UL_USER_THROUGHPUT"),
        dl_throughput_mbps=kpis.get("DL_USER_THROUGHPUT"),
        sinr_db=kpis.get("PUSCH_SINR_AVG"),
        cqi=kpis.get("CQI_AVG"),
        rank_indicator=kpis.get("RI_DISTRIBUTION"),
        power_headroom_db=kpis.get("PHR_AVG"),
        ul_bler_pct=kpis.get("PUSCH_BLER"),
        rsrp_dbm=kpis.get("RSRP_AVG"),
        rsrq_db=kpis.get("RSRQ_AVG"),
        source_system="Nokia-NetAct",
        reporting_latency_s=raw.get("granularity_s", 300),
    )
    metrics.confidence_score = _score_confidence(metrics, "Nokia")
    return metrics


def normalize_samsung_pm(raw: dict) -> CanonicalUplinkMetrics:
    """
    Maps Samsung OSS counter names to canonical schema.
    Samsung key reference (Samsung OSS PM Counter Dictionary):
      UL.Throughput.Volume → ul_throughput_mbps
      DL.Throughput.Volume → dl_throughput_mbps
      UL.SINR.Average → sinr_db
      UL.Rank.Average → rank_indicator
      UL.PHR.Average → power_headroom_db
    """
    ctrs = raw.get("counters", {})
    interval_s = raw.get("granularity_s", 300)
    ul_bytes = ctrs.get("UL.Throughput.Volume", 0)
    dl_bytes = ctrs.get("DL.Throughput.Volume", 0)
    metrics = CanonicalUplinkMetrics(
        cpe_id=raw.get("ueIndex", "unknown"),
        cell_id=raw.get("cellId", ""),
        vendor="Samsung",
        timestamp_unix=raw.get("ts", time.time()),
        ul_throughput_mbps=round(ul_bytes * 8 / interval_s / 1e6, 2) if ul_bytes else None,
        dl_throughput_mbps=round(dl_bytes * 8 / interval_s / 1e6, 2) if dl_bytes else None,
        sinr_db=ctrs.get("UL.SINR.Average"),
        rank_indicator=int(round(ctrs.get("UL.Rank.Average", 1))),
        power_headroom_db=ctrs.get("UL.PHR.Average"),
        ul_bler_pct=ctrs.get("UL.BLER"),
        rsrp_dbm=ctrs.get("RSRP.Average"),
        source_system="Samsung-OSS",
        reporting_latency_s=interval_s,
    )
    metrics.confidence_score = _score_confidence(metrics, "Samsung")
    return metrics


def normalize_huawei_pm(raw: dict) -> CanonicalUplinkMetrics:
    """
    Maps Huawei iMaster NCE counter names to canonical schema.
    Huawei key reference (Huawei iMaster NCE Performance Counter Reference):
      VS.PDCP.UL.BitRate → ul_throughput_mbps (in kbps, convert)
      VS.PDCP.DL.BitRate → dl_throughput_mbps
      VS.UL.MCS.Avg → ul_mcs
      VS.PHR.Avg → power_headroom_db
      VS.PUSCH.SINR.Avg → sinr_db
    """
    ctrs = raw.get("counters", {})
    ul_kbps = ctrs.get("VS.PDCP.UL.BitRate", 0)
    dl_kbps = ctrs.get("VS.PDCP.DL.BitRate", 0)
    metrics = CanonicalUplinkMetrics(
        cpe_id=raw.get("ueId", "unknown"),
        cell_id=raw.get("cellId", ""),
        vendor="Huawei",
        timestamp_unix=raw.get("ts", time.time()),
        ul_throughput_mbps=round(ul_kbps / 1000, 2) if ul_kbps else None,
        dl_throughput_mbps=round(dl_kbps / 1000, 2) if dl_kbps else None,
        sinr_db=ctrs.get("VS.PUSCH.SINR.Avg"),
        ul_mcs=ctrs.get("VS.UL.MCS.Avg"),
        power_headroom_db=ctrs.get("VS.PHR.Avg"),
        ul_bler_pct=ctrs.get("VS.PUSCH.BLER"),
        rsrp_dbm=ctrs.get("VS.RSRP.Avg"),
        rsrq_db=ctrs.get("VS.RSRQ.Avg"),
        source_system="Huawei-iMasterNCE",
        reporting_latency_s=raw.get("granularity_s", 300),
    )
    metrics.confidence_score = _score_confidence(metrics, "Huawei")
    return metrics


def normalize_tr369_cpe(raw: dict) -> CanonicalUplinkMetrics:
    """
    Maps TR-369 (USP) Device.Cellular.Interface data model to canonical schema.
    TR-369 TR-181 data model paths:
      Device.Cellular.Interface.{i}.Stats.BytesSent → ul_throughput
      Device.Cellular.Interface.{i}.X_RSRP → rsrp_dbm
      Device.Cellular.Interface.{i}.X_RSRQ → rsrq_db
      Device.Cellular.Interface.{i}.X_SINR → sinr_db
      Device.Cellular.Interface.{i}.TransmitPower → tx_power_dbm
      Device.DeviceInfo.TemperatureStatus.{i}.Value → thermal_state
    This is Tier 1 (standards-based, zero vendor dependency).
    """
    iface = raw.get("Device.Cellular.Interface", {})
    stats = iface.get("Stats", {})
    poll_interval_s = raw.get("poll_interval_s", 30)
    bytes_sent = stats.get("BytesSent", 0)
    bytes_recv = stats.get("BytesReceived", 0)

    temp_c = raw.get("Device.DeviceInfo.TemperatureStatus", {}).get("Value", 40)
    if temp_c >= 80:
        thermal = "CRITICAL"
    elif temp_c >= 70:
        thermal = "THROTTLING"
    else:
        thermal = "NORMAL"

    metrics = CanonicalUplinkMetrics(
        cpe_id=raw.get("cpe_id", "unknown"),
        cell_id=iface.get("X_ServingCellId", ""),
        vendor=raw.get("cpe_vendor", "unknown"),
        timestamp_unix=raw.get("ts", time.time()),
        rsrp_dbm=iface.get("X_RSRP"),
        rsrq_db=iface.get("X_RSRQ"),
        sinr_db=iface.get("X_SINR"),
        tx_power_dbm=iface.get("TransmitPower"),
        thermal_state=thermal,
        ul_throughput_mbps=round(bytes_sent * 8 / poll_interval_s / 1e6, 2) if bytes_sent else None,
        dl_throughput_mbps=round(bytes_recv * 8 / poll_interval_s / 1e6, 2) if bytes_recv else None,
        mimo_rank_active=iface.get("X_MIMORank"),
        intelligence_tier=1,
        source_system="TR-369-USP",
        reporting_latency_s=poll_interval_s,
    )
    metrics.confidence_score = _score_confidence(metrics, "TR-369")
    return metrics


def normalize_probe_data(raw: dict) -> CanonicalUplinkMetrics:
    """
    Maps ASTRA Probe JSON payload to canonical schema.
    Probe provides all of Tier 1 plus LAN-side application metrics.
    Intelligence tier = 2.
    """
    metrics = normalize_tr369_cpe(raw.get("tr369", {}))
    probe = raw.get("probe", {})

    # Probe-enhanced fields override TR-369 where more precise
    if probe.get("sinr_measured"):
        metrics.sinr_db = probe["sinr_measured"]
    if probe.get("ul_throughput_mbps"):
        metrics.ul_throughput_mbps = probe["ul_throughput_mbps"]

    metrics.intelligence_tier = 2
    metrics.source_system = "ASTRA-Probe"
    metrics.reporting_latency_s = probe.get("poll_interval_s", 5)
    metrics.confidence_score = _score_confidence(metrics, "Probe")
    return metrics


# ---------------------------------------------------------------------------
# Conflict resolution + temporal alignment
# ---------------------------------------------------------------------------

def resolve_conflict(m1: CanonicalUplinkMetrics, m2: CanonicalUplinkMetrics) -> CanonicalUplinkMetrics:
    """When two sources report the same CPE, prefer the higher-confidence, higher-tier reading."""
    if m2.intelligence_tier > m1.intelligence_tier:
        return m2
    if m2.confidence_score > m1.confidence_score:
        return m2
    return m1


def align_to_1min(metrics_list: list[CanonicalUplinkMetrics], target_ts: float) -> list[CanonicalUplinkMetrics]:
    """
    Temporal alignment: snap all metrics to the nearest 1-minute boundary.
    Metrics older than 5 minutes are dropped (stale data penalty applied first).
    """
    aligned = []
    minute_boundary = (target_ts // 60) * 60
    for m in metrics_list:
        age_s = target_ts - m.timestamp_unix
        if age_s > 300:
            continue
        # Apply staleness penalty to confidence score
        staleness_factor = max(0.5, 1.0 - (age_s / 600))
        m.confidence_score = round(m.confidence_score * staleness_factor, 3)
        m.timestamp_unix = minute_boundary
        aligned.append(m)
    return aligned


# ---------------------------------------------------------------------------
# Vendor alarm normalization
# ---------------------------------------------------------------------------

_ERICSSON_ALARM_MAP = {
    "CELL_UL_INTERFERENCE_HIGH": ("INTERFERENCE", "MAJOR"),
    "RADIO_LINK_FAILURE": ("UPLINK_DEGRADATION", "CRITICAL"),
    "CELL_UNAVAILABLE": ("CELL_OUTAGE", "CRITICAL"),
    "HIGH_TEMPERATURE": ("THERMAL", "MAJOR"),
    "BACKHAUL_LINK_DEGRADED": ("BACKHAUL", "MAJOR"),
}

_NOKIA_ALARM_MAP = {
    "UL_SINR_BELOW_THRESHOLD": ("UPLINK_DEGRADATION", "MAJOR"),
    "CELL_DOWNTIME": ("CELL_OUTAGE", "CRITICAL"),
    "PUSCH_HIGH_BLER": ("UPLINK_DEGRADATION", "MINOR"),
    "HW_TEMPERATURE_EXCEEDED": ("THERMAL", "MAJOR"),
    "TRANSPORT_DEGRADED": ("BACKHAUL", "MAJOR"),
}

_SAMSUNG_ALARM_MAP = {
    "UL_THROUGHPUT_DEGRADATION": ("UPLINK_DEGRADATION", "MAJOR"),
    "CELL_FAILURE": ("CELL_OUTAGE", "CRITICAL"),
    "HIGH_UL_BLER": ("UPLINK_DEGRADATION", "MINOR"),
    "TEMPERATURE_ALARM": ("THERMAL", "MAJOR"),
}

_HUAWEI_ALARM_MAP = {
    "ALM-25888 UL INTERFERENCE": ("INTERFERENCE", "MAJOR"),
    "ALM-25610 CELL UNAVAILABLE": ("CELL_OUTAGE", "CRITICAL"),
    "ALM-37009 HIGH TEMPERATURE": ("THERMAL", "MAJOR"),
    "ALM-25956 BACKHAUL FAIL": ("BACKHAUL", "CRITICAL"),
}


def normalize_alarm(raw_alarm: dict) -> CanonicalAlarm:
    vendor = raw_alarm.get("vendor", "unknown").lower()
    raw_code = raw_alarm.get("alarm_code", raw_alarm.get("alarmCode", ""))

    alarm_map = {
        "ericsson": _ERICSSON_ALARM_MAP,
        "nokia": _NOKIA_ALARM_MAP,
        "samsung": _SAMSUNG_ALARM_MAP,
        "huawei": _HUAWEI_ALARM_MAP,
    }.get(vendor, {})

    category, severity = alarm_map.get(raw_code, ("UNKNOWN", raw_alarm.get("severity", "MINOR")))

    return CanonicalAlarm(
        alarm_id=raw_alarm.get("alarmId", f"ALM-{int(time.time())}"),
        source_ne=raw_alarm.get("sourceNE", raw_alarm.get("cellId", "unknown")),
        vendor=raw_alarm.get("vendor", "unknown"),
        severity=severity,
        astra_category=category,
        description=raw_alarm.get("description", raw_alarm.get("text", "")),
        timestamp_unix=raw_alarm.get("ts", time.time()),
        raw_code=raw_code,
        confidence_score=0.9 if category != "UNKNOWN" else 0.4,
    )


# ---------------------------------------------------------------------------
# Dispatcher: route raw payload to correct adapter
# ---------------------------------------------------------------------------

ADAPTER_MAP = {
    "ericsson": normalize_ericsson_pm,
    "nokia": normalize_nokia_pm,
    "samsung": normalize_samsung_pm,
    "huawei": normalize_huawei_pm,
    "tr-369": normalize_tr369_cpe,
    "tr369": normalize_tr369_cpe,
    "probe": normalize_probe_data,
}


def normalize(raw: dict) -> CanonicalUplinkMetrics:
    source = raw.get("source", raw.get("vendor", "")).lower()
    adapter = ADAPTER_MAP.get(source)
    if adapter is None:
        raise ValueError(f"MVNL: no adapter registered for source '{source}'")
    return adapter(raw)


# ---------------------------------------------------------------------------
# Internal confidence scoring
# ---------------------------------------------------------------------------

# Base confidence per vendor/source — reflects measurement directness
_BASE_CONFIDENCE = {
    "Probe": 0.96,
    "TR-369": 0.87,
    "Nokia": 0.91,
    "Samsung": 0.88,
    "Ericsson": 0.85,
    "Huawei": 0.83,
}

# Fields that are critical for FWA uplink decisions
_CRITICAL_FIELDS = ["sinr_db", "rank_indicator", "power_headroom_db", "ul_bler_pct"]


def _score_confidence(m: CanonicalUplinkMetrics, source: str) -> float:
    base = _BASE_CONFIDENCE.get(source, 0.6)
    missing = sum(1 for f in _CRITICAL_FIELDS if getattr(m, f) is None)
    penalty = missing * 0.08
    return round(max(0.2, base - penalty), 3)


def metrics_to_dict(m: CanonicalUplinkMetrics) -> dict:
    return asdict(m)
