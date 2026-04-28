# Model Load Instructions for Person 3 (Group 25fltp)

## Overview

Person 2 has exported the fine-tuned model in **GGUF format** (quantized as `q4_k_m`). This file is ready to be loaded directly into Ollama on the EC2 instance.

## File Location

- **S3 Bucket**: `s3://25fltp-ecom-chatbot`
- **GGUF Path**: `s3://25fltp-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf`
- **Local path after download**: `./model/`
- **Main GGUF file**: `tinyllama-chat.Q4_K_M.gguf` (~668 MB, q4_k_m quantization)

---

## Step-by-Step Deployment Instructions

### Prerequisites

```bash
# SSH into your EC2 instance
ssh -i 25fltp-ecom-key.pem ubuntu@<ec2-public-ip>

# Verify Ollama is installed
ollama --version

# Start Ollama service
ollama serve &
```

---

### Step 1: Download Model from S3

```bash
# Create model directory
mkdir -p ~/model
cd ~/model

# Download the GGUF model from S3 (Person 2 uploaded this from Colab)
aws s3 cp s3://25fltp-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf ./

# Verify (~668 MB)
ls -lh ~/model/
```

---

### Step 2: Create the Modelfile

The Modelfile tells Ollama how to load and configure the model.

```bash
cd ~/model

cat > Modelfile << 'EOF'
FROM ./tinyllama-chat.Q4_K_M.gguf

# System prompt — defines the chatbot's persona
SYSTEM """
You are an expert e-commerce business intelligence analyst.
You specialize in SWOT analyses, competitor comparisons, and market trend reports.
Provide structured, concise, and evidence-based responses using e-commerce domain terminology.
"""

# Generation parameters optimized for structured output
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 2048
PARAMETER repeat_penalty 1.1
EOF

echo "Modelfile created successfully"
```

---

### Step 3: Register the Model with Ollama

```bash
# Register the model with Ollama
ollama create ecom-chatbot -f Modelfile

# Verify model is registered
ollama list
# Should show: ecom-chatbot   tinyllama-chat.Q4_K_M.gguf
```

---

### Step 4: Test the Model

```bash
# Quick test query
ollama run ecom-chatbot "Give me a SWOT analysis for Amazon in e-commerce."
```

---

### Step 5: Test the Ollama API (Required for Report Screenshot)

```bash
# Test via curl (required for report screenshot)
curl http://localhost:11434/api/generate -d '{
  "model": "ecom-chatbot",
  "prompt": "Give me a SWOT analysis for Amazon in e-commerce.",
  "stream": false
}'
```

---

## Troubleshooting

### Issue: "Model not found"
```bash
# Check what files are in the GGUF directory
ls -la ~/model/

# Verify GGUF file exists
ls -la ~/model/*.gguf

# The FROM path in Modelfile must match the actual filename
# Example: if file is "tinyllama-chat.Q4_K_M.gguf", use "FROM ./tinyllama-chat.Q4_K_M.gguf"
```

### Issue: "Ollama not running"
```bash
# Start Ollama as background service
nohup ollama serve > /tmp/ollama.log 2>&1 &

# Check if it's running
curl http://localhost:11434/api/tags
```

### Issue: Wrong FROM path in Modelfile
```bash
# Always use the RELATIVE path from the Modelfile location
# If Modelfile is in ~/model/ and GGUF is also there:
FROM ./tinyllama-chat.Q4_K_M.gguf   # ✅ Correct (relative path)
FROM /home/ubuntu/model/...          # ❌ Wrong (absolute path causes issues)
```

---

## Alternative: If GGUF Was Not Successfully Exported

If GGUF export failed during training, use the **LoRA adapter** instead:

```bash
# Download adapter from S3
aws s3 cp s3://25fltp-ecom-chatbot/model/ecom_chatbot_adapter/ ~/adapter/ --recursive

# Load base model + apply adapter using Python
python3 << 'PYEOF'
from unsloth import FastLanguageModel

# Load base model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    max_seq_length=2048,
    load_in_4bit=True,
)

# Apply LoRA adapter
model = FastLanguageModel.get_peft_model(model, r=16, lora_alpha=32)

# Merge and export to GGUF
model.save_pretrained_gguf("/home/ubuntu/model/ecom_chatbot_gguf", tokenizer)
print("Adapter merged and exported to GGUF!")
PYEOF
```

Then continue with Steps 2-5 above.

---

## Model Information Summary (Group 25fltp)

| Property | Value |
|---|---|
| Base Model | TinyLlama/TinyLlama-1.1B-Chat-v1.0 |
| Fine-Tuning Method | QLoRA (4-bit NF4 + LoRA r=16, alpha=32) |
| Quantization | q4_k_m (4-bit K-Quant Medium) |
| File Size | ~668 MB |
| Context Length | 2048 tokens |
| Fine-Tuning Data | 9 categories × ~7,000 examples = ~65,000 instruction pairs |
| Training Epochs | 2 |
| Domain | E-commerce SWOT, competitor analysis, market trends, product category, customer sentiment |
| HuggingFace ID | TinyLlama/TinyLlama-1.1B-Chat-v1.0 |
| License | Apache 2.0 |

---

## Expected Model Behavior

The fine-tuned model should produce structured responses in these formats:

**SWOT Analysis**: Strengths / Weaknesses / Opportunities / Threats / Strategic Takeaway

**Competitor Comparison**: Fixed-dimension table (Pricing / Logistics / AI / Assortment / Customer Experience)

**Market Trends**: Numbered list with trend name + explanation + business implication

**Review Intelligence**: Bullet list with issue categorization + frequency + recommendation

**Business Recommendation**: Structured priority tiers with evidence backing

---

## GGUF Export Path (Unsloth 2026.4.8)

**IMPORTANT**: Unsloth 2026.4.8 creates a **quadruple-nested** directory structure:

```
./outputs/ecom_chatbot_gguf_gguf_gguf_gguf/tinyllama-chat.Q4_K_M.gguf
```

If you don't find the GGUF file, search recursively:
```bash
find ./outputs -name "*.gguf" -type f
```