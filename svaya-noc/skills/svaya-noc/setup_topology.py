import os
import redis
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load from the same directory
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
        print("✅ Redis connection successful!")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")

def setup_neo4j():
    print("\nTesting Neo4j and setting up topology...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("✅ Neo4j connection successful!")
        
        with driver.session() as session:
            print("Clearing existing graph...")
            session.run("MATCH (n) DETACH DELETE n")
            
            print("Building Cisco Transport Network...")
            # Core and Aggregation layer
            session.run("CREATE (c:Equipment {id: 'CISCO-CORE-1', vendor: 'Cisco', type: 'Core Router'})")
            session.run("CREATE (a1:Equipment {id: 'CISCO-ASR-1', vendor: 'Cisco', type: 'Aggregation Router'})")
            session.run("CREATE (a2:Equipment {id: 'CISCO-ASR-2', vendor: 'Cisco', type: 'Aggregation Router'})")
            
            session.run("MATCH (a1:Equipment {id: 'CISCO-ASR-1'}), (c:Equipment {id: 'CISCO-CORE-1'}) CREATE (a1)-[:UPLINK]->(c)")
            session.run("MATCH (a2:Equipment {id: 'CISCO-ASR-2'}), (c:Equipment {id: 'CISCO-CORE-1'}) CREATE (a2)-[:UPLINK]->(c)")
            
            print("Deploying 5 Ericsson gNodeBs to CISCO-ASR-1...")
            for i in range(1, 6):
                session.run(f"CREATE (g:Equipment {{id: 'ERIC-gNB-{i}', vendor: 'Ericsson', type: 'gNodeB'}})")
                session.run(f"MATCH (g:Equipment {{id: 'ERIC-gNB-{i}'}}), (a:Equipment {{id: 'CISCO-ASR-1'}}) CREATE (g)-[:BACKHAUL]->(a)")
                
            print("Deploying 5 Nokia gNodeBs to CISCO-ASR-2...")
            for i in range(1, 6):
                session.run(f"CREATE (g:Equipment {{id: 'NOK-gNB-{i}', vendor: 'Nokia', type: 'gNodeB'}})")
                session.run(f"MATCH (g:Equipment {{id: 'NOK-gNB-{i}'}}), (a:Equipment {{id: 'CISCO-ASR-2'}}) CREATE (g)-[:BACKHAUL]->(a)")
                
        print("\n✅ Topology successfully injected into Neo4j:")
        print("  - 1x Cisco Core Router")
        print("  - 2x Cisco ASR Aggregation Routers")
        print("  - 5x Ericsson gNodeBs (connected to ASR-1)")
        print("  - 5x Nokia gNodeBs (connected to ASR-2)")
        
    except Exception as e:
        print(f"❌ Neo4j setup failed: {e}")
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == "__main__":
    test_redis()
    setup_neo4j()
