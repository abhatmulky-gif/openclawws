import os
import redis
import json
import time
from dotenv import load_dotenv

# Load env
env_path = os.path.join(os.path.dirname(__file__), 'svaya-poc.env')
load_dotenv(env_path)

REDIS_URL = os.getenv('REDIS_URL')

def simulate_storm():
    r = redis.from_url(REDIS_URL)
    
    print("Initiating Alarm Storm Simulation: Cisco ASR-1 Failure...")
    
    # 1. The Root Cause Event (happens first, but might be buried in logs)
    rc_alarm = {
        "timestamp": time.time(),
        "node": "CISCO-ASR-1",
        "vendor": "Cisco",
        "severity": "CRITICAL",
        "message": "SYS-2-MOD_DOWN: Line card 0/1 went down. Power failure detected."
    }
    r.rpush('raw_alarms', json.dumps(rc_alarm))
    print(f"Sent: {rc_alarm['node']} - {rc_alarm['message']}")
    
    time.sleep(1) # Slight delay
    
    # 2. The Symptom Storm (All 5 Ericsson gNBs lose backhaul)
    for i in range(1, 6):
        sym_alarm = {
            "timestamp": time.time(),
            "node": f"ERIC-gNB-{i}",
            "vendor": "Ericsson",
            "severity": "MAJOR",
            "message": "S1/X2 Interface Link Down - Gateway unreachable."
        }
        r.rpush('raw_alarms', json.dumps(sym_alarm))
        print(f"Sent: {sym_alarm['node']} - {sym_alarm['message']}")
        time.sleep(0.2)
        
    print("\nStorm published to Redis queue 'raw_alarms'!")

if __name__ == "__main__":
    simulate_storm()
