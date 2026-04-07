# Svaya Technical Sales & Commercial Playbook

## 1. The Core Identity: What is Svaya?
Svaya is a **QoE-Driven Cognitive RCA Platform**. We do not just monitor hardware; we monitor actual user experience at the edge, correlate it against a live multi-vendor network graph, and use Local AI (LLMs + RAG) to prescribe exact fixes. 

**Our tagline:** *Stop monitoring routers. Start protecting revenue.*

---

## 2. The Product Suite
We go to market with two intertwined products:
1. **Svaya QoE Edge (The Sensor):** A lightweight Android SDK embedded in the operator's existing customer app (e.g., "My Jio"). It passively computes a composite QoE score directly on the device on a *per-cell* basis. **Security is paramount:** Device telemetry memory is DRM-protected, utilizing per-network-node encryption keys (weighted by data volume), and remains completely dark until the operator explicitly enables it alongside the Svaya Core.
2. **Svaya Cognitive Core (The Brain):** An LLM-native orchestrator that ingests the QoE SOS, queries the network topology (Neo4j), actively probes the suspect routers (Cisco, Ericsson, Nokia) for silent faults, and generates an actionable Root Cause Analysis.

---

## 3. The Business Model: How We Monetize
We utilize a **Land and Expand SaaS Model**, structured around building trust with risk-averse telecom CTOs.

### The Pricing Structure
* **Platform Base Fee:** Flat annual fee for the Cognitive Core, Neo4j Topology Engine, and Vector DB ingestion (bringing their manuals and historical tickets into the AI).
* **Sensor Licensing (Volume-based / Phase 1 Guarantee):** Tiered pricing based on the number of active QoE SDK devices monitored. **Crucially, during Phase 1, we offer a Performance Guarantee:** We only charge the Sensor License fee if the Trust Dashboard proves the AI's Root Cause Accuracy is >95%. If we miss the mark, the pilot is free. This completely de-risks the commercial engagement for the operator.
* **Autopilot Premium (Upsell):** Once the customer upgrades from "Advisor" (read-only) to "Autopilot" (zero-touch closed-loop remediation), we charge a premium for active network write-access.

### The 3-Phase "Trust" Rollout Strategy (Crucial for Sales)
Telcos will not buy a "Black Box AI" that changes configurations on Day 1. You must pitch the Trust Journey:
* **Phase 1: The Advisor & The Trust Dashboard (Months 1-3).** Svaya is strictly read-only and geo-fenced to minimize the blast radius (e.g., deployed only in one specific city like Bangalore, or targeting a single non-critical network domain). Operators interact with the **Trust Dashboard**, a UI designed specifically to open the "Black Box." It visually displays the AI's Confidence Score, the exact Neo4j graph path the AI traversed, and side-by-side citations of the historical tickets it used to reach its conclusion. *Goal: Build human confidence and prove 99% RCA accuracy in a controlled, low-risk environment.*
* **Phase 2: The Co-Pilot (Months 3-6).** Svaya pre-writes the configuration patch (e.g., QoS update for a Cisco router). A human engineer reviews it and clicks "Approve."
* **Phase 3: Autopilot (Month 6+).** For validated fault types (e.g., micro-burst congestion), Svaya executes the fix instantly without human intervention. 

---

## 4. The ROI & OPEX Savings (The CTO Pitch)
*Critical Note: We are NOT pitching headcount reduction. Human efficiency and error reduction are byproducts. Our core pricing justification is based purely on hard OPEX savings and uncovering blind spots.*

### A. Uncovering the "Invisible" Network (New Visibility)
* **What we uncover:** Silent faults, micro-bursts, and indoor "Structural Shadows."
* **The OPEX Save:** **Elimination of Drive Testing.** You no longer need to roll $100,000 drive-test vans or dispatch field engineers to hunt for dead zones. 50 million customer devices act as your continuous, automated audit fleet.

### B. Slashing Cross-Domain MTTR (War Room Elimination)
* **What we uncover:** The exact boundary where a Cisco transport issue drops an Ericsson radio.
* **The OPEX Save:** **War Room Efficiency.** NOC engineers currently spend hours pointing fingers between the RAN, Transport, and Core teams. Svaya correlates the multi-vendor graph in seconds, giving your existing engineers the exact root cause so they can act immediately. We empower the NOC to fix things faster, not replace them.

### C. SLA Penalty & Churn Prevention (Revenue Protection)
* **What we uncover:** VIP and Enterprise experience degradation *before* they call the complaint desk.
* **The OPEX Save:** **SLA Protection.** By triggering on QoE drops instead of waiting for a total hardware failure, operators can mitigate congestion before breaching Enterprise SLAs or losing high-ARPU premium subscribers.

### D. Optimizing Existing Asset Utilization
* **What we uncover:** Whether a drop in quality is a software/config issue or a true capacity limit.
* **The OPEX Save:** **CAPEX Deferral.** Operators often buy new hardware to fix slow networks. Svaya’s LLM identifies if the issue can be fixed via a generated QoS script or parameter tuning, maximizing the efficiency of existing hardware before spending CAPEX on new boxes.

---

## 5. Overcoming Key Technical Objections

**Objection 1: "We don't want our data going to OpenAI."**
* **Rebuttal:** "Svaya is strictly Sovereign AI. We deploy open-source LLMs (like Llama 3) natively within your private cloud/data center using Ollama or vLLM. No network telemetry ever leaves your perimeter."

**Objection 2: "AI hallucinates. We can't trust it."**
* **Rebuttal:** "We don't use raw LLM generation. Svaya uses Graph RAG. The AI is mathematically constrained by the Neo4j network topology, and it must cite its sources (your own historical ServiceNow tickets or vendor PDFs) for every recommendation."

**Objection 3: "It will take 2 years to integrate with our legacy OSS."**
* **Rebuttal:** "Svaya is a Zero-Integration Brownfield platform. We don't need you to build custom vendor APIs. We ingest standard syslogs and read your existing ticketing system. We overlay your network; we don't replace it."

**Objection 4: "We cannot risk putting a 3rd party SDK on millions of customer devices. What about data privacy and security?"**
* **Rebuttal:** "The Svaya SDK telemetry is locked down via DRM. Local memory is encrypted using per-node dynamic keys, weighted by expected data volumes. The SDK remains completely dormant until you, the operator, explicitly authenticate and enable it per cell in tandem with the Svaya Core. You hold the keys; we just provide the math."