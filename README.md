# E-commerce Business Intelligence Chatbot — Group 25fltp

**Course:** CISC 886 – Cloud Computing | Queen's University

**Team members:** Data Engineering, Model Fine-Tuning, Deployment

**Group ID:** 25fltp

**Live Demo:** `http://<EC2-Elastic-IP>:3000`

---

## Project Overview

This project implements an end-to-end cloud-based conversational chatbot specialized for **e-commerce business intelligence**. The chatbot processes the Amazon Reviews 2023 dataset across 9 categories, fine-tunes a lightweight LLM (TinyLlama-1.1B) using QLoRA, and deploys it on AWS EC2 with a RAG-augmented web interface.

### What the Chatbot Does

The chatbot answers three core categories of business queries (and more):

| Query Type | Description | Example |
|------------|-------------|---------|
| **SWOT Analysis** | Structured strengths, weaknesses, opportunities, threats | "SWOT analysis for Amazon in e-commerce" |
| **Competitor Comparison** | Multi-dimensional comparison across dimensions | "Compare Amazon vs Walmart vs Alibaba" |
| **Market Trends** | Current and emerging e-commerce trends | "What are the latest e-commerce trends?" |
| **Product Category** | Category-specific insights | "Analyze the Electronics category" |
| **Customer Sentiment** | Sentiment analysis of reviews | "What do customers say about Pet Supplies?" |
| **Pricing & Delivery** | Price and shipping analysis | "Compare pricing strategies" |
| **Review Intelligence** | Deep review analysis | "Summarize reviews for Home products" |

### Categories Covered (9/9)

Electronics, Clothing_Shoes_and_Jewelry, Home_and_Kitchen, Books, Sports_and_Outdoors, Beauty_and_Personal_Care, Toys_and_Games, Grocery_and_Gourmet_Food, Pet_Supplies

---

## System Architecture

![Architecture Diagram](img\architecture_diagram.gif)

---

## Repository Structure

```
25fltp-ecom-chatbot/
├── README.md                         # This file
├── .gitignore
├── training/
│   ├── finetune.ipynb               # Original (Electronics only, 7,256 examples)
│   └── finetune_all_categories.ipynb # NEW (All 9 categories, ~65,000 examples)
├── terraform/
│   ├── main.tf                      # Complete infrastructure (VPC + EMR + EC2 + S3)
│   ├── variables.tf                 # All variables (including EMR instance types)
│   ├── terraform.tfvars.example      # Template for deployment
│   └── user_data.sh                 # Cloud-init script for EC2 auto-provisioning
├── spark/
│   ├── spark_preprocess.py          # PySpark ETL pipeline (Person 1)
│   ├── run_commands.sh              # Manual EMR commands (Person 1)
│   └── scripts/
│       └── emr_bootstrap.sh        # Bootstrap for EMR nodes
├── deployment/
│   ├── deploy_commands.md           # SSH + Modelfile commands (Person 3)
│   ├── backend_rag.py               # RAG layer with FAISS (Person 2)
│   └── model_load_instructions.md   # GGUF loading guide (Person 2)
└── docs/
    ├── submission_checklist.md      # Professor submission checklist
    └── architecture_diagram.svg     # Visual architecture diagram
```

---

## Prerequisites

- **AWS Account** with programmatic access (IAM credentials)
- **AWS Region:** us-east-1
- **Python:** 3.10+
- **Google Colab** with T4 GPU runtime (free tier)
- **GitHub Account** for repository
- **AWS CLI** configured locally (`aws configure`)
- **Key Pair:** `25fltp-ecom-key` created in AWS EC2

---

## Step-by-Step Workflow

### Data Preprocessing (PySpark on EMR)

**Purpose:** Process raw Amazon reviews data into structured train/val/test sets.

**Files:**
- `spark/spark_preprocess.py` — Main PySpark pipeline
- `spark/run_commands.sh` — Manual EMR commands
- `spark/scripts/emr_bootstrap.sh` — Node bootstrap script

**Execution:**
```bash
# Launch EMR cluster (via Terraform or manual)
aws emr create-cluster \
  --name "25fltp-ecom-spark-cluster" \
  --release-label emr-7.1.0 \
  --instance-type m6i.2xlarge \
  --instance-count 3 \
  --ec2-attributes KeyName=25fltp-ecom-key,SubnetId=<subnet-id> \
  --applications Name=Spark

# Submit Spark job
aws emr add-steps --cluster-id j-<CLUSTER_ID> \
  --steps Type=Spark,Name=EcomPreprocess,Args=[--deploy-mode,cluster,s3://25fltp-ecom-chatbot/code/spark_preprocess.py]
```

**Output:** `s3://25fltp-ecom-chatbot/processed/` (train.jsonl, val.jsonl, test.jsonl)

**EDA Statistics (Across 9 Categories):**
- **Train:** 360,277 samples (Avg Length: 285.9 chars)
- **Val:** 44,874 samples (Avg Length: 284.6 chars)
- **Test:** 44,849 samples (Avg Length: 286.9 chars)
- **Total Dataset:** 450,000 processed reviews.
- **Top Detected Topic:** Quality
---

### Model Fine-Tuning (QLoRA → GGUF)

**Purpose:** Fine-tune TinyLlama-1.1B on e-commerce BI instruction data, export to GGUF.

**Files:**
- `training/finetune_all_categories.ipynb` — Unified notebook for all 9 categories
- `deployment/model_load_instructions.md` — GGUF loading guide
- `deployment/backend_rag.py` — RAG layer

**Execution (Google Colab):**
1. Open `training/finetune_all_categories.ipynb`
2. Runtime → Change runtime → **T4 GPU**
3. Run BLOCK 1-15 sequentially

**Steps Overview:**
| Step | Purpose |
|-------|---------|
| 1 | Install Dependencies (Unsloth, transformers, trl, peft, awscli) |
| 2 | S3 Login & Download Data (Total 360,277 training samples downloaded) |
| 3 | Load Model & Base Test (unsloth/tinyllama-chat-bnb-4bit) |
| 4 | Apply LoRA Adapters (r=16, alpha=16, dropout=0) |
| 5 | Dataset & Formatting (Subset to 70,000 samples: 63k train / 7k eval) |
| 6 | Hyperparameter Table (LR=2e-4, batch=2, grad_accum=4, steps=500) |
| 7 | Train Model (Early stopped at ~291 steps due to convergence) |
| 8 | Training Summary (Calculated 83.72% loss improvement and plotted curves) |
| 9 | Final Inference Test (SWOT, Risk Assessment, Market Forecast) |

**GGUF Output Path:**
```
./outputs/ecom_chatbot_gguf_gguf_gguf_gguf/tinyllama-chat.Q4_K_M.gguf
```
*(Unsloth 2026.4.8 uses quadruple-nested directories)*

**Upload to S3:**
```bash
aws s3 cp ./outputs/ecom_chatbot_gguf_gguf_gguf_gguf/tinyllama-chat.Q4_K_M.gguf \
  s3://25fltp-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf
```

---

### Deployment (EC2 + Ollama + OpenWebUI)

**Purpose:** Deploy GGUF model on EC2 with RAG-augmented web interface.

**Files:**
- `terraform/main.tf` — Complete infrastructure (VPC + EMR + EC2 + S3)
- `terraform/user_data.sh` — Cloud-init auto-provisioning
- `deployment/deploy_commands.md` — SSH commands and Modelfile

**Deployment via Terraform:**
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: set allowed_ip to your IP (e.g., "203.0.113.42/32")
terraform init
terraform apply
```

**Manual SSH:**
```bash
ssh -i 25fltp-ecom-key.pem ubuntu@<ec2_public_ip>

# Verify Ollama
ollama list
# Should show: ecom-chatbot

# Test model
ollama run ecom-chatbot "Give me a SWOT analysis for Amazon"

# Access OpenWebUI
# http://<ec2_public_ip>:3000
```

---

## Terraform Infrastructure (Group 25fltp)

### Resources Created
| Resource | Name | Purpose |
|----------|------|---------|
| VPC | 25fltp-ecom-vpc | Network isolation (10.0.0.0/16) |
| Subnet | 25fltp-ecom-public-subnet | EC2 + EMR deployment |
| EMR Cluster | 25fltp-ecom-spark-cluster | PySpark preprocessing |
| EC2 Instance | 25fltp-ecom-chatbot-ec2 | Ollama + OpenWebUI |
| S3 Bucket | 25fltp-ecom-chatbot | Model + data storage |
| S3 Bucket (State) | 25fltp-terraform-state | Terraform backend |
| Security Group | 25fltp-ec2-sg | SSH (22) + HTTP (3000) |
| Security Group | 25fltp-emr-sg | EMR internal communication |
| IAM Role | 25fltp-ec2-s3-role | EC2 → S3 access |
| IAM Role | 25fltp-emr-role | EMR → S3 + EC2 access |

### Terraform Outputs
```bash
terraform output  # Shows:
# ec2_public_ip    = "54.123.456.789"
# openwebui_url   = "http://54.123.456.789:3000"
# emr_cluster_id  = "j-XXXXXXXX"
# s3_model_path   = "s3://25fltp-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf"
```

---

---

## Model Card

| Property | Value |
|----------|-------|
| Model | unsloth/tinyllama-chat-bnb-4bit |
| Parameters | 1.1 billion |
| Fine-Tuning Method | QLoRA (4-bit + LoRA r=16, alpha=16, dropout=0) |
| Training Data | 70,000 samples (63k train, 7k val) across 9 categories |
| Epochs | 1 |
| Max Steps | 500 (Early stopped at ~291) |
| Batch Size | 2 (effective 8 with gradient accumulation=4) |
| Learning Rate | 2e-4 |
| Context Length | 2048 tokens |
| GGUF Quantization | Q4_K_M (~668 MB) |
| Final Loss | 0.4038 (Train), 0.3906 (Validation) |

---

## AWS Cost Estimate

| Service | Usage | Est. Cost |
|---------|-------|-----------|
| Amazon S3 | ~10 GB storage | ~$1.50/month |
| Amazon EMR | 1 cluster × ~2 hours (m6i.2xlarge × 3) | ~$10.00 |
| Amazon EC2 | t3.xlarge × ~48 hours | ~$15.00 |
| Data Transfer | ~5 GB outbound | ~$0.50 |
| **Total** | | **~$23.00** |

> Always terminate EMR immediately after processing to save costs.

---

## Troubleshooting

### GGUF Path Not Found
```bash
# Unsloth 2026.4.8 creates quadruple-nested path
find ./outputs -name "*.gguf" -type f
# Expected: ./outputs/ecom_chatbot_gguf_gguf_gguf_gguf/tinyllama-chat.Q4_K_M.gguf
```

### Ollama Not Running
```bash
systemctl status ollama
sudo systemctl restart ollama
ollama list
```

### OpenWebUI Cannot Connect
```bash
export OLLAMA_BASE_URL="http://localhost:11434"
open-webui serve --port 3000
```

### S3 Permissions Denied
```bash
# Verify IAM role attached
aws ec2 describe-iam-instance-profile-associations --instance-id <id>
```

---

---


## References

- TinyLlama: Zhang et al., arXiv:2401.02385 (2024)
- LoRA: Hu et al., ICLR 2022
- QLoRA: Dettmers et al., NeurIPS 2023
- Amazon Reviews 2023: Hou et al., arXiv:2403.03952 (2024)
- Unsloth: https://unsloth.ai
- Ollama: https://ollama.com
- OpenWebUI: https://openwebui.com