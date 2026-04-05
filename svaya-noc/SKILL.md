---
name: svaya-noc
description: Interact with the Svaya Networks AI Engine on RunPod to analyze 5G telecom alarms, perform cross-vendor root cause analysis (RCA), and correlate alarm storms.
---

# Svaya NOC Skill

This skill allows the agent to communicate with the Svaya AI Engine running natively on a RunPod GPU.

## Usage
When the user asks to analyze an alarm or check an alarm storm, use the `scripts/analyze.py` tool.
Pass the raw alarm text using the `--alarm` flag. If the user provides multiple alarms, you can call it multiple times or combine them.

### Analyze a single alarm
```bash
python C:\Users\smitakudva\.openclaw\workspace\skills\svaya-noc\scripts\analyze.py --alarm "CRITICAL: Ericsson gNodeB Sector 2 - X2 Link Failure"
```

### Analyze a correlated storm
```bash
python C:\Users\smitakudva\.openclaw\workspace\skills\svaya-noc\scripts\analyze.py --alarm "MAJOR: eNodeB ENB-101 S1 Link Down. CRITICAL: Cisco ASR-9000 Interface Gi0/0/1 state DOWN."
```

## Setup Note
Ensure the `RUNPOD_URL` in `scripts/analyze.py` is updated to point to the live RunPod endpoint (or Ngrok URL) where the Flask API is hosted.