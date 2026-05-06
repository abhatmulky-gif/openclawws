"""
ASTRA FWA Topology Setup — Neo4j
Injects a multi-vendor FWA pilot topology into Neo4j Aura.
Topology: Ericsson + Nokia RAN → ASR aggregation → Core
         + FWA CPEs (ZTE, Inseego, Arcadyan, Sagemcom) per cell
         + persistent interference edges between CPE pairs
"""

import os
import redis
from neo4j import GraphDatabase
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), 'svaya-poc.env')
load_dotenv(env_path)

REDIS_URL = os.getenv('REDIS_URL')
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USER = os.getenv('NEO4J_USER')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')


def test_redis():
    print("Testing Redis connection...")
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
        print("  Redis connection successful!")
    except Exception as e:
        print(f"  Redis connection failed: {e}")


def setup_fwa_topology():
    print("\nBuilding ASTRA FWA topology in Neo4j...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("  Neo4j connection successful!")

        with driver.session() as s:
            print("  Clearing existing graph...")
            s.run("MATCH (n) DETACH DELETE n")

            # --- Transport Layer ---
            print("  Building Cisco transport backbone...")
            s.run("CREATE (:Equipment {id:'CISCO-CORE-1', vendor:'Cisco', type:'Core Router'})")
            s.run("CREATE (:Equipment {id:'CISCO-ASR-1', vendor:'Cisco', type:'Aggregation Router'})")
            s.run("CREATE (:Equipment {id:'CISCO-ASR-2', vendor:'Cisco', type:'Aggregation Router'})")
            s.run("MATCH (a:Equipment {id:'CISCO-ASR-1'}),(c:Equipment {id:'CISCO-CORE-1'}) CREATE (a)-[:UPLINK]->(c)")
            s.run("MATCH (a:Equipment {id:'CISCO-ASR-2'}),(c:Equipment {id:'CISCO-CORE-1'}) CREATE (a)-[:UPLINK]->(c)")

            # --- RAN Layer: Ericsson gNBs ---
            print("  Deploying Ericsson gNBs (n78, FWA)...")
            for i in range(1, 4):
                s.run(
                    "CREATE (:Cell {id:$cell_id, vendor:'Ericsson', band:'n78', type:'gNodeB'})",
                    cell_id=f"ERIC-gNB-{i}-FWA"
                )
                s.run(
                    "MATCH (g:Cell {id:$cid}),(a:Equipment {id:'CISCO-ASR-1'}) CREATE (g)-[:BACKHAUL]->(a)",
                    cid=f"ERIC-gNB-{i}-FWA"
                )

            # --- RAN Layer: Nokia gNBs ---
            print("  Deploying Nokia gNBs (n41, FWA)...")
            for i in range(1, 4):
                s.run(
                    "CREATE (:Cell {id:$cell_id, vendor:'Nokia', band:'n41', type:'gNodeB'})",
                    cell_id=f"NOK-gNB-{i}-FWA"
                )
                s.run(
                    "MATCH (g:Cell {id:$cid}),(a:Equipment {id:'CISCO-ASR-2'}) CREATE (g)-[:BACKHAUL]->(a)",
                    cid=f"NOK-gNB-{i}-FWA"
                )

            # --- FWA CPE Fleet ---
            print("  Registering FWA CPE devices...")
            fwa_cpes = [
                {"id": "CPE-ZTE-001",       "vendor": "ZTE",       "model": "MC801A",  "tier": 1, "cell": "ERIC-gNB-1-FWA"},
                {"id": "CPE-Inseego-002",   "vendor": "Inseego",   "model": "FW2000e", "tier": 2, "cell": "ERIC-gNB-1-FWA"},
                {"id": "CPE-Arcadyan-003",  "vendor": "Arcadyan",  "model": "VRX592",  "tier": 1, "cell": "NOK-gNB-1-FWA"},
                {"id": "CPE-Sagemcom-004",  "vendor": "Sagemcom",  "model": "RTL96",   "tier": 1, "cell": "NOK-gNB-1-FWA"},
                {"id": "CPE-Huawei-005",    "vendor": "Huawei",    "model": "B818",    "tier": 1, "cell": "ERIC-gNB-2-FWA"},
                {"id": "CPE-Nokia-006",     "vendor": "Nokia",     "model": "FastMile","tier": 1, "cell": "NOK-gNB-2-FWA"},
            ]
            for cpe in fwa_cpes:
                s.run(
                    "CREATE (:CPE {id:$id, vendor:$vendor, model:$model, intelligence_tier:$tier})",
                    id=cpe["id"], vendor=cpe["vendor"],
                    model=cpe["model"], tier=cpe["tier"]
                )
                s.run(
                    "MATCH (c:CPE {id:$cpe_id}),(cell:Cell {id:$cell_id}) CREATE (c)-[:SERVED_BY]->(cell)",
                    cpe_id=cpe["id"], cell_id=cpe["cell"]
                )

            # --- Interference Edges ---
            print("  Creating static interference edges...")
            interference_pairs = [
                {"src": "CPE-Sagemcom-004", "dst": "CPE-Arcadyan-003", "db": 8.5, "hours": 31.0},
                {"src": "CPE-ZTE-001",      "dst": "CPE-Inseego-002",  "db": 5.2, "hours": 12.0},
            ]
            for p in interference_pairs:
                s.run(
                    "MATCH (a:CPE {id:$src}),(b:CPE {id:$dst}) "
                    "CREATE (a)-[:INTERFERES_WITH {interference_db:$db, persistence_h:$hours}]->(b)",
                    src=p["src"], dst=p["dst"], db=p["db"], hours=p["hours"]
                )

            # --- ASTRA Probes (Tier 2 companion devices) ---
            print("  Registering ASTRA Probes (Tier 2)...")
            s.run("CREATE (:Probe {id:'PROBE-0042', firmware:'1.4.0', lte_fallback:'active'})")
            s.run(
                "MATCH (p:Probe {id:'PROBE-0042'}),(c:CPE {id:'CPE-Inseego-002'}) "
                "CREATE (p)-[:MONITORS]->(c)"
            )

        print("\n  ASTRA FWA Topology Injected Successfully:")
        print("  - 1x Cisco Core Router + 2x ASR Aggregation Routers")
        print("  - 3x Ericsson gNBs (n78) + 3x Nokia gNBs (n41)")
        print("  - 6x CPE Devices (ZTE, Inseego/Tier2, Arcadyan, Sagemcom, Huawei, Nokia)")
        print("  - 2x Static interference pairs")
        print("  - 1x ASTRA Probe monitoring Inseego CPE")

    except Exception as e:
        print(f"  Neo4j setup failed: {e}")
    finally:
        if 'driver' in locals():
            driver.close()


if __name__ == "__main__":
    test_redis()
    setup_fwa_topology()
