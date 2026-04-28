#!/bin/bash
# terraform/user_data.sh
# Cloud-Init script — runs on EC2 first boot
# Installs: Ollama, RAG dependencies, downloads GGUF from S3, configures services

set -e

echo "====== E-commerce BI Chatbot Provisioning ======"
echo "Started at: $(date)"

# ──────────────────────────────────────────────────────────────
# 1. System Updates & Core Dependencies
# ──────────────────────────────────────────────────────────────
echo "[1/8] Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    curl \
    wget \
    git \
    jq \
    python3 \
    python3-pip \
    python3-venv \
    awscli \
    ufw \
    &>/dev/null

echo "[1/8] Done"

# ──────────────────────────────────────────────────────────────
# 2. Install Ollama
# ──────────────────────────────────────────────────────────────
echo "[2/8] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
echo "[2/8] Done"

# ──────────────────────────────────────────────────────────────
# 3. Create Model Directory
# ──────────────────────────────────────────────────────────────
echo "[3/8] Creating model directory..."
mkdir -p /home/ubuntu/model
mkdir -p /home/ubuntu/ecom-chatbot/knowledge
chown -R ubuntu:ubuntu /home/ubuntu/model /home/ubuntu/ecom-chatbot
echo "[3/8] Done"

# ──────────────────────────────────────────────────────────────
# 4. Download GGUF Model from S3
# ──────────────────────────────────────────────────────────────
echo "[4/8] Downloading GGUF model from S3..."
aws s3 cp s3://${s3_bucket}/${model_path} /home/ubuntu/model/
echo "Model downloaded: $(ls -lh /home/ubuntu/model/*.gguf)"
echo "[4/8] Done"

# ──────────────────────────────────────────────────────────────
# 5. Create Modelfile & Register Model with Ollama
# ──────────────────────────────────────────────────────────────
echo "[5/8] Creating Modelfile and registering model..."
cat > /home/ubuntu/model/Modelfile << 'EOF'
FROM ./tinyllama-chat.Q4_K_M.gguf

SYSTEM """
You are an expert e-commerce business intelligence analyst.
You specialize in SWOT analyses, competitor comparisons, and market trend reports.
Provide structured, concise, and evidence-based responses using e-commerce domain terminology.
"""

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 2048
PARAMETER repeat_penalty 1.1
EOF

cd /home/ubuntu/model
ollama create ecom-chatbot -f Modelfile
echo "Model registered: $(ollama list | grep ecom-chatbot)"
echo "[5/8] Done"

# ──────────────────────────────────────────────────────────────
# 6. Install RAG Dependencies
# ──────────────────────────────────────────────────────────────
echo "[6/8] Installing RAG dependencies (faiss-cpu, sentence-transformers)..."
pip3 install -q faiss-cpu sentence-transformers requests
echo "[6/8] Done"

# ──────────────────────────────────────────────────────────────
# 7. Install & Start OpenWebUI
# ──────────────────────────────────────────────────────────────
echo "[7/8] Installing and starting OpenWebUI..."
pip3 install -q open-webui
nohup open-webui serve --port 3000 --ollama-base-url http://localhost:11434 \
    > /tmp/openwebui.log 2>&1 &
echo "OpenWebUI started (PID: $!)"
echo "[7/8] Done"

# ──────────────────────────────────────────────────────────────
# 8. Configure Firewall (UFW)
# ──────────────────────────────────────────────────────────────
echo "[8/8] Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ${local_ip}/32 to any port 22    # SSH from your IP only
ufw allow ${local_ip}/32 to any port 3000   # OpenWebUI from your IP only
ufw --force enable
echo "[8/8] Done"

echo "====== Provisioning Complete ======"
echo "EC2 Public IP: ${ec2_ip}"
echo "OpenWebUI URL: http://${ec2_ip}:3000"
echo "Completed at: $(date)"
