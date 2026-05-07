"""
ASTRA FWA TypeDB Client
Single interface for all knowledge-graph operations.
Replaces Neo4j entirely. Uses TypeDB's Datalog reasoning engine
for deterministic safety-critical decisions (no LLM in the decision loop).

All queries are TypeQL. Inference is enabled on read transactions so
that rule-derived facts (autonomy-tier, status = "isolated", etc.)
are returned alongside explicitly stored facts.

Spec ref: ASTRA Architecture Spec v1.1, Sections 4.3–4.4
"""

import time
from contextlib import contextmanager
from typing import Optional

from typedb.driver import TypeDB, SessionType, TransactionType

# Attempt to import TypeDBOptions for inference control.
# In TypeDB 3.x inference is always on in READ transactions;
# in TypeDB 2.x it must be enabled explicitly via options.
try:
    from typedb.driver import TypeDBOptions as _TypeDBOptions
    _INFER_OPTS = _TypeDBOptions()
    _INFER_OPTS.infer = True
except Exception:
    _INFER_OPTS = None

TYPEDB_HOST = "127.0.0.1:1729"
DB_NAME = "astra_fwa"

# Import the canonical metric model from MVNL so we can convert TypeDB rows → metrics
try:
    from fwa_mvnl import CanonicalUplinkMetrics
    from fwa_uplink_engine import InterferencePair
except ImportError:
    # Graceful fallback if called from a different working directory
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from fwa_mvnl import CanonicalUplinkMetrics
    from fwa_uplink_engine import InterferencePair


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

@contextmanager
def _read_tx():
    """Open a read transaction with inference enabled."""
    with TypeDB.core_driver(TYPEDB_HOST) as driver:
        with driver.session(DB_NAME, SessionType.DATA) as session:
            if _INFER_OPTS is not None:
                with session.transaction(TransactionType.READ, _INFER_OPTS) as tx:
                    yield tx
            else:
                with session.transaction(TransactionType.READ) as tx:
                    yield tx


@contextmanager
def _write_tx():
    """Open a write transaction (inference not relevant for writes)."""
    with TypeDB.core_driver(TYPEDB_HOST) as driver:
        with driver.session(DB_NAME, SessionType.DATA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                yield tx
                tx.commit()


def _v(concept_map, key: str):
    """Extract a native Python value from a ConceptMap attribute variable."""
    c = concept_map.get(key)
    if c is None:
        return None
    attr = c.as_attribute()
    if hasattr(attr, "get_value"):
        return attr.get_value()
    # TypeDB 3.x uses .value property
    return getattr(attr, "value", None)


def _consume(iterator) -> list:
    """Eagerly consume a TypeDB result iterator into a list while tx is open."""
    return list(iterator)


# ---------------------------------------------------------------------------
# 1. Uplink state upsert (called on every CPE telemetry poll)
# ---------------------------------------------------------------------------

def insert_cpe_telemetry(m: CanonicalUplinkMetrics) -> None:
    """
    Upsert a CPE's uplink state in TypeDB.
    Pattern: delete existing uplink-state (cascades uplink-binding), insert fresh.
    If CPE entity does not exist, insert it first.
    """
    with TypeDB.core_driver(TYPEDB_HOST) as driver:
        with driver.session(DB_NAME, SessionType.DATA) as session:

            # Step 1: Check if CPE entity exists
            with session.transaction(TransactionType.READ) as tx:
                existing = _consume(tx.query.get(
                    f'match $cpe isa cpe-device, has name "{m.cpe_id}"; get $cpe;'
                ))

            # Step 2: Insert CPE if new
            if not existing:
                with session.transaction(TransactionType.WRITE) as tx:
                    tx.query.insert(
                        f'insert $cpe isa cpe-device, '
                        f'has name "{m.cpe_id}", '
                        f'has vendor "{m.vendor}", '
                        f'has intelligence-tier {m.intelligence_tier}, '
                        f'has status "online";'
                    )
                    tx.commit()

            # Step 3: In one WRITE transaction — delete stale uplink state + insert fresh
            with session.transaction(TransactionType.WRITE) as tx:
                # Safe delete (no-op if no prior state)
                tx.query.delete(
                    f'match '
                    f'$cpe isa cpe-device, has name "{m.cpe_id}"; '
                    f'$ul isa uplink-state; '
                    f'(subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding; '
                    f'delete $ul isa uplink-state;'
                )

                # Build TypeQL attribute clause from non-null fields
                attrs = _build_uplink_attrs(m)

                tx.query.insert(
                    f'match $cpe isa cpe-device, has name "{m.cpe_id}"; '
                    f'insert '
                    f'$ul isa uplink-state, {attrs}; '
                    f'(subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding;'
                )
                tx.commit()


def _build_uplink_attrs(m: CanonicalUplinkMetrics) -> str:
    parts = []
    _add = lambda attr, val: parts.append(f"has {attr} {val}") if val is not None else None
    _add("sinr-db", m.sinr_db)
    _add("mimo-rank", m.mimo_rank_active)
    _add("ul-mcs", m.ul_mcs)
    _add("ul-bler-pct", m.ul_bler_pct)
    _add("ul-throughput-mbps", m.ul_throughput_mbps)
    _add("dl-throughput-mbps", m.dl_throughput_mbps)
    _add("power-headroom-db", m.power_headroom_db)
    _add("rsrp-dbm", m.rsrp_dbm)
    _add("rsrq-db", m.rsrq_db)
    _add("cqi", m.cqi)
    _add("rank-indicator", m.rank_indicator)
    _add("tx-power-dbm", m.tx_power_dbm)
    if m.thermal_state:
        parts.append(f'has thermal-state "{m.thermal_state}"')
    parts.append(f"has data-source-tier {m.intelligence_tier}")
    parts.append(f"has confidence-score {m.confidence_score}")
    parts.append(f'has timestamp "{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}"')
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# 2. Topology context query (replaces Neo4j MATCH traversals)
# ---------------------------------------------------------------------------

def get_topology_context(cpe_ids: list[str]) -> tuple[list[str], list[str]]:
    """
    Returns (topology_edges, nms_systems) for the given CPE IDs.
    Traverses: CPE → cell-coverage → cell-site → backhaul-connection → backhaul-node
               cell-site → nms-management → ran-nms
    """
    if not cpe_ids:
        return [], []

    edges = []
    nms_systems = []

    id_filter = " or ".join(f'$n == "{cid}"' for cid in cpe_ids)

    tql = f"""
        match
          $cpe isa cpe-device, has name $n;
          {{ {id_filter} }};
          (serving-cell: $cell, served-cpe: $cpe) isa cell-coverage;
          $cell has name $cell_name, has vendor $cell_vendor;
          (managing-system: $nms, managed-element: $cell) isa nms-management;
          $nms has name $nms_name, has vendor $nms_vendor;
        get $n, $cell_name, $cell_vendor, $nms_name, $nms_vendor;
    """
    with _read_tx() as tx:
        for cm in _consume(tx.query.get(tql)):
            cpe_id = _v(cm, "n")
            cell = _v(cm, "cell_name")
            cell_v = _v(cm, "cell_vendor")
            nms = _v(cm, "nms_name")
            nms_v = _v(cm, "nms_vendor")
            edges.append(f"{cpe_id} —cell-coverage→ {cell} ({cell_v})")
            edges.append(f"{cell} —nms-management→ {nms} ({nms_v})")
            nms_systems.append(nms)

    # Backhaul chain: cell → ASR → Core
    bh_tql = f"""
        match
          $cpe isa cpe-device, has name $n;
          {{ {id_filter} }};
          (serving-cell: $cell, served-cpe: $cpe) isa cell-coverage;
          $cell has name $cell_name;
          (radio-access: $cell, transport: $asr) isa backhaul-connection;
          $asr has name $asr_name, has node-type $asr_type;
          (downstream-node: $asr, upstream-node: $core) isa aggregation-link;
          $core has name $core_name;
        get $cell_name, $asr_name, $asr_type, $core_name;
    """
    with _read_tx() as tx:
        for cm in _consume(tx.query.get(bh_tql)):
            cell = _v(cm, "cell_name")
            asr = _v(cm, "asr_name")
            asr_type = _v(cm, "asr_type")
            core = _v(cm, "core_name")
            edges.append(f"{cell} —backhaul→ {asr} ({asr_type})")
            edges.append(f"{asr} —aggregation→ {core}")

    # Interference neighbours
    intf_tql = f"""
        match
          $cpe isa cpe-device, has name $n;
          {{ {id_filter} }};
          (interferer: $other, victim: $cpe) isa interference-link;
          $other has name $other_name;
        get $n, $other_name;
    """
    with _read_tx() as tx:
        for cm in _consume(tx.query.get(intf_tql)):
            edges.append(f"{_v(cm, 'other_name')} —interferes-with→ {_v(cm, 'n')}")

    return list(dict.fromkeys(edges)), list(dict.fromkeys(nms_systems))


# ---------------------------------------------------------------------------
# 3. Interference pairs (replaces Neo4j INTERFERES_WITH query)
# ---------------------------------------------------------------------------

def get_interference_pairs(min_persistence_h: float = 0.0) -> list[InterferencePair]:
    """
    Returns all static CPE-to-CPE interference pairs from the TypeDB graph.
    Interference attributes (level, persistence, direction) live on the relation itself.
    """
    tql = f"""
        match
          $a isa cpe-device, has name $a_name, has vendor $a_vendor;
          $b isa cpe-device, has name $b_name, has vendor $b_vendor;
          $link (interferer: $a, victim: $b) isa interference-link,
            has persistence-hours $h,
            has interference-level-db $idb;
          $h > {min_persistence_h};
          (serving-cell: $cell_a, served-cpe: $a) isa cell-coverage;
          $cell_a has name $cell_a_name;
          (serving-cell: $cell_b, served-cpe: $b) isa cell-coverage;
          $cell_b has name $cell_b_name;
        get $a_name, $b_name, $a_vendor, $b_vendor, $h, $idb, $cell_a_name, $cell_b_name;
    """
    pairs = []
    with _read_tx() as tx:
        for cm in _consume(tx.query.get(tql)):
            pairs.append(InterferencePair(
                interferer_cpe=_v(cm, "a_name"),
                victim_cpe=_v(cm, "b_name"),
                cell_interferer=_v(cm, "cell_a_name"),
                cell_victim=_v(cm, "cell_b_name"),
                interference_db=float(_v(cm, "idb") or 0),
                persistence_hours=float(_v(cm, "h") or 0),
                vendor_interferer=_v(cm, "a_vendor"),
                vendor_victim=_v(cm, "b_vendor"),
            ))
    return pairs


# ---------------------------------------------------------------------------
# 4. Datalog inference decisions
# Queries TypeDB with inference ON → returns pre-reasoned autonomy decisions.
# This is the RDFox-equivalent: deterministic rule results, no LLM.
# ---------------------------------------------------------------------------

def get_inferred_decisions() -> dict:
    """
    Queries TypeDB with inference enabled.
    Returns decisions grouped by autonomy tier — derived entirely by Datalog rules.
    CPE decisions: uplink-rank-downgrade, phr-exhausted, thermal-stress, silent-zone, cell-isolation, churn-audit.
    Interference decisions: persistent-interference-noc-escalation.
    """
    green = []
    amber = []
    red = []
    isolated = []
    audit = []

    # CPE-level inferred autonomy tiers
    cpe_tql = """
        match
          $cpe isa cpe-device, has name $cpe_name, has autonomy-tier $tier;
          (subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding;
          $ul has sinr-db $sinr, has mimo-rank $rank,
               has ul-bler-pct $bler, has ul-throughput-mbps $ul_tput;
          (serving-cell: $cell, served-cpe: $cpe) isa cell-coverage;
          $cell has name $cell_name, has vendor $cell_vendor;
        get $cpe_name, $tier, $sinr, $rank, $bler, $ul_tput, $cell_name, $cell_vendor;
    """
    with _read_tx() as tx:
        for cm in _consume(tx.query.get(cpe_tql)):
            tier = _v(cm, "tier")
            entry = {
                "cpe_id": _v(cm, "cpe_name"),
                "sinr_db": _v(cm, "sinr"),
                "mimo_rank": _v(cm, "rank"),
                "ul_bler_pct": _v(cm, "bler"),
                "ul_throughput_mbps": _v(cm, "ul_tput"),
                "cell": _v(cm, "cell_name"),
                "cell_vendor": _v(cm, "cell_vendor"),
                "source": "Datalog inference",
            }
            if tier == "green-auto":
                green.append(entry)
            elif tier == "amber-noc":
                amber.append(entry)
            elif tier == "red-engineering":
                red.append(entry)

    # Isolation cascade (inferred status = "isolated")
    iso_tql = """
        match
          $cpe isa cpe-device, has name $cpe_name, has status "isolated";
          (serving-cell: $cell, served-cpe: $cpe) isa cell-coverage;
          $cell has name $cell_name, has status $cell_status;
        get $cpe_name, $cell_name, $cell_status;
    """
    with _read_tx() as tx:
        for cm in _consume(tx.query.get(iso_tql)):
            isolated.append({
                "cpe_id": _v(cm, "cpe_name"),
                "offline_cell": _v(cm, "cell_name"),
                "cell_status": _v(cm, "cell_status"),
                "source": "Datalog inference (cell-site-isolation-cascade)",
            })

    # Uplink audit flag (inferred status = "uplink-audit-required")
    audit_tql = """
        match
          $cpe isa cpe-device, has name $cpe_name, has status "uplink-audit-required";
          (subscriber: $hh, access-node: $cpe) isa household-service;
          $hh has address $addr, has churn-risk-score $score;
        get $cpe_name, $addr, $score;
    """
    with _read_tx() as tx:
        for cm in _consume(tx.query.get(audit_tql)):
            audit.append({
                "cpe_id": _v(cm, "cpe_name"),
                "household_address": _v(cm, "addr"),
                "churn_risk_score": _v(cm, "score"),
                "source": "Datalog inference (high-churn-uplink-audit)",
            })

    # Interference-link level decisions (amber-noc from persistent-interference rule)
    intf_tql = """
        match
          $a isa cpe-device, has name $a_name;
          $b isa cpe-device, has name $b_name;
          $link (interferer: $a, victim: $b) isa interference-link,
            has autonomy-tier "amber-noc",
            has interference-level-db $idb,
            has persistence-hours $h;
        get $a_name, $b_name, $idb, $h;
    """
    with _read_tx() as tx:
        for cm in _consume(tx.query.get(intf_tql)):
            amber.append({
                "cpe_id": _v(cm, "b_name"),   # victim
                "interferer": _v(cm, "a_name"),
                "interference_db": _v(cm, "idb"),
                "persistence_hours": _v(cm, "h"),
                "action": "beam-nulling CoMP coordination",
                "source": "Datalog inference (persistent-interference-noc-escalation)",
            })

    return {
        "green_auto": green,
        "amber_noc": amber,
        "red_engineering": red,
        "isolated_cpes": isolated,
        "uplink_audit_required": audit,
    }


# ---------------------------------------------------------------------------
# 5. All uplink states → CanonicalUplinkMetrics list (for Uplink Engine)
# ---------------------------------------------------------------------------

def get_all_uplink_states(cpe_ids: list[str] | None = None) -> list[CanonicalUplinkMetrics]:
    """
    Fetches all CPE uplink states from TypeDB and converts them to
    CanonicalUplinkMetrics for consumption by the Uplink Intelligence Engine.
    """
    id_clause = ""
    if cpe_ids:
        id_filter = " or ".join(f'$n == "{c}"' for c in cpe_ids)
        id_clause = f"{{ {id_filter} }};"

    tql = f"""
        match
          $cpe isa cpe-device, has name $n, has vendor $v, has intelligence-tier $tier;
          {id_clause}
          (serving-cell: $cell, served-cpe: $cpe) isa cell-coverage;
          $cell has name $cell_name;
          (subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding;
          $ul isa uplink-state;
          $ul has confidence-score $conf;
        get $n, $v, $tier, $cell_name, $ul, $conf;
    """

    results = []
    with _read_tx() as tx:
        for cm in _consume(tx.query.get(tql)):
            # Fetch uplink-state attributes via a second query inside same tx
            cpe_id = _v(cm, "n")
            vendor = _v(cm, "v")
            tier = int(_v(cm, "tier") or 1)
            cell_name = _v(cm, "cell_name")
            confidence = float(_v(cm, "conf") or 0.5)

            # Fetch individual UL attributes
            ul_tql = f"""
                match
                  $cpe isa cpe-device, has name "{cpe_id}";
                  (subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding;
                  $ul isa uplink-state;
            """
            # Build metric from available attributes
            m = CanonicalUplinkMetrics(
                cpe_id=cpe_id,
                cell_id=cell_name,
                vendor=vendor,
                timestamp_unix=time.time(),
                intelligence_tier=tier,
                confidence_score=confidence,
                source_system="TypeDB",
            )
            # Pull each optional attribute individually to handle missing ones
            m = _enrich_metric(tx, m, cpe_id)
            results.append(m)

    return results


def _enrich_metric(tx, m: CanonicalUplinkMetrics, cpe_id: str) -> CanonicalUplinkMetrics:
    """Pull uplink-state attributes for one CPE from an open read transaction."""
    attr_queries = {
        "sinr_db":           ("sinr-db", float),
        "mimo_rank_active":  ("mimo-rank", int),
        "ul_mcs":            ("ul-mcs", int),
        "ul_bler_pct":       ("ul-bler-pct", float),
        "ul_throughput_mbps":("ul-throughput-mbps", float),
        "dl_throughput_mbps":("dl-throughput-mbps", float),
        "power_headroom_db": ("power-headroom-db", float),
        "rsrp_dbm":          ("rsrp-dbm", float),
        "rsrq_db":           ("rsrq-db", float),
        "cqi":               ("cqi", int),
        "rank_indicator":    ("rank-indicator", int),
        "tx_power_dbm":      ("tx-power-dbm", float),
    }
    for py_field, (tql_attr, cast) in attr_queries.items():
        q = (
            f'match $cpe isa cpe-device, has name "{cpe_id}"; '
            f'(subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding; '
            f'$ul has {tql_attr} $val; '
            f'get $val;'
        )
        rows = _consume(tx.query.get(q))
        if rows:
            try:
                setattr(m, py_field, cast(_v(rows[0], "val")))
            except (TypeError, ValueError):
                pass

    # String attributes
    for py_field, tql_attr in [("thermal_state", "thermal-state")]:
        q = (
            f'match $cpe isa cpe-device, has name "{cpe_id}"; '
            f'(subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding; '
            f'$ul has {tql_attr} $val; '
            f'get $val;'
        )
        rows = _consume(tx.query.get(q))
        if rows:
            setattr(m, py_field, _v(rows[0], "val"))

    return m


# ---------------------------------------------------------------------------
# 6. Single CPE uplink state
# ---------------------------------------------------------------------------

def get_cpe_uplink_state(cpe_id: str) -> Optional[CanonicalUplinkMetrics]:
    with _read_tx() as tx:
        q = f'match $cpe isa cpe-device, has name "{cpe_id}"; get $cpe;'
        if not _consume(tx.query.get(q)):
            return None
        m = CanonicalUplinkMetrics(
            cpe_id=cpe_id,
            cell_id="",
            vendor="",
            timestamp_unix=time.time(),
            source_system="TypeDB",
        )
        # Get cell
        cell_q = (
            f'match $cpe isa cpe-device, has name "{cpe_id}"; '
            f'$cpe has vendor $v, has intelligence-tier $t; '
            f'(serving-cell: $cell, served-cpe: $cpe) isa cell-coverage; '
            f'$cell has name $cn; get $v, $t, $cn;'
        )
        rows = _consume(tx.query.get(cell_q))
        if rows:
            m.vendor = _v(rows[0], "v") or ""
            m.cell_id = _v(rows[0], "cn") or ""
            m.intelligence_tier = int(_v(rows[0], "t") or 1)
        return _enrich_metric(tx, m, cpe_id)


# ---------------------------------------------------------------------------
# 7. Household profiles (for /household/qoe and /outcome/report)
# ---------------------------------------------------------------------------

def get_household_profiles() -> list[dict]:
    """
    Returns all households with their CPE, uplink state, and inferred decisions.
    """
    tql = """
        match
          $hh isa household, has address $addr, has plan-tier $plan,
               has churn-risk-score $score, has status $hh_status;
          (subscriber: $hh, access-node: $cpe) isa household-service;
          $cpe has name $cpe_name, has vendor $cpe_vendor,
               has intelligence-tier $tier, has status $cpe_status;
        get $addr, $plan, $score, $hh_status, $cpe_name, $cpe_vendor, $tier, $cpe_status;
    """
    profiles = []
    with _read_tx() as tx:
        for cm in _consume(tx.query.get(tql)):
            profiles.append({
                "address": _v(cm, "addr"),
                "plan_tier": _v(cm, "plan"),
                "churn_risk_score": _v(cm, "score"),
                "household_status": _v(cm, "hh_status"),
                "cpe_id": _v(cm, "cpe_name"),
                "cpe_vendor": _v(cm, "cpe_vendor"),
                "intelligence_tier": int(_v(cm, "tier") or 1),
                "cpe_status": _v(cm, "cpe_status"),
            })
    return profiles


# ---------------------------------------------------------------------------
# 8. Multi-vendor summary (for /outcome/report)
# ---------------------------------------------------------------------------

def get_multi_vendor_summary() -> dict:
    """Count CPEs and cell sites per vendor."""
    cpe_tql = """
        match $cpe isa cpe-device, has vendor $v; get $v;
    """
    cell_tql = """
        match $cell isa cell-site, has vendor $v; get $v;
    """
    cpe_counts: dict[str, int] = {}
    cell_counts: dict[str, int] = {}
    with _read_tx() as tx:
        for cm in _consume(tx.query.get(cpe_tql)):
            v = _v(cm, "v")
            cpe_counts[v] = cpe_counts.get(v, 0) + 1
        for cm in _consume(tx.query.get(cell_tql)):
            v = _v(cm, "v")
            cell_counts[v] = cell_counts.get(v, 0) + 1
    return {"cpes_per_vendor": cpe_counts, "cells_per_vendor": cell_counts}


# ---------------------------------------------------------------------------
# 9. Update CPE status (used after remediation or rollback)
# ---------------------------------------------------------------------------

def update_cpe_status(cpe_id: str, new_status: str) -> None:
    """Overwrite the status attribute on a CPE device."""
    with TypeDB.core_driver(TYPEDB_HOST) as driver:
        with driver.session(DB_NAME, SessionType.DATA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                # Delete old status attribute
                tx.query.delete(
                    f'match $cpe isa cpe-device, has name "{cpe_id}", has status $s; '
                    f'delete $cpe has status $s;'
                )
                # Insert new status
                tx.query.insert(
                    f'match $cpe isa cpe-device, has name "{cpe_id}"; '
                    f'insert $cpe has status "{new_status}";'
                )
                tx.commit()


# ---------------------------------------------------------------------------
# 10. Health check
# ---------------------------------------------------------------------------

def ping() -> bool:
    """Returns True if TypeDB is reachable and the FWA database exists."""
    try:
        with TypeDB.core_driver(TYPEDB_HOST) as driver:
            return driver.databases.contains(DB_NAME)
    except Exception:
        return False
