# EC2 Deployment Commands — Person 3

All commands to be run on the EC2 instance after SSH.

---

## Prerequisites: IAM Role for EC2

Attach an IAM role to your EC2 instance with S3 read/write access so it can download the model:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::25fltp-ecom-chatbot",
                   "arn:aws:s3:::25fltp-ecom-chatbot/*"]
    }
  ]
}
```

Attach via AWS Console: EC2 → Instances → Actions → Security → Modify IAM Role.

---

## 1. Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version

# Start Ollama as background service
nohup ollama serve > /tmp/ollama.log 2>&1 &
echo "Ollama started (PID: $!)"
```

---

## 2. Download Fine-Tuned Model from S3

```bash
# Create model directory
mkdir -p ~/model
cd ~/model

# Download the GGUF model from S3 (uploaded by Person 2)
aws s3 cp s3://25fltp-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf ./

# Verify download (~668 MB)
ls -lh tinyllama-chat.Q4_K_M.gguf
```

---

## 3. Create Modelfile

```bash
cat > ~/model/Modelfile << 'EOF'
FROM ./tinyllama-chat.Q4_K_M.gguf

SYSTEM """
You are an expert e-commerce business intelligence analyst.
You specialize in SWOT analyses, competitor comparisons, and market trend reports.
Provide structured, concise, and evidence-based responses.
"""

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 2048
PARAMETER repeat_penalty 1.1
EOF

echo "Modelfile created"
```

---

## 4. Register and Test Model

```bash
# Register model with Ollama
cd ~/model
ollama create ecom-chatbot -f Modelfile

# Verify model is registered
ollama list

# Test with a query
ollama run ecom-chatbot "Give me a SWOT analysis for Amazon in e-commerce." --verbose
```

---

## 5. Test Ollama API (Required for Report Screenshot)

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "ecom-chatbot",
  "prompt": "Compare Amazon, Walmart, and Alibaba on pricing, logistics, and AI.",
  "stream": false,
  "options": {
    "temperature": 0.3,
    "top_p": 0.9
  }
}'
```

Save the output as `api_curl_test.png` or copy to `api_curl_test.txt` for the report.

---

## 6. Install OpenWebUI

```bash
# Install OpenWebUI
pip install open-webui

# Create systemd service for auto-start on reboot
sudo tee /etc/systemd/system/openwebui.service > /dev/null << 'EOF'
[Unit]
Description=OpenWebUI Service
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
ExecStart=/usr/local/bin/open-webui serve --port 3000 --ollama-base-url http://localhost:11434
Restart=always
User=ubuntu
Environment="OLLAMA_BASE_URL=http://localhost:11434"

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd, enable and start
sudo systemctl daemon-reload
sudo systemctl enable openwebui
sudo systemctl start openwebui

# Check status
sudo systemctl status openwebui
```

---

## 7. Verify Everything is Running

```bash
# Check all services
echo "=== Ollama ===" && curl -s http://localhost:11434/api/tags | python3 -m json.tool
echo "=== OpenWebUI ===" && sudo systemctl status openwebui | head -5
echo "=== Ollama Process ===" && ps aux | grep ollama | grep -v grep
```

---

## 8. Terminate EC2 (When Done)

```bash
# Get instance ID
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region us-east-1
```

---

## Port Reference

| Port | Service | Access |
|---|---|---|
| 22 | SSH | Your IP only |
| 11434 | Ollama API | localhost only (internal) |
| 3000 | OpenWebUI | Your IP only |
