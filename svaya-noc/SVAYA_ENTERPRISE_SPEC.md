# Svaya Cognitive Engine: Enterprise Hardware & Integration Specification
*(TypeDB Open-Source Edition)*

## 1. Hardware Architecture & Dimensioning
This specification dimensioning supports the hybrid AI model: OpenClaw orchestration, TypeDB for deterministic semantic inference, ChromaDB for vector memory, and LLM reasoning.

### The "Svaya AI Node" (Production Spec for 10,000+ Cells)
*   **Compute (CPU):** Dual AMD EPYC 9004 series or Intel Xeon Platinum (64 to 128 Cores) for Kafka stream processing and Time-Series indexing.
*   **Memory (RAM):** 512GB to 1TB DDR5. (Significantly less than RDFox deployments, as TypeDB uses disk-backed storage with RAM caching).
*   **Storage (Disk):** 10TB to 20TB NVMe SSDs (PCIe Gen 4/5) in RAID 10. Critical for TypeDB, Time-Series data, and Vector Embeddings.
*   **AI Compute (GPU):** 2x to 4x NVIDIA A100 (80GB) or H100 GPUs. For sub-second Llama-3 70B inference.
*   **Networking:** Dual 100Gbps NICs.

---

## 2. Cost Analysis

### Option 1: On-Premise / Bare Metal (CapEx)
*Preferred for Data Sovereignty and strict telecom privacy compliance.*
*   **Chassis & Base System:** ~$15,000
*   **CPUs:** ~$12,000
*   **RAM:** ~$5,000
*   **Storage:** ~$4,000
*   **Networking:** ~$1,500
*   **GPUs:** $30,000 to $140,000 (A100 vs H100 configurations)
*   **Software Licensing:** $0 (TypeDB, ChromaDB, OpenClaw, Llama-3 are all open-source, saving millions compared to RDFox/Neo4j Enterprise).
*   **Total Estimated CapEx per Node:** **$67,500 to $177,500**.

### Option 2: Cloud / GPU Rental (OpEx)
*   **AWS (p4d.24xlarge / 8x A100):** ~$23,000 / month (On-Demand).
*   **RunPod (4x A100):** ~$5,000 to $7,200 / month.

### Option 3: Lean POC Build (Bangalore 1,500 Cells)
*   **Hardware:** Refurbished 4U Server with 2x NVIDIA RTX 3090/4090 (48GB VRAM total).
*   **Total Estimated CapEx:** **$4,000 to $8,000**.

---

## 3. Operator Interface Specification (Integration Points)

### A. Telemetry & Fault Ingestion (Read-Only)
*   **Modern Streaming:** gRPC / Kafka topics (Protobuf/JSON).
*   **Legacy PM (TS 32.432):** SFTP pulling 15-minute XML/CSV files.
*   **Fault Management:** SNMPv3 Traps or VES over REST.

### B. Execution & Configuration (Write-Access)
*   **Legacy Automation:** CLI / SSH (Netmiko/NAPALM) for execution on API-less legacy hardware.
*   **Modern Control:** NETCONF (RFC 6241) / YANG or EMS REST APIs.

### C. Northbound Intent & Orchestration
*   **Machine Interface:** TMF921 Intent Management API (JSON).
*   **Human Interface:** OpenClaw Telegram Plugin (NLP).

### D. User QoE SDK Interface
*   **Handset Telemetry:** MQTT over TLS or HTTPS POST (TTFB, DNS Latency, Stall Ratios).