import os
import time
import requests
import threading
from flask import Flask, request, jsonify
import xml.etree.ElementTree as ET

app = Flask(__name__)

# In-memory state for legacy PM counters
latest_pm_state = {"Bangalore_Sector_105": {"prb_util": 0}}

def poll_legacy_xml():
    """Background thread that mimics an SFTP poller reading 15-min XML files"""
    print("[INGESTION] Background XML Poller started...")
    while True:
        xml_path = "pm_data/PM_15min_latest.xml"
        if os.path.exists(xml_path):
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                for cell in root.findall('Cell'):
                    cid = cell.get('id')
                    prb = float(cell.find('PRBUtilization').text)
                    latest_pm_state[cid] = {"prb_util": prb}
            except Exception as e:
                pass
        time.sleep(2)

@app.route('/qoe_stream', methods=['POST'])
def qoe_stream():
    """Real-time endpoint receiving MQTT/HTTP payloads from the QoE SDK"""
    data = request.json
    cell_id = data.get("cell_id")
    ttfb = data.get("ttfb_ms", 0)
    stall = data.get("stall_ratio_pct", 0)
    
    prb = latest_pm_state.get(cell_id, {}).get("prb_util", 0)
    
    print(f"\n[INGESTION] Received telemetry for {cell_id} | TTFB: {ttfb}ms | Stall: {stall}% | PRB (from XML): {prb}%")
    
    # ---------------------------------------------------------
    # SURGE DETECTION LOGIC
    # If Bottom-Up (PRB > 85%) aligns with Top-Down (TTFB > 200ms)
    # ---------------------------------------------------------
    if ttfb > 200 and stall > 5 and prb > 85:
        print(f"[INGESTION] 🚨 CONGESTION SURGE DETECTED on {cell_id}!")
        print("[INGESTION] Generating TMF921 Declarative Intent...")
        
        # Build the TM Forum Intent
        intent_payload = {
          "id": f"intent_surge_{cell_id}_001",
          "intentExpectation": [
            {
              "expectationTarget": [
                {
                  "targetName": "TTFB_Latency",
                  "targetCondition": "less_than",
                  "targetValue": "200",
                  "unit": "ms"
                },
                {
                  "targetName": "Handover_Success_Rate",
                  "targetCondition": "greater_than",
                  "targetValue": "95",
                  "unit": "percentage"
                }
              ]
            }
          ],
          "intentContext": [
            {
              "contextAttribute": "Location",
              "contextValue": cell_id
            }
          ]
        }
        
        # Fire it to the Svaya Cognitive Core (backend.py on port 5000)
        try:
            print("[INGESTION] Pushing Intent to Svaya Cognitive Core...")
            res = requests.post("http://127.0.0.1:5000/tmf921/intent", json=intent_payload)
            print("\n[INGESTION] Svaya Cognitive Core Response:")
            print(res.json())
        except Exception as e:
            print("[INGESTION] ERROR: Could not contact Svaya Core at port 5000.", str(e))
            
    return jsonify({"status": "received"})

if __name__ == '__main__':
    # Start the XML polling thread
    threading.Thread(target=poll_legacy_xml, daemon=True).start()
    
    # Start the Flask app for real-time JSON on port 5001
    print("[INGESTION] Worker listening on port 5001 for QoE payloads...")
    app.run(host='0.0.0.0', port=5001)