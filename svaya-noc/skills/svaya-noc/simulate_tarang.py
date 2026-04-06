import os
import redis
import json
import time
from dotenv import load_dotenv

# Load env
env_path = os.path.join(os.path.dirname(__file__), 'svaya-poc.env')
load_dotenv(env_path)

REDIS_URL = os.getenv('REDIS_URL')

def simulate_tarang_trigger():
    r = redis.from_url(REDIS_URL)
    
    print("Initiating Tarang.ai QoE Trigger Simulation...")
    
    # 1. Tarang SDK detects massive signal drop from premium users (The Trigger)
    qoe_alert = {
        "timestamp": time.time(),
        "source": "Tarang_SDK",
        "type": "QoE_DEGRADATION",
        "severity": "CRITICAL",
        "location": "Electronic City, Tech Park, Floor 4",
        "affected_users": 42,
        "metrics": {"RSRP": "-126dBm", "SINR": "-8dB", "Barometer_Z": "12m", "PCI": "ERIC-gNB-3"},
        "message": "Cluster of Premium Users experiencing complete data stall and VoLTE drops. Structural Shadow or Silent Sector Failure."
    }
    r.rpush('raw_alarms', json.dumps(qoe_alert))
    print(f"Sent: Tarang QoE Alert mapped to Cell: {qoe_alert['metrics']['PCI']}")
    
    time.sleep(2) # Delay to simulate network catching up to user experience
    
    # 2. The hidden network alarms that the NOC missed (The Root Cause)
    rc_alarm = {
        "timestamp": time.time(),
        "node": "CISCO-ASR-1",
        "vendor": "Cisco",
        "severity": "MINOR", # NOC ignored this because it was minor
        "message": "SYS-3-CPUHOG: Process IP Input consuming 92% CPU. Micro-burst traffic causing intermittent queue drops on Gi0/1."
    }
    r.rpush('raw_alarms', json.dumps(rc_alarm))
    print(f"Sent: {rc_alarm['node']} - {rc_alarm['message']}")
    
    print("\nTarang-triggered storm published to Redis queue 'raw_alarms'!")

if __name__ == "__main__":
    simulate_tarang_trigger()
