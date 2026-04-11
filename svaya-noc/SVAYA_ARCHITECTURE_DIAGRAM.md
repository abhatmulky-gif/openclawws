# Svaya Cognitive RCA & SON Engine
## Architecture Diagram (TypeDB Hybrid Edition)

```text
=========================================================================================
                              NORTHBOUND INTERFACES (The "What")
=========================================================================================
  [ 👨‍💻 NOC Engineers ]                            [ 🏢 Operator Umbrella Orchestrator ]
           │                                                    │
    (Plain English via Telegram)                     (Standardized JSON Payload)
           │                                                    │
           ▼                                                    ▼
[ OpenClaw Telegram Plugin ]                    [ TMF921 Intent Management API ]
=========================================================================================
                               SVAYA COGNITIVE CORE (OpenClaw)
=========================================================================================
                             │                                  │
                             ▼                                  ▼
                ┌────────────────────────────────────────────────────────┐
                │             OPENCLAW AI ORCHESTRATION LAYER            │
                │                                                        │
                │  1. Intent Parser & Translation (LLM Prompting)        │
                │  2. RAG Orchestrator (Context Gathering)               │
                │  3. Execution Planner (MOP Generation)                 │
                └──────┬────────────────────────┬─────────────────┬──────┘
                       │                        │                 │
            (Deterministic Inference)   (Memory Query)     (Metric Query)
                       │                        │                 │
                       ▼                        ▼                 ▼
             [ Knowledge Graph ]        [ Vector Database ] [ Time-Series DB ]
             (TypeDB: Ontologies &      (Chroma: SOPs &     (InfluxDB/Postgres:
              Rules-Based Inference)     Learned Lessons)    Live QoE/PM Metrics)
                       │                        ▲                 ▲
=======================│========================│=================│======================
                       │ (Closed Loop Feedback) │                 │
                       └────────────────────────┘                 │
                                                                  │
              ┌──────────────────────────┐           ┌────────────┴─────────────┐
              │ OPENCLAW EXECUTION LAYER │           │ HIGH-THROUGHPUT INGESTION│
              │   (Skills / Scripts)     │           │   (Kafka / Redis Bus)    │
              └──────┬────────────┬──────┘           └────▲────────▲────────▲───┘
                     │            │                       │        │        │
=====================│============│=======================│========│========│============
                     │            │                       │        │        │
          (API Call) │            │ (SSH / CLI)  (MQTT/JSON) (SFTP/XML) (SNMP/gRPC)
                     │            │                       │        │        │
                     ▼            ▼                       │        │        │
=========================================================================================
                            SOUTHBOUND INTERFACES (The Network)
=========================================================================================
          [ Modern 5G EMS ]  [ Legacy 2G/4G ]        [ UE ]   [ Legacy EMS ] [ 5G Core ]
          (NETCONF / REST)   (Ericsson/Cisco)     (QoE SDK)   (PM XMLs)      (Telemetry)
=========================================================================================
```

## Core Upgrades in this Version:
*   **TypeDB Replaces Neo4j:** Moves from dumb traversal to deterministic semantic reasoning. Provides RDFox-like inference (e.g., auto-deducing blast radiuses via rules) while remaining fully open-source and avoiding extreme RAM costs.
*   **Hybrid AI Safety Net:** TypeDB acts as the mathematical anchor, ensuring the LLM cannot hallucinate physical network topologies.