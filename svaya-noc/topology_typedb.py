from typedb.driver import TypeDB, SessionType, TransactionType

# ASTRA FWA Knowledge Graph Schema
# Extends Svaya V9 TypeDB architecture with FWA-specific entity types
# as specified in ASTRA Architecture Spec v1.1, Layer 2
SCHEMA_QUERY = """
define
    # --- Attributes ---
    name sub attribute, value string;
    status sub attribute, value string;
    vendor sub attribute, value string;
    model sub attribute, value string;
    firmware-version sub attribute, value string;
    address sub attribute, value string;
    plan-tier sub attribute, value string;
    sla-class sub attribute, value string;
    churn-risk-score sub attribute, value double;
    thermal-state sub attribute, value string;
    tx-power-dbm sub attribute, value double;
    mimo-rank sub attribute, value long;
    intelligence-tier sub attribute, value long;
    rsrp-dbm sub attribute, value double;
    rsrq-db sub attribute, value double;
    sinr-db sub attribute, value double;
    cqi sub attribute, value long;
    rank-indicator sub attribute, value long;
    power-headroom-db sub attribute, value double;
    ul-mcs sub attribute, value long;
    ul-bler-pct sub attribute, value double;
    dl-throughput-mbps sub attribute, value double;
    ul-throughput-mbps sub attribute, value double;
    latency-ms sub attribute, value double;
    band sub attribute, value string;
    tdd-ratio sub attribute, value string;
    capacity-utilization-pct sub attribute, value double;
    beam-config sub attribute, value string;
    material-type sub attribute, value string;
    floor-count sub attribute, value long;
    orientation sub attribute, value string;
    interference-level-db sub attribute, value double;
    direction sub attribute, value string;
    persistence-hours sub attribute, value double;
    data-source-tier sub attribute, value long;
    confidence-score sub attribute, value double;
    probe-id sub attribute, value string;
    lte-fallback-status sub attribute, value string;
    autonomy-tier sub attribute, value string;
    timestamp sub attribute, value string;

    # --- Entities ---
    network-element sub entity, abstract,
        owns name,
        owns status,
        owns vendor;

    household sub entity,
        owns address,
        owns plan-tier,
        owns sla-class,
        owns churn-risk-score,
        owns status,
        plays household-service:subscriber,
        plays household-location:resident,
        plays cpe-installation:installation-site;

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
        plays household-service:access-node,
        plays cpe-installation:installed-cpe,
        plays cell-coverage:served-cpe,
        plays interference-link:interferer,
        plays interference-link:victim,
        plays uplink-binding:subject-cpe;

    astra-probe sub entity,
        owns probe-id,
        owns firmware-version,
        owns lte-fallback-status,
        owns status,
        plays probe-monitoring:probe-device,
        plays cpe-installation:companion-probe;

    cell-site sub entity,
        owns name,
        owns vendor,
        owns band,
        owns tdd-ratio,
        owns capacity-utilization-pct,
        owns beam-config,
        owns status,
        plays cell-coverage:serving-cell,
        plays nms-management:managed-element;

    ran-nms sub entity,
        owns name,
        owns vendor,
        plays nms-management:managing-system;

    building sub entity,
        owns address,
        owns material-type,
        owns floor-count,
        owns orientation,
        plays household-location:structure,
        plays signal-attenuation:attenuating-body;

    uplink-state sub entity,
        owns sinr-db,
        owns mimo-rank,
        owns ul-mcs,
        owns ul-bler-pct,
        owns ul-throughput-mbps,
        owns power-headroom-db,
        owns rsrp-dbm,
        owns rsrq-db,
        owns cqi,
        owns rank-indicator,
        owns data-source-tier,
        owns confidence-score,
        owns timestamp,
        plays uplink-binding:uplink-snapshot;

    interference-graph-node sub entity,
        owns name,
        owns interference-level-db,
        owns direction,
        owns persistence-hours,
        plays interference-link:edge-node,
        plays signal-attenuation:propagation-path;

    # --- Relations ---
    household-service sub relation,
        relates subscriber,
        relates access-node;

    cpe-installation sub relation,
        relates installation-site,
        relates installed-cpe,
        relates companion-probe;

    cell-coverage sub relation,
        relates serving-cell,
        relates served-cpe;

    interference-link sub relation,
        relates interferer,
        relates victim,
        relates edge-node;

    uplink-binding sub relation,
        relates subject-cpe,
        relates uplink-snapshot;

    probe-monitoring sub relation,
        relates probe-device,
        relates installed-cpe;

    household-location sub relation,
        relates resident,
        relates structure;

    signal-attenuation sub relation,
        relates attenuating-body,
        relates propagation-path;

    nms-management sub relation,
        relates managing-system,
        relates managed-element;

    # --- Datalog Inference Rules ---
    # Rule 1: CPE uplink is SINR-constrained; force rank 1 when SINR below threshold
    rule uplink-rank-downgrade:
    when {
        $cpe isa cpe-device;
        (subject-cpe: $cpe, uplink-snapshot: $ul) isa uplink-binding;
        $ul isa uplink-state, has sinr-db $sinr;
        $sinr < 5.0;
        $ul has mimo-rank $rank;
        $rank = 2;
    } then {
        $cpe has autonomy-tier "green-auto";
    };

    # Rule 2: CPE thermal stress — reactive Tx power reduction (Tier 1 reactive path)
    rule cpe-thermal-stress:
    when {
        $cpe isa cpe-device, has thermal-state "THROTTLING";
    } then {
        $cpe has autonomy-tier "green-auto";
    };

    # Rule 3: Persistent interference pair requires NOC approval for beam nulling
    rule persistent-interference-requires-noc:
    when {
        $a isa cpe-device;
        $b isa cpe-device;
        (interferer: $a, victim: $b) isa interference-link;
        $e isa interference-graph-node, has persistence-hours $h;
        $h > 24.0;
    } then {
        $e has autonomy-tier "amber-noc";
    };

    # Rule 4: Cell isolation — if cell site is offline all served CPEs enter fault state
    rule cell-site-isolation:
    when {
        $cell isa cell-site, has status "offline";
        $cpe isa cpe-device;
        (serving-cell: $cell, served-cpe: $cpe) isa cell-coverage;
    } then {
        $cpe has status "isolated";
    };

    # Rule 5: High churn risk household needs uplink audit
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
"""

# FWA pilot topology: 2 cell sites (Ericsson + Nokia), 6 households, CPEs at varying tiers
DATA_QUERY = """
insert
    # Cell sites
    $cell1 isa cell-site,
        has name "ERIC-gNB-1-Sector-A",
        has vendor "Ericsson",
        has band "n78",
        has tdd-ratio "4DL:1UL",
        has capacity-utilization-pct 72.0,
        has beam-config "default",
        has status "online";

    $cell2 isa cell-site,
        has name "NOK-gNB-2-Sector-B",
        has vendor "Nokia",
        has band "n41",
        has tdd-ratio "3DL:2UL",
        has capacity-utilization-pct 45.0,
        has beam-config "default",
        has status "online";

    $nms1 isa ran-nms,
        has name "Ericsson-ENM-01",
        has vendor "Ericsson";
    $nms2 isa ran-nms,
        has name "Nokia-NetAct-01",
        has vendor "Nokia";

    (managing-system: $nms1, managed-element: $cell1) isa nms-management;
    (managing-system: $nms2, managed-element: $cell2) isa nms-management;

    # Building
    $bldg1 isa building,
        has address "12 Maple Street",
        has material-type "brick",
        has floor-count 3,
        has orientation "north-facing";

    # Household 1 — standard plan, Ericsson cell, Tier 1 CPE, uplink constrained
    $hh1 isa household,
        has address "12 Maple St, Unit 1A",
        has plan-tier "standard",
        has sla-class "residential",
        has churn-risk-score 0.75,
        has status "active";
    $cpe1 isa cpe-device,
        has name "CPE-ZTE-001",
        has vendor "ZTE",
        has model "MC801A",
        has firmware-version "2.1.4",
        has thermal-state "NORMAL",
        has tx-power-dbm 23.0,
        has mimo-rank 2,
        has intelligence-tier 1,
        has status "online";
    $ul1 isa uplink-state,
        has sinr-db 3.2,
        has mimo-rank 2,
        has ul-mcs 8,
        has ul-bler-pct 14.5,
        has ul-throughput-mbps 18.3,
        has power-headroom-db -2.1,
        has rsrp-dbm -102.0,
        has rsrq-db -13.5,
        has cqi 7,
        has rank-indicator 1,
        has data-source-tier 1,
        has confidence-score 0.87,
        has timestamp "2026-05-06T08:00:00Z";
    (subscriber: $hh1, access-node: $cpe1) isa household-service;
    (installation-site: $hh1, installed-cpe: $cpe1) isa cpe-installation;
    (serving-cell: $cell1, served-cpe: $cpe1) isa cell-coverage;
    (subject-cpe: $cpe1, uplink-snapshot: $ul1) isa uplink-binding;
    (resident: $hh1, structure: $bldg1) isa household-location;

    # Household 2 — premium plan, Ericsson cell, Tier 2 CPE + Probe, thermal stress
    $hh2 isa household,
        has address "12 Maple St, Unit 2B",
        has plan-tier "premium",
        has sla-class "premium-sla",
        has churn-risk-score 0.3,
        has status "active";
    $cpe2 isa cpe-device,
        has name "CPE-Inseego-002",
        has vendor "Inseego",
        has model "FW2000e",
        has firmware-version "3.0.1",
        has thermal-state "THROTTLING",
        has tx-power-dbm 25.5,
        has mimo-rank 2,
        has intelligence-tier 2,
        has status "online";
    $probe2 isa astra-probe,
        has probe-id "PROBE-0042",
        has firmware-version "1.4.0",
        has lte-fallback-status "active",
        has status "online";
    $ul2 isa uplink-state,
        has sinr-db 9.1,
        has mimo-rank 2,
        has ul-mcs 14,
        has ul-bler-pct 3.2,
        has ul-throughput-mbps 67.8,
        has power-headroom-db 1.5,
        has rsrp-dbm -89.0,
        has rsrq-db -9.0,
        has cqi 11,
        has rank-indicator 2,
        has data-source-tier 2,
        has confidence-score 0.96,
        has timestamp "2026-05-06T08:00:00Z";
    (subscriber: $hh2, access-node: $cpe2) isa household-service;
    (installation-site: $hh2, installed-cpe: $cpe2, companion-probe: $probe2) isa cpe-installation;
    (serving-cell: $cell1, served-cpe: $cpe2) isa cell-coverage;
    (subject-cpe: $cpe2, uplink-snapshot: $ul2) isa uplink-binding;
    (probe-device: $probe2, installed-cpe: $cpe2) isa probe-monitoring;
    (resident: $hh2, structure: $bldg1) isa household-location;

    # Household 3 — standard plan, Nokia cell, Tier 1 CPE, interference victim
    $hh3 isa household,
        has address "45 Oak Avenue, Unit 5",
        has plan-tier "standard",
        has sla-class "residential",
        has churn-risk-score 0.55,
        has status "active";
    $cpe3 isa cpe-device,
        has name "CPE-Arcadyan-003",
        has vendor "Arcadyan",
        has model "VRX592",
        has firmware-version "1.8.2",
        has thermal-state "NORMAL",
        has tx-power-dbm 23.0,
        has mimo-rank 2,
        has intelligence-tier 1,
        has status "online";
    $ul3 isa uplink-state,
        has sinr-db 6.4,
        has mimo-rank 2,
        has ul-mcs 10,
        has ul-bler-pct 7.8,
        has ul-throughput-mbps 32.1,
        has power-headroom-db 0.3,
        has rsrp-dbm -96.0,
        has rsrq-db -11.2,
        has cqi 9,
        has rank-indicator 2,
        has data-source-tier 1,
        has confidence-score 0.82,
        has timestamp "2026-05-06T08:00:00Z";
    (subscriber: $hh3, access-node: $cpe3) isa household-service;
    (installation-site: $hh3, installed-cpe: $cpe3) isa cpe-installation;
    (serving-cell: $cell2, served-cpe: $cpe3) isa cell-coverage;
    (subject-cpe: $cpe3, uplink-snapshot: $ul3) isa uplink-binding;

    # Interference: CPE-3 is being interfered with by CPE-4 (persistent static)
    $cpe4 isa cpe-device,
        has name "CPE-Sagemcom-004",
        has vendor "Sagemcom",
        has model "RTL96",
        has firmware-version "2.3.0",
        has thermal-state "NORMAL",
        has tx-power-dbm 24.0,
        has mimo-rank 1,
        has intelligence-tier 1,
        has status "online";
    $hh4 isa household,
        has address "47 Oak Avenue, Unit 6",
        has plan-tier "standard",
        has sla-class "residential",
        has churn-risk-score 0.2,
        has status "active";
    $ul4 isa uplink-state,
        has sinr-db 14.2,
        has mimo-rank 1,
        has ul-mcs 18,
        has ul-bler-pct 1.1,
        has ul-throughput-mbps 55.0,
        has power-headroom-db 3.8,
        has rsrp-dbm -82.0,
        has rsrq-db -7.5,
        has cqi 13,
        has rank-indicator 1,
        has data-source-tier 1,
        has confidence-score 0.91,
        has timestamp "2026-05-06T08:00:00Z";
    (subscriber: $hh4, access-node: $cpe4) isa household-service;
    (installation-site: $hh4, installed-cpe: $cpe4) isa cpe-installation;
    (serving-cell: $cell2, served-cpe: $cpe4) isa cell-coverage;
    (subject-cpe: $cpe4, uplink-snapshot: $ul4) isa uplink-binding;

    $inode isa interference-graph-node,
        has name "INTF-CPE003-CPE004",
        has interference-level-db 8.5,
        has direction "UL",
        has persistence-hours 31.0;
    (interferer: $cpe4, victim: $cpe3) isa interference-link;
"""


def setup_typedb():
    print("=== ASTRA FWA Knowledge Graph Setup (TypeDB) ===")
    with TypeDB.core_driver("127.0.0.1:1729") as driver:
        if driver.databases.contains("astra_fwa"):
            print("Database 'astra_fwa' already exists. Recreating...")
            driver.databases.get("astra_fwa").delete()

        driver.databases.create("astra_fwa")
        print("Created database: astra_fwa")

        with driver.session("astra_fwa", SessionType.SCHEMA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                print("Defining FWA ontology and Datalog inference rules...")
                tx.query.define(SCHEMA_QUERY)
                tx.commit()

        with driver.session("astra_fwa", SessionType.DATA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                print("Inserting FWA pilot topology (2 cells, 4 households, 1 probe)...")
                tx.query.insert(DATA_QUERY)
                tx.commit()

        print("\nASTRA TypeDB Setup Complete!")
        print("  - 2x Cell Sites (Ericsson n78 + Nokia n41)")
        print("  - 4x CPE Devices (ZTE, Inseego, Arcadyan, Sagemcom)")
        print("  - 1x ASTRA Probe (Tier 2, with LTE fallback)")
        print("  - 4x Households with Uplink State snapshots")
        print("  - 1x Persistent Interference pair (30h+ duration)")
        print("  - 5x Datalog inference rules active")
        print("Visualize in TypeDB Studio at 127.0.0.1:1729 → database: astra_fwa")


if __name__ == "__main__":
    try:
        setup_typedb()
    except Exception as e:
        print(f"Error connecting to TypeDB: {e}")
        print("Make sure TypeDB Core is running on port 1729!")
