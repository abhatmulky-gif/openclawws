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

# NOTE: Adjust this based on your RunPod LLM's API (e.g., Ollama, vLLM, standard OpenAI compatible)
LLM_URL = os.getenv('RUNPOD_URL', 'http://127.0.0.1:8000/v1/chat/completions')

def get_topology_context(nodes):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    context = []
    try:
        with driver.session() as session:
            for node in nodes:
                # Get the node and its immediate neighbors (1 hop)
                query = f"MATCH (n:Equipment {{id: '{node}'}})-[r]-(m:Equipment) RETURN n, type(r) as rel, m"
                results = session.run(query)
                for record in results:
                    n_id = record['n']['id']
                    rel = record['rel']
                    m_id = record['m']['id']
                    context.append(f"{n_id} {rel} {m_id}")
    finally:
        driver.close()
    return list(set(context)) # deduplicate

def run_rca(alarms, topology):
    print("\n--- Running Cognitive RCA via LLM ---")
    prompt = f"""
    You are the Svaya Cognitive RCA Engine.
    Analyze the following telecom alarm storm and the associated network topology to determine the root cause.
    
    ALARMS:
    {json.dumps(alarms, indent=2)}
    
    TOPOLOGY GRAPH (Neo4j):
    {chr(10).join(topology)}
    
    Provide a brief, professional Root Cause Analysis. Clearly state the ROOT CAUSE and the SYMPTOMS.
    """
    
    try:
        # Assuming OpenAI-compatible endpoint on RunPod
        payload = {
            "model": "svaya-model", # Update to your model name if required
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300
        }
        headers = {"Content-Type": "application/json"}
        # If your runpod needs an auth token, add it here
        
        response = requests.post(LLM_URL, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"LLM API Error: {response.text}"
    except Exception as e:
        return f"Failed to reach LLM at {LLM_URL}: {e}"

def main():
    r = redis.from_url(REDIS_URL)
    print("Svaya Engine starting on RunPod. Listening for alarm storms...")
    
    while True:
        # Block and wait for alarms
        alarms = []
        # Pop all available alarms currently in the queue
        while r.llen('raw_alarms') > 0:
            alarm_data = r.lpop('raw_alarms')
            if alarm_data:
                alarms.append(json.loads(alarm_data))
                
        if alarms:
            print(f"\n[!] Detected Storm of {len(alarms)} alarms. Processing...")
            affected_nodes = [a['node'] for a in alarms]
            
            # 1. Fetch Graph Context
            print("Querying Neo4j for topology context...")
            topology = get_topology_context(affected_nodes)
            
            # 2. Run LLM
            rca_result = run_rca(alarms, topology)
            
            # 3. Publish Notification
            print("Publishing RCA to Telegram Notifier queue...")
            r.rpush('rca_notifications', rca_result)
            
        time.sleep(2) # Polling interval

if __name__ == "__main__":
    main()
