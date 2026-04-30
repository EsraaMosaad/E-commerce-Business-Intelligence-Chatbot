#!/bin/bash
# terraform/user_data.sh
# Universal script for Ubuntu and Amazon Linux 2023

set -e
echo "====== E-commerce BI Chatbot Provisioning ======"
echo "Started at: $(date)"

# 1. Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS="unknown"
fi

echo "Detected OS: $OS"

# 2. Install Dependencies based on OS
if [ "$OS" = "ubuntu" ]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq curl wget git jq python3 python3-pip python3-venv awscli &>/dev/null
elif [ "$OS" = "amzn" ]; then
    dnf update -y
    dnf install -y curl wget git jq python3 python3-pip aws-cli &>/dev/null
fi

# 3. Install Ollama
echo "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# 4. Setup Directories
mkdir -p /home/ec2-user/model || mkdir -p /home/ubuntu/model
USER_HOME=$(eval echo ~$${USER:-$(id -un)})
mkdir -p $USER_HOME/model

# 5. Download GGUF Model from S3
echo "Downloading model from S3..."
aws s3 cp s3://${s3_bucket}/${model_path} $USER_HOME/model/

# 6. Register Model with Ollama
echo "Registering model..."
cat > $USER_HOME/model/Modelfile << 'EOF'
FROM ./tinyllama-chat.Q4_K_M.gguf
SYSTEM """You are the Amazon Internal Executive BI Assistant. 
Your role is to provide the CEO and Company Owners with strategic insights based on OUR internal customer data.
Always refer to categories and products as 'OURS'. 
Focus on market share, competitor threats, and product health. 
Be decisive, executive-level, and data-driven."""
PARAMETER temperature 0.1
PARAMETER top_p 0.9
EOF

cd $USER_HOME/model
ollama create ecom-chatbot -f Modelfile

# 7. Install OpenWebUI
echo "Installing OpenWebUI..."
pip3 install open-webui

# 8. Start Service (Simple background run for now)
nohup open-webui serve --port 3000 > /var/log/openwebui.log 2>&1 &

echo "====== Provisioning Complete ======"
