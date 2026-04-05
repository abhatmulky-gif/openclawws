#!/bin/bash
echo "========================================="
echo " SVAYA NOC + OPENCLAW DEPLOYMENT SCRIPT  "
echo "========================================="

# 1. Update OS and Install Node.js for OpenClaw
echo "[*] Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 2. Install OpenClaw
echo "[*] Installing OpenClaw..."
npm install -g openclaw

# 3. Install Python Dependencies
echo "[*] Installing Python Libraries..."
pip install -r requirements.txt

# 4. Install Ollama and start it
echo "[*] Installing Ollama Natively..."
curl -fsSL https://ollama.com/install.sh | sh
echo "[*] Starting Ollama Server in background..."
ollama serve > ollama.log 2>&1 &
sleep 5

# 5. Pull Llama 3 Model
echo "[*] Pulling Llama 3..."
ollama pull llama3

# 6. Create RAG Ingestion Script
echo "[*] Building Vector DB Knowledge Base..."
python ingest.py

# 7. Start Flask Backend
echo "[*] Starting AI Correlation API..."
python backend.py > flask.log 2>&1 &
sleep 3

# 8. Setup OpenClaw Workspace & Skill
echo "[*] Configuring OpenClaw NOC Skill..."
mkdir -p ~/.openclaw/workspace/skills/svaya-noc/scripts

cp SKILL.md ~/.openclaw/workspace/skills/svaya-noc/SKILL.md
cp scripts/analyze.py ~/.openclaw/workspace/skills/svaya-noc/scripts/analyze.py

echo "========================================="
echo " DEPLOYMENT COMPLETE!                    "
echo "========================================="
echo ""
echo "Next Steps:"
echo "1. Run: openclaw setup"
echo "2. Run: openclaw start"
echo "3. Text your bot: 'Analyze this alarm storm: 10x Ericsson S1 Link Down, Cisco ASR Gi0/0/1 Down'"
