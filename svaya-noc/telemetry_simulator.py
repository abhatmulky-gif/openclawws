import os
import time
import json
import requests
import xml.etree.ElementTree as ET

# Ensure directory exists for PM files
os.makedirs("pm_data", exist_ok=True)

def generate_pm_xml(prb_utilization):
    """Simulates 15-minute legacy PM XML counter drop from an EMS"""
    root = ET.Element("PMSetup")
    cell = ET.SubElement(root, "Cell", id="Bangalore_Sector_105")
    ET.SubElement(cell, "PRBUtilization").text = str(prb_utilization)
    ET.SubElement(cell, "ActiveRRCUsers").text = "850" if prb_utilization > 85 else "300"
    
    tree = ET.ElementTree(root)
    file_path = "pm_data/PM_15min_latest.xml"
    tree.write(file_path)
    print(f"[SIMULATOR] Wrote Legacy PM XML (PRB: {prb_utilization}%) to {file_path}")

def stream_qoe_payload(ttfb, stall_ratio):
    """Simulates real-time JSON payload from the mobile QoE SDK"""
    payload = {
        "cell_id": "Bangalore_Sector_105",
        "ttfb_ms": ttfb,
        "stall_ratio_pct": stall_ratio,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    try:
        # Pushing to our Ingestion Worker (running on port 5001)
        requests.post("http://127.0.0.1:5001/qoe_stream", json=payload)
        print(f"[SIMULATOR] Streamed QoE JSON (TTFB: {ttfb}ms, Stall: {stall_ratio}%)")
    except Exception as e:
        print("[SIMULATOR] Failed to stream QoE. Is ingestion_worker.py running on port 5001?")

if __name__ == "__main__":
    print("=== SVAYA MULTI-RAT TELEMETRY SIMULATOR ===")
    
    print("\n--- 1. Simulating NORMAL Network State ---")
    generate_pm_xml(prb_utilization=65.0)
    time.sleep(1)
    stream_qoe_payload(ttfb=110, stall_ratio=1.5)
    time.sleep(3)
    
    print("\n--- 2. Simulating SURGE Network State ---")
    print("A massive crowd just entered Bangalore_Sector_105...")
    generate_pm_xml(prb_utilization=94.5)
    time.sleep(1)
    stream_qoe_payload(ttfb=280, stall_ratio=8.2)
    
    print("\n[SIMULATOR] Done generating events.")