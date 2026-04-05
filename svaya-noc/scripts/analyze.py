import argparse
import requests
import sys

# Replace this with the Ngrok URL you get from your RunPod terminal
# e.g., "https://abc-123.ngrok.app/analyze_alarm"
RUNPOD_URL = "https://effort-pottery-mate-waves.trycloudflare.com/analyze"

def analyze():
    parser = argparse.ArgumentParser(description="Svaya Networks AI NOC Correlator")
    parser.add_argument("--alarm", type=str, required=True, help="The raw telecom alarm(s) to analyze")
    args = parser.parse_args()
    
    print(f"[*] Sending alarm stream to Svaya AI Engine on RunPod GPU...")
    print(f"    Target: {RUNPOD_URL}\n")
    
    try:
        # We send it as a single element in the alarms list so the backend correlation works
        response = requests.post(RUNPOD_URL, json={"alarms": [args.alarm]}, timeout=30)
        
        if response.status_code != 200:
            print(f"HTTP Error {response.status_code}: {response.text}")
            sys.exit(1)
            
        result = response.json().get("analysis", "Error in analysis returned by LLM.")
        print("==============================")
        print("  SVAYA AI ROOT CAUSE (RCA)   ")
        print("==============================\n")
        print(result)
        print("\n==============================")
        
    except requests.exceptions.ConnectionError:
        print("[!] FATAL: Could not connect to the RunPod Engine. Make sure ngrok is running on the pod and the RUNPOD_URL is updated in this script.")
    except Exception as e:
        print(f"[!] Unexpected error: {e}")

if __name__ == "__main__":
    analyze()