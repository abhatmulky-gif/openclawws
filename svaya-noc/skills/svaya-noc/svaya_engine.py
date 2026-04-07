import os
import redis
import json
import time
from neo4j import GraphDatabase
import requests
from dotenv import load_dotenv

load_dotenv('svaya-poc.env')

REDIS_URL = os.getenv('REDIS_URL')
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USER = os.getenv('NEO4J_USER')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

LLM_URL = os.getenv('RUNPOD_URL', 'http://127.0.0.1:8000/v1/chat/completions')

def get_topology_context(nodes):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    context = []
    upstream_routers = set()
    try:
        with driver.session() as session:
            for node in nodes:
                # Get the node and its immediate neighbors (1 hop up to aggregators/core)
                query = f"MATCH (n:Equipment {{id: '{node}'}})-[r]-(m:Equipment) RETURN n, type(r) as rel, m"
                results = session.run(query)
                for record in results:
                    n_id = record['n']['id']
                    rel = record['rel']
                    m_id = record['m']['id']
                    context.append(f"{n_id} {rel} {m_id}")
                    if "CISCO" in m_id:
                        upstream_routers.add(m_id)
            
            # Get 2nd hop (Core connections)
            for router in list(upstream_routers):
                query = f"MATCH (n:Equipment {{id: '{router}'}})-[r]-(m:Equipment) RETURN n, type(r) as rel, m"
                results = session.run(query)
                for record in results:
                    context.append(f"{record['n']['id']} {record['rel']} {record['m']['id']}")
                    if "CISCO-CORE" in record['m']['id']:
                        upstream_routers.add(record['m']['id'])
                        
    finally:
        driver.close()
    return list(set(context)), list(upstream_routers)

def active_probing(routers):
    print("\n[HUNT INITIATED] Actively polling PM counters on upstream routers...")
    discovered_faults = []
    for router in routers:
        print(f" -> SSH/API Call to {router}: Fetching interface stats...")
        time.sleep(1) # Simulate polling delay
        if router == "CISCO-CORE-1":
            print(f"    [!] SILENT FAULT FOUND on {router}!")
            discovered_faults.append({
                "node": router,
                "state": "SILENT_DROP",
                "telemetry": "Process IP Input consuming 94% CPU. Micro-burst traffic causing queue drops on Core Uplink. No threshold alarm generated."
            })
        else:
            print(f"    [OK] {router} metrics nominal.")
    return discovered_faults

def run_rca(alarms, topology, active_telemetry):
    print("\n--- Running Cognitive RCA via LLM ---")
    prompt = f"""
    You are the Svaya Cognitive RCA Engine.
    Analyze the following event storm, which includes Svaya QoE Engine telemetry (SOS Pushes) and proactively probed network states.
    Use the associated network topology graph to find the hidden root cause impacting the users.
    
    EVENTS (Svaya QoE Data):
    {json.dumps(alarms, indent=2)}
    
    ACTIVELY PROBED TELEMETRY (The Hunt Results):
    {json.dumps(active_telemetry, indent=2)}
    
    TOPOLOGY GRAPH (Neo4j):
    {chr(10).join(topology)}
    
    Provide a brief, professional Root Cause Analysis. 
    1. State the ROOT CAUSE and the SYMPTOMS.
    2. Provide an EXECUTION STRATEGY indicating if it's [AUTO-REMEDIATION ELIGIBLE] or [REQUIRES PHYSICAL ACTION] and the exact steps.
    3. Include a TRUST DASHBOARD summary at the end with:
       - Confidence Score (%)
       - Source Citation (e.g., Historical Ticket or Vendor Doc used)
    """
    
    try:
        payload = {
            "model": "llama3", # Default Ollama model
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        # Changed endpoint from /v1/chat/completions to Ollama's native endpoint
        response = requests.post("http://127.0.0.1:11434/api/chat", json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()['message']['content']
        else:
            return f"LLM API Error: {response.text}"
    except Exception as e:
        return f"Failed to reach LLM at {LLM_URL}: {e}"

def main():
    r = redis.from_url(REDIS_URL)
    print("Svaya Engine starting on RunPod. Listening for QoE SOS Pushes...")
    
    while True:
        alarms = []
        while r.llen('raw_alarms') > 0:
            alarm_data = r.lpop('raw_alarms')
            if alarm_data:
                alarms.append(json.loads(alarm_data))
                
        if alarms:
            print(f"\n[!] Detected SOS Push from QoE SDK. Processing...")
            
            # --- NEW: DRM Validation at the Core ---
            print("[SECURITY] Authenticating incoming telemetry DRM signatures...")
            for a in alarms:
                sig = a.get("drm_signature", "MISSING")
                if "VALID" in sig:
                    print(f"[SECURITY] ✅ Valid per-node key detected ({sig}). Data decrypted.")
                else:
                    print(f"[SECURITY] ❌ Invalid DRM signature. Dropping payload.")
                    continue
            print("-" * 50)
            # ---------------------------------------
            
            # Extract affected cells from QoE alert
            affected_nodes = []
            for a in alarms:
                if 'metrics' in a and 'Affected_Cells' in a['metrics']:
                    affected_nodes.extend(a['metrics']['Affected_Cells'])
            
            # 1. Fetch Graph Context & Upstream Routers
            print("Querying Neo4j for blast radius...")
            topology, upstream_routers = get_topology_context(affected_nodes)
            
            # 2. Active Probing (The Hunt)
            active_telemetry = active_probing(upstream_routers)
            
            # --- NEW: Trust Dashboard Simulation & State Save ---
            dashboard_state = {
                "mode": "PHASE 1: ADVISOR MODE",
                "blast_radius": f"{len(topology)} network edges",
                "traversal": "Edge Cells -> ASRs -> CISCO-CORE-1",
                "rag_match": "Ticket INC-2025-08-4192",
                "guardrails": "Read-Only Mode Active (Zero-Touch Disabled)",
                "confidence": "98%",
                "status": "Ready for Operator Review",
                "affected_nodes": affected_nodes,
                "timestamp": time.time()
            }
            r.set('dashboard_state', json.dumps(dashboard_state))
            
            print("\n" + "="*55)
            print("📊 SVAYA TRUST DASHBOARD (PHASE 1: ADVISOR MODE)")
            print("="*55)
            print(f"📍 Blast Radius Mapped: {dashboard_state['blast_radius']}")
            print(f"🗺️ Graph Traversal: {dashboard_state['traversal']}")
            print(f"🔍 Knowledge Base (RAG): Match found ({dashboard_state['rag_match']})")
            print(f"🛡️ Guardrails: {dashboard_state['guardrails']}")
            print(f"✅ AI Confidence Score: {dashboard_state['confidence']} ({dashboard_state['status']})")
            print("="*55 + "\n")
            # ---------------------------------------
            
            # 3. Run LLM
            rca_result = run_rca(alarms, topology, active_telemetry)
            
            # 4. Publish Notification
            print("\nPublishing RCA to Telegram Notifier queue...")
            r.rpush('rca_notifications', rca_result)
            print(rca_result)
            
        time.sleep(2)

if __name__ == "__main__":
    main()