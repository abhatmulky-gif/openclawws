"""
ASTRA FWA Knowledge Graph — TypeDB Schema + Pilot Data
Eight-layer ASTRA stack, Layers 0–2 represented here.
Deterministic Datalog reasoning replaces statistical ML for safety-critical decisions.
Spec ref: ASTRA Architecture Spec v1.1, Section 4.3 (Layer 2).
"""

from typedb.driver import TypeDB, SessionType, TransactionType

DB_NAME = "astra_fwa"
TYPEDB_HOST = "127.0.0.1:1729"

# ---------------------------------------------------------------------------
# Schema: FWA ontology + Datalog inference rules
# Design principles:
#   - Multi-vendor complexity absorbed entirely at schema level
#   - Interference attributes live on the relation (not a separate entity)
#   - Backhaul transport layer (ASR/Core) is a first-class entity
#   - Every safety-critical decision derived by deterministic Datalog rule
# ---------------------------------------------------------------------------
SCHEMA_QUERY = """
define

  # ---- Primitive attributes ----
  name             sub attribute, value string;
  status           sub attribute, value string;
  vendor           sub attribute, value string;
  model            sub attribute, value string;
  firmware-version sub attribute, value string;
  node-type        sub attribute, value string;
  address          sub attribute, value string;
  plan-tier        sub attribute, value string;
  sla-class        sub attribute, value string;
  churn-risk-score sub attribute, value double;
  autonomy-tier    sub attribute, value string;
  connection-type  sub attribute, value string;
  timestamp        sub attribute, value string;

  # Radio / uplink metrics
  rsrp-dbm           sub attribute, value double;
  rsrq-db            sub attribute, value double;
  sinr-db            sub attribute, value double;
  cqi                sub attribute, value long;
  rank-indicator     sub attribute, value long;
  power-headroom-db  sub attribute, value double;
  ul-mcs             sub attribute, value long;
  ul-bler-pct        sub attribute, value double;
  ul-throughput-mbps sub attribute, value double;
  dl-throughput-mbps sub attribute, value double;
  timing-advance     sub attribute, value long;
  tx-power-dbm       sub attribute, value double;
  thermal-state      sub attribute, value string;   # NORMAL | THROTTLING | CRITICAL
  mimo-rank          sub attribute, value long;
  intelligence-tier  sub attribute, value long;     # 1=TR-369 | 2=Probe | 3=SDK
  data-source-tier   sub attribute, value long;
  confidence-score   sub attribute, value double;
  reporting-latency-s sub attribute, value double;

  # Cell site attributes
  band                  sub attribute, value string;
  tdd-ratio             sub attribute, value string;
  capacity-utilization-pct sub attribute, value double;
  beam-config           sub attribute, value string;

  # Building attributes
  material-type  sub attribute, value string;
  floor-count    sub attribute, value long;
  orientation    sub attribute, value string;

  # Probe attributes
  probe-id            sub attribute, value string;
  lte-fallback-status sub attribute, value string;

  # Interference attributes (live on the relation itself, not a separate entity)
  interference-level-db sub attribute, value double;
  persistence-hours     sub attribute, value double;
  direction             sub attribute, value string;


  # ---- Entities ----

  # Backhaul/transport equipment (Cisco ASR, Core Routers, microwave links)
  # Replaces Neo4j :Equipment nodes
  backhaul-node sub entity,
    owns name,
    owns vendor,
    owns node-type,
    owns status,
    plays aggregation-link:upstream-node,
    plays aggregation-link:downstream-node,
    plays backhaul-connection:transport;

  # gNB / Cell sector
  cell-site sub entity,
    owns name,
    owns vendor,
    owns band,
    owns tdd-ratio,
    owns capacity-utilization-pct,
    owns beam-config,
    owns status,
    plays cell-coverage:serving-cell,
    plays nms-management:managed-element,
    plays backhaul-connection:radio-access;

  # RAN NMS (Ericsson ENM, Nokia NetAct, Samsung OSS, Huawei iMaster NCE)
  ran-nms sub entity,
    owns name,
    owns vendor,
    plays nms-management:managing-system;

  # FWA CPE device
  cpe-device sub entity,
    owns name,
    owns vendor,
    owns model,
    owns firmware-version,
    owns thermal-state,
    owns tx-power-dbm,
    owns mimo-rank,
    owns intelligence-tier,
    owns status,
    owns autonomy-tier,
    plays household-service:access-node,
    plays cpe-installation:installed-cpe,
    plays cell-coverage:served-cpe,
    plays interference-link:interferer,
    plays interference-link:victim,
    plays uplink-binding:subject-cpe;

  # ASTRA Probe (Tier 2 companion device — manufactured by ASTRA, zero CPE vendor dependency)
  astra-probe sub entity,
    owns probe-id,
    owns firmware-version,
    owns lte-fallback-status,
    owns status,
    plays probe-monitoring:probe-device,
    plays cpe-installation:companion-probe;

  # Subscriber household
  household sub entity,
    owns address,
    owns plan-tier,
    owns sla-class,
    owns churn-risk-score,
    owns status,
    plays household-service:subscriber,
    plays household-location:resident,
    plays cpe-installation:installation-site;

  # Physical building (attenuation profile)
  building sub entity,
    owns address,
    owns material-type,
    owns floor-count,
    owns orientation,
    plays household-location:structure;

  # Uplink state snapshot (one per CPE; upserted on each telemetry poll)
  uplink-state sub entity,
    owns sinr-db,
    owns mimo-rank,
    owns ul-mcs,
    owns ul-bler-pct,
    owns ul-throughput-mbps,
    owns dl-throughput-mbps,
    owns power-headroom-db,
    owns rsrp-dbm,
    owns rsrq-db,
    owns cqi,
    owns rank-indicator,
    owns tx-power-dbm,
    owns thermal-state,
    owns data-source-tier,
    owns confidence-score,
    owns reporting-latency-s,
    owns timestamp,
    plays uplink-binding:uplink-snapshot;


  # ---- Relations ----

  # CPE served by a cell sector
  cell-coverage sub relation,
    relates serving-cell,
    relates served-cpe;

  # Cell backhaul to transport node (gNB → ASR)
  backhaul-connection sub relation,
    owns connection-type,
    relates radio-access,
    relates transport;

  # Transport node aggregation (ASR → Core)
  aggregation-link sub relation,
    owns connection-type,
    relates upstream-node,
    relates downstream-node;

  # Cell site managed by a RAN NMS
  nms-management sub relation,
    relates managing-system,
    relates managed-element;

  # CPE at a household
  household-service sub relation,
    relates subscriber,
    relates access-node;

  # Physical installation (household + CPE + optional probe)
  cpe-installation sub relation,
    relates installation-site,
    relates installed-cpe,
    relates companion-probe;

  # Uplink snapshot bound to a CPE
  uplink-binding sub relation,
    relates subject-cpe,
    relates uplink-snapshot;

  # ASTRA Probe monitoring a CPE
  probe-monitoring sub relation,
    relates probe-device,
    relates installed-cpe;

  # Household in a building
  household-location sub relation,
    relates resident,
    relates structure;

  # Static CPE-to-CPE interference edge.
  # Attributes live ON the relation (not a separate entity) so Datalog rules
  # can reason over them directly without an extra join.
  interference-link sub relation,
    relates interferer,
    relates victim,
    owns interference-level-db,
    owns persistence-hours,
    owns direction,
    owns autonomy-tier;


  # ---- Datalog Inference Rules ----
  # All safety-critical decisions are derived here — zero LLM in the decision loop.

  # Rule 1: SINR too low for Rank 2 — auto-downgrade to Rank 1
  # Fires when SINR < 5dB AND CPE is currently operating at Rank 2.
  rule uplink-rank-downgrade:
  when {
    $cpe isa cpe-device;
    (subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding;
    $ul isa uplink-state, has sinr-db $sinr, has mimo-rank $rank;
    $sinr < 5.0;
    $rank = 2;
  } then {
    $cpe has autonomy-tier "green-auto";
  };

  # Rule 2: CPE power headroom exhausted — Rank 1 is mandatory
  # PHR < 0 dB means the CPE is at its maximum transmit power.
  rule uplink-phr-exhausted:
  when {
    $cpe isa cpe-device;
    (subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding;
    $ul isa uplink-state, has power-headroom-db $phr, has mimo-rank $rank;
    $phr < 0.0;
    $rank = 2;
  } then {
    $cpe has autonomy-tier "green-auto";
  };

  # Rule 3: CPE thermal stress — reactive Tx power reduction via TR-369
  rule cpe-thermal-stress:
  when {
    $cpe isa cpe-device, has thermal-state "THROTTLING";
  } then {
    $cpe has autonomy-tier "green-auto";
  };

  # Rule 4: Persistent static interference — NOC approval required for beam nulling
  # Static FWA interference patterns lasting > 24h will not self-resolve.
  rule persistent-interference-noc-escalation:
  when {
    $link (interferer: $a, victim: $b) isa interference-link,
      has persistence-hours $h;
    $h > 24.0;
  } then {
    $link has autonomy-tier "amber-noc";
  };

  # Rule 5: Cell site offline → all served CPEs become isolated
  rule cell-site-isolation-cascade:
  when {
    $cell isa cell-site, has status "offline";
    $cpe isa cpe-device;
    (serving-cell: $cell, served-cpe: $cpe) isa cell-coverage;
  } then {
    $cpe has status "isolated";
  };

  # Rule 6: High-churn household + high UL BLER → flag CPE for uplink audit
  rule high-churn-uplink-audit:
  when {
    $h isa household, has churn-risk-score $score;
    $score > 0.7;
    $cpe isa cpe-device;
    (subscriber: $h, access-node: $cpe) isa household-service;
    (subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding;
    $ul isa uplink-state, has ul-bler-pct $bler;
    $bler > 10.0;
  } then {
    $cpe has status "uplink-audit-required";
  };

  # Rule 7: Silent Zone detection — PHR exhausted AND RSRP at cell edge
  # These CPEs are candidates for Cross-Band UL/DL Decoupling (Red tier, engineering).
  rule silent-zone-candidate:
  when {
    $cpe isa cpe-device;
    (subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding;
    $ul isa uplink-state, has power-headroom-db $phr, has rsrp-dbm $rsrp;
    $phr < -5.0;
    $rsrp < -110.0;
  } then {
    $cpe has autonomy-tier "red-engineering";
  };
"""

# ---------------------------------------------------------------------------
# Pilot data: 2 RAN vendors, 6 CPEs, transport backbone, 4 households, 1 probe
# Mirrors the topology previously in Neo4j + the TypeDB-only data.
# ---------------------------------------------------------------------------
DATA_QUERY = """
insert

  # --- Transport backbone (previously Neo4j :Equipment nodes) ---
  $core isa backhaul-node,
    has name "CISCO-CORE-1",
    has vendor "Cisco",
    has node-type "Core Router",
    has status "online";
  $asr1 isa backhaul-node,
    has name "CISCO-ASR-1",
    has vendor "Cisco",
    has node-type "Aggregation Router",
    has status "online";
  $asr2 isa backhaul-node,
    has name "CISCO-ASR-2",
    has vendor "Cisco",
    has node-type "Aggregation Router",
    has status "online";
  (upstream-node: $core, downstream-node: $asr1) isa aggregation-link,
    has connection-type "fiber";
  (upstream-node: $core, downstream-node: $asr2) isa aggregation-link,
    has connection-type "fiber";

  # --- RAN NMS systems ---
  $nms1 isa ran-nms, has name "Ericsson-ENM-01", has vendor "Ericsson";
  $nms2 isa ran-nms, has name "Nokia-NetAct-01",  has vendor "Nokia";

  # --- Ericsson cell sites (n78 FWA) ---
  $cell_e1 isa cell-site,
    has name "ERIC-gNB-1-FWA", has vendor "Ericsson",
    has band "n78", has tdd-ratio "4DL:1UL",
    has capacity-utilization-pct 72.0,
    has beam-config "default", has status "online";
  $cell_e2 isa cell-site,
    has name "ERIC-gNB-2-FWA", has vendor "Ericsson",
    has band "n78", has tdd-ratio "4DL:1UL",
    has capacity-utilization-pct 58.0,
    has beam-config "default", has status "online";
  $cell_e3 isa cell-site,
    has name "ERIC-gNB-3-FWA", has vendor "Ericsson",
    has band "n78", has tdd-ratio "4DL:1UL",
    has capacity-utilization-pct 31.0,
    has beam-config "default", has status "online";

  (radio-access: $cell_e1, transport: $asr1) isa backhaul-connection, has connection-type "fiber";
  (radio-access: $cell_e2, transport: $asr1) isa backhaul-connection, has connection-type "fiber";
  (radio-access: $cell_e3, transport: $asr1) isa backhaul-connection, has connection-type "microwave";
  (managing-system: $nms1, managed-element: $cell_e1) isa nms-management;
  (managing-system: $nms1, managed-element: $cell_e2) isa nms-management;
  (managing-system: $nms1, managed-element: $cell_e3) isa nms-management;

  # --- Nokia cell sites (n41 FWA) ---
  $cell_n1 isa cell-site,
    has name "NOK-gNB-1-FWA", has vendor "Nokia",
    has band "n41", has tdd-ratio "3DL:2UL",
    has capacity-utilization-pct 45.0,
    has beam-config "default", has status "online";
  $cell_n2 isa cell-site,
    has name "NOK-gNB-2-FWA", has vendor "Nokia",
    has band "n41", has tdd-ratio "3DL:2UL",
    has capacity-utilization-pct 61.0,
    has beam-config "default", has status "online";
  $cell_n3 isa cell-site,
    has name "NOK-gNB-3-FWA", has vendor "Nokia",
    has band "n41", has tdd-ratio "3DL:2UL",
    has capacity-utilization-pct 22.0,
    has beam-config "default", has status "online";

  (radio-access: $cell_n1, transport: $asr2) isa backhaul-connection, has connection-type "fiber";
  (radio-access: $cell_n2, transport: $asr2) isa backhaul-connection, has connection-type "fiber";
  (radio-access: $cell_n3, transport: $asr2) isa backhaul-connection, has connection-type "microwave";
  (managing-system: $nms2, managed-element: $cell_n1) isa nms-management;
  (managing-system: $nms2, managed-element: $cell_n2) isa nms-management;
  (managing-system: $nms2, managed-element: $cell_n3) isa nms-management;

  # --- Building ---
  $bldg isa building,
    has address "12 Maple Street",
    has material-type "brick",
    has floor-count 3,
    has orientation "north-facing";

  # --- CPE 1: ZTE MC801A — Tier 1, uplink-constrained (SINR 3.2 < 5, Rank 2) ---
  $cpe1 isa cpe-device,
    has name "CPE-ZTE-001", has vendor "ZTE", has model "MC801A",
    has firmware-version "2.1.4", has thermal-state "NORMAL",
    has tx-power-dbm 23.0, has mimo-rank 2, has intelligence-tier 1,
    has status "online";
  $ul1 isa uplink-state,
    has sinr-db 3.2, has mimo-rank 2, has ul-mcs 8,
    has ul-bler-pct 14.5, has ul-throughput-mbps 18.3,
    has power-headroom-db -2.1, has rsrp-dbm -102.0, has rsrq-db -13.5,
    has cqi 7, has rank-indicator 1,
    has data-source-tier 1, has confidence-score 0.87,
    has timestamp "2026-05-06T08:00:00Z";
  $hh1 isa household,
    has address "12 Maple St, Unit 1A", has plan-tier "standard",
    has sla-class "residential", has churn-risk-score 0.75, has status "active";
  (subscriber: $hh1, access-node: $cpe1) isa household-service;
  (installation-site: $hh1, installed-cpe: $cpe1) isa cpe-installation;
  (serving-cell: $cell_e1, served-cpe: $cpe1) isa cell-coverage;
  (subject-cpe: $cpe1, uplink-snapshot: $ul1) isa uplink-binding;
  (resident: $hh1, structure: $bldg) isa household-location;

  # --- CPE 2: Inseego FW2000e — Tier 2 + Probe, thermal throttling ---
  $cpe2 isa cpe-device,
    has name "CPE-Inseego-002", has vendor "Inseego", has model "FW2000e",
    has firmware-version "3.0.1", has thermal-state "THROTTLING",
    has tx-power-dbm 25.5, has mimo-rank 2, has intelligence-tier 2,
    has status "online";
  $probe2 isa astra-probe,
    has probe-id "PROBE-0042", has firmware-version "1.4.0",
    has lte-fallback-status "active", has status "online";
  $ul2 isa uplink-state,
    has sinr-db 9.1, has mimo-rank 2, has ul-mcs 14,
    has ul-bler-pct 3.2, has ul-throughput-mbps 67.8,
    has power-headroom-db 1.5, has rsrp-dbm -89.0, has rsrq-db -9.0,
    has cqi 11, has rank-indicator 2,
    has data-source-tier 2, has confidence-score 0.96,
    has timestamp "2026-05-06T08:00:00Z";
  $hh2 isa household,
    has address "12 Maple St, Unit 2B", has plan-tier "premium",
    has sla-class "premium-sla", has churn-risk-score 0.3, has status "active";
  (subscriber: $hh2, access-node: $cpe2) isa household-service;
  (installation-site: $hh2, installed-cpe: $cpe2, companion-probe: $probe2) isa cpe-installation;
  (serving-cell: $cell_e1, served-cpe: $cpe2) isa cell-coverage;
  (subject-cpe: $cpe2, uplink-snapshot: $ul2) isa uplink-binding;
  (probe-device: $probe2, installed-cpe: $cpe2) isa probe-monitoring;

  # --- CPE 3: Arcadyan VRX592 — Tier 1, interference victim ---
  $cpe3 isa cpe-device,
    has name "CPE-Arcadyan-003", has vendor "Arcadyan", has model "VRX592",
    has firmware-version "1.8.2", has thermal-state "NORMAL",
    has tx-power-dbm 23.0, has mimo-rank 2, has intelligence-tier 1,
    has status "online";
  $ul3 isa uplink-state,
    has sinr-db 6.4, has mimo-rank 2, has ul-mcs 10,
    has ul-bler-pct 7.8, has ul-throughput-mbps 32.1,
    has power-headroom-db 0.3, has rsrp-dbm -96.0, has rsrq-db -11.2,
    has cqi 9, has rank-indicator 2,
    has data-source-tier 1, has confidence-score 0.82,
    has timestamp "2026-05-06T08:00:00Z";
  $hh3 isa household,
    has address "45 Oak Ave, Unit 5", has plan-tier "standard",
    has sla-class "residential", has churn-risk-score 0.55, has status "active";
  (subscriber: $hh3, access-node: $cpe3) isa household-service;
  (installation-site: $hh3, installed-cpe: $cpe3) isa cpe-installation;
  (serving-cell: $cell_n1, served-cpe: $cpe3) isa cell-coverage;
  (subject-cpe: $cpe3, uplink-snapshot: $ul3) isa uplink-binding;

  # --- CPE 4: Sagemcom RTL96 — Tier 1, interference source (31h persistent) ---
  $cpe4 isa cpe-device,
    has name "CPE-Sagemcom-004", has vendor "Sagemcom", has model "RTL96",
    has firmware-version "2.3.0", has thermal-state "NORMAL",
    has tx-power-dbm 24.0, has mimo-rank 1, has intelligence-tier 1,
    has status "online";
  $ul4 isa uplink-state,
    has sinr-db 14.2, has mimo-rank 1, has ul-mcs 18,
    has ul-bler-pct 1.1, has ul-throughput-mbps 55.0,
    has power-headroom-db 3.8, has rsrp-dbm -82.0, has rsrq-db -7.5,
    has cqi 13, has rank-indicator 1,
    has data-source-tier 1, has confidence-score 0.91,
    has timestamp "2026-05-06T08:00:00Z";
  $hh4 isa household,
    has address "47 Oak Ave, Unit 6", has plan-tier "standard",
    has sla-class "residential", has churn-risk-score 0.2, has status "active";
  (subscriber: $hh4, access-node: $cpe4) isa household-service;
  (installation-site: $hh4, installed-cpe: $cpe4) isa cpe-installation;
  (serving-cell: $cell_n1, served-cpe: $cpe4) isa cell-coverage;
  (subject-cpe: $cpe4, uplink-snapshot: $ul4) isa uplink-binding;

  # --- CPE 5: Huawei B818 — Tier 1, Nokia cell, healthy ---
  $cpe5 isa cpe-device,
    has name "CPE-Huawei-005", has vendor "Huawei", has model "B818",
    has firmware-version "4.1.0", has thermal-state "NORMAL",
    has tx-power-dbm 22.5, has mimo-rank 2, has intelligence-tier 1,
    has status "online";
  $ul5 isa uplink-state,
    has sinr-db 12.8, has mimo-rank 2, has ul-mcs 17,
    has ul-bler-pct 2.3, has ul-throughput-mbps 48.5,
    has power-headroom-db 2.9, has rsrp-dbm -88.0, has rsrq-db -9.8,
    has cqi 12, has rank-indicator 2,
    has data-source-tier 1, has confidence-score 0.88,
    has timestamp "2026-05-06T08:00:00Z";
  $hh5 isa household,
    has address "100 Pine Rd, Unit 3", has plan-tier "standard",
    has sla-class "residential", has churn-risk-score 0.18, has status "active";
  (subscriber: $hh5, access-node: $cpe5) isa household-service;
  (installation-site: $hh5, installed-cpe: $cpe5) isa cpe-installation;
  (serving-cell: $cell_n2, served-cpe: $cpe5) isa cell-coverage;
  (subject-cpe: $cpe5, uplink-snapshot: $ul5) isa uplink-binding;

  # --- CPE 6: Nokia FastMile — Tier 1, Ericsson cell, Silent Zone candidate ---
  $cpe6 isa cpe-device,
    has name "CPE-Nokia-006", has vendor "Nokia", has model "FastMile-5G21",
    has firmware-version "21.4.2", has thermal-state "NORMAL",
    has tx-power-dbm 25.9, has mimo-rank 1, has intelligence-tier 1,
    has status "online";
  $ul6 isa uplink-state,
    has sinr-db 1.8, has mimo-rank 1, has ul-mcs 4,
    has ul-bler-pct 19.2, has ul-throughput-mbps 7.1,
    has power-headroom-db -7.3, has rsrp-dbm -114.0, has rsrq-db -17.1,
    has cqi 4, has rank-indicator 1,
    has data-source-tier 1, has confidence-score 0.79,
    has timestamp "2026-05-06T08:00:00Z";
  $hh6 isa household,
    has address "88 Elm Blvd, Unit 9", has plan-tier "standard",
    has sla-class "residential", has churn-risk-score 0.82, has status "active";
  (subscriber: $hh6, access-node: $cpe6) isa household-service;
  (installation-site: $hh6, installed-cpe: $cpe6) isa cpe-installation;
  (serving-cell: $cell_e2, served-cpe: $cpe6) isa cell-coverage;
  (subject-cpe: $cpe6, uplink-snapshot: $ul6) isa uplink-binding;

  # --- Interference edges (attributes live on the relation) ---
  # CPE-4 (Sagemcom) → CPE-3 (Arcadyan): 31h persistent — triggers amber-noc rule
  (interferer: $cpe4, victim: $cpe3) isa interference-link,
    has interference-level-db 8.5,
    has persistence-hours 31.0,
    has direction "UL";

  # CPE-6 (Nokia) → CPE-1 (ZTE): 9h — below 24h threshold, no NOC escalation yet
  (interferer: $cpe6, victim: $cpe1) isa interference-link,
    has interference-level-db 4.1,
    has persistence-hours 9.0,
    has direction "UL";
"""


def setup_typedb(recreate: bool = True):
    print(f"=== ASTRA FWA Knowledge Graph — TypeDB Setup (db: {DB_NAME}) ===")
    with TypeDB.core_driver(TYPEDB_HOST) as driver:
        if driver.databases.contains(DB_NAME):
            if recreate:
                print(f"  Database '{DB_NAME}' exists — dropping and recreating...")
                driver.databases.get(DB_NAME).delete()
            else:
                print(f"  Database '{DB_NAME}' already exists. Use recreate=True to reset.")
                return

        driver.databases.create(DB_NAME)
        print(f"  Created database: {DB_NAME}")

        with driver.session(DB_NAME, SessionType.SCHEMA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                print("  Defining FWA ontology + 7 Datalog inference rules...")
                tx.query.define(SCHEMA_QUERY)
                tx.commit()

        with driver.session(DB_NAME, SessionType.DATA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                print("  Inserting pilot topology (6 CPEs, 6 cells, 6 households, 1 probe)...")
                tx.query.insert(DATA_QUERY)
                tx.commit()

    print("\nASTRA TypeDB Setup Complete:")
    print("  Transport:     1x Cisco Core + 2x Cisco ASR (previously Neo4j only)")
    print("  RAN:           3x Ericsson gNBs (n78) + 3x Nokia gNBs (n41)")
    print("  CPEs:          6x (ZTE, Inseego/Tier2, Arcadyan, Sagemcom, Huawei, Nokia)")
    print("  Households:    6x (2 high churn-risk)")
    print("  Probes:        1x ASTRA Probe (Tier 2, LTE fallback active)")
    print("  Interference:  2x static pairs (1 triggers amber-noc rule at 31h)")
    print("  Datalog rules: 7 active (uplink, thermal, interference, isolation, churn, silent-zone)")
    print(f"\nVisualize: TypeDB Studio → {TYPEDB_HOST} → database: {DB_NAME}")


if __name__ == "__main__":
    try:
        setup_typedb()
    except Exception as e:
        print(f"\nError: {e}")
        print(f"Make sure TypeDB Core is running on {TYPEDB_HOST}")
