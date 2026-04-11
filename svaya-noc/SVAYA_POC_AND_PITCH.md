# Svaya Cognitive Engine: Master Architecture, POC & Sales Pitch
*(Locked Version: TypeDB Hybrid AI Architecture)*

## 1. The Sales Pitch: Why Svaya Wins
Telecom operators are stuck between rigid "Expert Systems" (like RDFox) that require massive manual rule-coding, and unpredictable LLMs that hallucinate. 

**Svaya is the ultimate Hybrid Cognitive rApp.** It fuses the deterministic mathematical inference of a semantic knowledge graph (**TypeDB**) with the infinite flexibility and intent-parsing of Generative AI (**OpenClaw + LLM**).

*   **The Intent Advantage (TMF921):** Operators send declarative intents ("Maintain latency < 200ms"). Svaya handles the "how."
*   **The RDFox Advantage without the Cost:** By using TypeDB, Svaya infers network blast radiuses deterministically in milliseconds (e.g., *Rule: If router drops, infer all connected cells are isolated*). We get semantic reasoning without the proprietary, RAM-heavy enterprise licenses of RDFox.
*   **Cognition over Dumb Automation:** If a scenario is novel, the LLM reads unstructured vendor PDFs from the Vector DB (ChromaDB). If a past action failed, Svaya's closed-loop feedback remembers and pivots dynamically.
*   **Seamless Integration:** Svaya controls modern 5G cores via REST/NETCONF, but seamlessly automates legacy 2G/4G via SSH/CLI. No vendor API upgrade required.

---

## 2. Detailed Engineering Architecture

### A. Northbound Interface (The Intent Layer)
*   **Machine Track:** TMF921 Intent Management API. Orchestrators send standardized JSON payloads.
*   **Human Track:** Telegram NLP via OpenClaw. Engineers type plain English; Svaya translates to TMF921 schemas.

### B. The Cognitive Core (The Hybrid Brain)
*   **Knowledge Graph & Inference (TypeDB):** Replaces traditional property graphs. Defines strict telecom ontologies and runs real-time deterministic rules (e.g., hierarchical topology, fault propagation). Acts as the deterministic safety net.
*   **Vector Database (Chroma/Milvus):** The Semantic Memory. Stores unstructured vendor SOPs and "Learned Lessons" (Feedback Loop).
*   **LLM Gateway (Llama-3 via OpenClaw):** The fuzzy logic engine. Merges TypeDB's strict topology with ChromaDB's SOPs to generate a precise Method of Procedure (MOP).

### C. Southbound Interface (Execution & Confidence Wrapper)
*   **Hybrid Execution:** Python-based SSH/CLI automation (Netmiko) for legacy; REST/NETCONF for modern gear.
*   **Safety Pre-Flight & Closed Loop:** State capture before execution -> Execute -> Wait 3 mins -> Poll QoE SDK -> If intent failed, Auto-Rollback & write "Failure Lesson" to ChromaDB.

---

## 3. The Bangalore POC Definition
**Target:** 1,500 multi-RAT cells (2G, 4G, 5G) in a dense RF environment.

### POC Objectives:
1.  **Surge Mitigation:** Detect a TTFB surge via QoE SDK and dynamically adjust Call Admission Control (CAC).
2.  **Deterministic Inference:** Demonstrate TypeDB instantly inferring cell isolation when a simulated edge router drops, preventing the LLM from hallucinating fixes for dead cells.
3.  **Intent Learning:** Prove the system learns from a failed mitigation and pivots strategy using the TMF921 feedback loop.

---

## 4. Hardware Dimensioning & Costing

### A. The Bangalore POC (Single Server - 1,500 Cells)
*   **Option 1: Refurbished "Frankenstein" Lab Build (CapEx):** Off-lease 4U Enterprise Server (Dual Xeon/EPYC, 256GB RAM, NVMe) + 2x NVIDIA RTX 3090/4090 (48GB VRAM). 
    *   **Cost: ~$4,000 to $8,000 total.** (100% On-Premise, CISO approved).
*   **Option 2: Secure VPC Cloud (OpEx):** 1x RunPod A100 instance.
    *   **Cost: ~$1,000 to $1,500 / month.**

### B. Enterprise Scale Deployment (10,000+ Cells)
*   **Specs:** Dual AMD EPYC 9004, 512GB-1TB RAM, 20TB NVMe, 2x to 4x NVIDIA A100/H100.
*   **CapEx:** $67,500 to $177,500 per node (Open source DBs eliminate millions in software licensing).