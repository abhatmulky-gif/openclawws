# Svaya POC RunPod Deployment Guide
*(Complete Step-by-Step for the Hybrid TypeDB + ChromaDB + LLM Architecture)*

This guide walks through deploying the complete Svaya Cognitive Engine POC on a fresh RunPod instance.

---

## Phase 1: Environment Setup on RunPod

1. **Deploy Pod:** Spin up a 1x RTX 4090 or RTX A6000 pod using the "RunPod Pytorch" template. Ensure ports `5000`, `5001`, and `1729` are exposed.
2. **Open Terminal:** Launch Jupyter Lab or the Web Terminal.
3. **Install Python Dependencies:**
   ```bash
   pip install flask chromadb requests typedb-driver
   ```

## Phase 2: Install and Start Infrastructure

### A. Ollama (The LLM Engine)
1. Install Ollama:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```
2. Start the server in the background:
   ```bash
   ollama serve &
   ```
3. Pull the model (takes ~2 mins):
   ```bash
   ollama run llama3
   ```
   *(Press `Ctrl+D` to exit the chat prompt once it loads).*

### B. TypeDB (The Knowledge Graph & Reasoning Engine)
1. Download and extract TypeDB:
   ```bash
   wget https://github.com/vaticle/typedb/releases/download/2.28.0/typedb-all-mac-linux-2.28.0.zip
   unzip typedb-all-mac-linux-2.28.0.zip
   cd typedb-all-mac-linux-2.28.0
   ```
2. Start the TypeDB server in the background:
   ```bash
   ./typedb server &
   ```
3. *(Optional)* Download **TypeDB Studio** on your local laptop to visually explore the graph later.

---

## Phase 3: Initialize the Data (The Brain's Memory)

1. **Initialize Vector Memory (ChromaDB):**
   Run the ingestion script to load Telecom SOPs and Intent logic into the vector database.
   ```bash
   python ingest.py
   ```
2. **Initialize Knowledge Graph (TypeDB):**
   Run the topology script to build the physical network graph and load the deterministic inference rules.
   ```bash
   python topology_typedb.py
   ```

---

## Phase 4: Run the Simulation (The Closed Loop)

You will need **three separate terminal tabs** open to see the architecture talk to itself.

1. **Terminal 1 (The Cognitive Core):**
   Start the main brain that listens for TMF921 Intents and talks to the LLM.
   ```bash
   python backend.py
   ```

2. **Terminal 2 (The Ingestion Worker / TMF921 Translator):**
   Start the worker that listens to network data and generates Intents when a surge hits.
   ```bash
   python ingestion_worker.py
   ```

3. **Terminal 3 (The Live Network Trigger):**
   Execute the simulator. It will generate a normal state, wait, and then blast a massive traffic surge (High TTFB, High PRB) into Bangalore Sector 105.
   ```bash
   python telemetry_simulator.py
   ```

### What to watch for:
*   Watch **Terminal 2** detect the surge and fire the TMF921 JSON Intent.
*   Watch **Terminal 1** receive the intent, query the databases, and output the exact parameter tuning MOP (e.g., CAC Throttling or `a3Offset` adjustments) based on the learned logic!