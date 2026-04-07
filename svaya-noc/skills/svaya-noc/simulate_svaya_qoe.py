import os
import redis
import json
import time
from dotenv import load_dotenv

# Load env
env_path = os.path.join(os.path.dirname(__file__), 'svaya-poc.env')
load_dotenv(env_path)

REDIS_URL = os.getenv('REDIS_URL')

def simulate_qoe_trigger():
    r = redis.from_url(REDIS_URL)
    
    print("Initiating Svaya QoE Engine 'SOS Push' (Indiranagar Scenario)...")
    
    # --- NEW: DRM & Security Handshake Simulation ---
    print("[SECURITY] Checking DRM activation status for local cells...")
    time.sleep(1)
    cells = ["ERIC-gNB-1", "NOK-gNB-1"]
    for cell in cells:
        print(f"[SECURITY] Requesting per-node DRM key for {cell} (Weightage: High Volume)")
        time.sleep(0.5)
        print(f"[SECURITY] ✅ Key verified. Telemetry unlocked for {cell} by Operator Core.")
    print("-" * 50)
    # ------------------------------------------------
    
    # The SDK detects a massive throughput drop from users on the boundary of Ericsson and Nokia
    qoe_alert = {
        "timestamp": time.time(),
        "source": "Svaya_QoE_SDK",
        "type": "SOS_PUSH_DEGRADATION",
        "severity": "CRITICAL",
        "location": "Indiranagar Boundary Area",
        "affected_users": 15,
        "drm_signature": "VALID_PER_NODE_KEY_0xA9F4",
        "metrics": {
            "RSRP": "-85dBm", 
            "SINR": "18dB", 
            "Throughput": "0 kbps", 
            "Affected_Cells": cells
        },
        "message": "Users experiencing complete data stall despite excellent RF conditions. Triggering active hunt."
    }
    r.rpush('raw_alarms', json.dumps(qoe_alert))
    print(f"Sent: SOS Push from Indiranagar. Affected Cells: {qoe_alert['metrics']['Affected_Cells']}")
    
    # Notice we DO NOT send a Cisco alarm. The Cognitive Engine will have to "hunt" for it.
    print("\nSvaya QoE trigger published to Redis queue 'raw_alarms'!")

if __name__ == "__main__":
    simulate_qoe_trigger()