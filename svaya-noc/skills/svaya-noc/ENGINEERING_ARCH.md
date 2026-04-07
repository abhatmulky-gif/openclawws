# Svaya Engineering Architecture: End-to-End Platform

## 1. High-Level Data Flow Diagram
```text
[ DEVICE EDGE ]                                 [ CLOUD INGESTION ]                        [ COGNITIVE CORE ]
+-------------------+                           +-------------------+                      +-------------------+
| Svaya QoE SDK     | ---- MQTT/gRPC (1hr) ---> | Time-Series DB    | -- Score < 50? ----> | Redis Event Bus   |
| (Passive Monitor) |                           | (Aggregator)      |                      | (Raw Alarms + QoE)|
| * Local Math      | ---- SOS PUSH (Drop) ---> |                   |                      +---------+---------+
+-------------------+                           +-------------------+                                |
                                                                                                   v
[ EXTERNAL IT / OSS ]                           [ THE KNOWLEDGE ]                          +-------------------+
+-------------------+                           +-------------------+                      | Svaya LLM Engine  |
| Network Elements  | ---- Syslog/Traps ------> | Neo4j AuraDB      | <--- Graph Context --| * Prompt Builder  |
| (Cisco, Ericsson) | <--- Active Probing ----- | (Live Topology)   |                      | * RCA Generator   |
+-------------------+                           +-------------------+                      +---------+---------+
                                                                                                   |
+-------------------+                           +-------------------+                              |
| Ticketing / Docs  | ---- Batch Ingest ------> | Vector DB (RAG)   | <--- Similarity Match -------+
| (ServiceNow, PDFs)|                           | (Past Incidents)  |                              |
+-------------------+                           +-------------------+                              v
                                                                                           [ OUTPUT / ACTION ]
                                                                                           +-------------------+
                                                                                           | NOC Telegram Bot  |
                                                                                           | / REST Webhook to |
                                                                                           | Orchestrator      |
                                                                                           +-------------------+
```

## 2. Component Specifications

### 2.1 The Edge: Svaya QoE Engine (Android SDK)
*   **Role:** The Ground-Truth Trigger.
*   **Security & DRM:** Device memory and local telemetry are protected via DRM. The SDK remains dormant until explicitly enabled by the operator. Encryption keys are managed dynamically *per network node*, with specific weightages assigned per node based on the expected volume of data to protect.
*   **Logic:** Runs passive, zero-impact collection via `TrafficStats` and `TelephonyManager`. QoE analysis is highly granular (computed *per cell*) and must be activated in tandem with the Svaya Cognitive Core. Computes composite score locally (RSRP + SINR + CQI + Throughput + Z-axis Barometer).
*   **Transmission:** Hourly 2KB batches to save battery. Bypasses batching to send instant "SOS Push" if QoE drops below threshold (e.g., < 30).

### 2.2 The State & Topology (IT Plumbing)
*   **Event Bus (Redis):** Ingests raw multi-vendor network alarms and SOS Pushes from the QoE SDK. 
*   **Topology Graph (Neo4j):** Maintains the physical/logical cross-vendor map. When an alarm hits, the engine pulls a 1-hop or 2-hop radius around the affected node.

### 2.3 The Cognitive Core (RAG + LLM)
*   **Knowledge Base (Vector DB):** Holds historical NOC tickets and vendor manuals. 
*   **The Brain (LLM):** Ingests the Trigger (QoE), the Context (Neo4j), and the History (Vector DB). 

### 2.4 The Synergy: Active Network Probing (The "Hunt")
The Svaya Cognitive Engine is not just a passive listener. When the QoE Engine fires an Emergency "SOS Push" (e.g., a boundary cluster in Indiranagar drops), the two engines collaborate in a proactive loop:
1.  **Target Identification:** The LLM uses the QoE Cell ID data to query Neo4j and isolate the exact blast radius (e.g., an Ericsson/Nokia boundary area connected to a specific Cisco router).
2.  **Active Polling:** Before traditional alarms even trigger in the NOC, Svaya actively queries the PM counters, logs, and interface statistics of the specific nodes in that radius.
3.  **Silent Fault Detection:** By pulling real-time state data based on user experience, Svaya detects "Silent Congestion" or configuration mismatches that standard threshold-based alarms miss.

## 3. Engineering for "Trust" (The Trust Architecture)
AI hallucinations are the #1 blocker in telecom. We engineer trust at the foundational level:
1.  **Explainability via RAG:** The LLM does not generate fixes from its latent training data. It is restricted to RAG output. Every RCA must cite its source (e.g., *"Recommended action based on historical ticket INC-4192"*).
2.  **Deterministic Topology:** The LLM does not guess network paths. It is mathematically constrained by the Neo4j Graph.
3.  **Confidence Scoring:** The engine outputs a confidence % based on Vector distance. Low confidence routes to a human; high confidence routes to auto-remediation.