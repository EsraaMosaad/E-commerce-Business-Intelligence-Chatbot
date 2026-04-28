# Complete Developer & Deployment Guide
## E-commerce Business Intelligence Chatbot — CISC 886

---

## Table of Contents

1. [How to Verify the GGUF Model Works](#1-how-to-verify-the-gguf-model-works)
2. [Complete Team Workflow (Person 1 → Person 2 → Person 3)](#2-complete-team-workflow-person-1--person-2--person-3)
3. [Architecture Design Diagram](#3-architecture-design-diagram)
4. [Why Use .md Files Instead of Hard-Coding?](#4-why-use-md-files-instead-of-hard-coding)
5. [Terraform: What It Is and Why You Need It](#5-terraform-what-it-is-and-why-you-need-it)
6. [GitHub Actions CI/CD: Automation Explained](#6-github-actions-cicd-automation-explained)
7. [File-by-File Usage Guide](#7-file-by-file-usage-guide)
8. [How to Upload Everything to GitHub](#8-how-to-upload-everything-to-github)

---

## 1. How to Verify the GGUF Model Works

### Quick Local Test (Before Uploading to S3)

You don't need AWS to test the model. After downloading `tinyllama-chat.Q4_K_M.gguf` from Colab, you can verify it works locally on your computer:

#### Option A: Using Ollama CLI (Recommended)

```bash
# 1. Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# 2. Create a test directory
mkdir -p ~/test-chatbot
cd ~/test-chatbot

# 3. Move the GGUF file
mv ~/Downloads/tinyllama-chat.Q4_K_M.gguf ~/test-chatbot/

# 4. Create Modelfile
cat > Modelfile << 'EOF'
FROM ./tinyllama-chat.Q4_K_M.gguf

SYSTEM """
You are an expert e-commerce business intelligence analyst.
You specialize in SWOT analyses, competitor comparisons, and market trend reports.
Provide structured, concise, and evidence-based responses.
"""

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 2048
PARAMETER repeat_penalty 1.1
EOF

# 5. Register the model
ollama create ecom-chatbot -f Modelfile

# 6. Test with a SWOT query
ollama run ecom-chatbot "Give me a SWOT analysis for Amazon in e-commerce."

# 7. Test with competitor comparison
ollama run ecom-chatbot "Compare Amazon, Walmart, and Alibaba on pricing, logistics, and AI."

# 8. Test with market trends
ollama run ecom-chatbot "What are the top 3 e-commerce market trends and their business implications?"
```

#### Option B: Using llama.cpp (Direct CLI)

```bash
# Download llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
mkdir build && cd build
cmake .. && cmake --build . --config Release

# Run the model directly
./build/bin/llama-cli \
  -m ~/test-chatbot/tinyllama-chat.Q4_K_M.gguf \
  -p "You are an expert e-commerce BI analyst. Give me a SWOT analysis for Amazon." \
  -n 300 \
  --temp 0.3 \
  --top-p 0.9
```

#### Expected Output (SWOT Analysis):

```
## Strengths
- Strong product quality and customer satisfaction
- Established delivery infrastructure
- Competitive pricing and value for money

## Weaknesses
- Price sensitivity and competitive pricing pressure
- Regional service quality variation
- Variable customer service response times

## Opportunities
- Growing e-commerce market penetration
- AI-powered personalization and recommendations
- Expansion into emerging markets

## Threats
- Intense competition from Walmart and Alibaba
- Supply chain and logistics disruptions
- Regulatory and data privacy challenges
```

#### Verification Checklist

| Test | Expected | Status |
|---|---|---|
| `ollama create ecom-chatbot` | Success, no errors | ✅ |
| SWOT query produces structured output | Markdown headings present | ✅ |
| Comparison query produces table | Markdown table format | ✅ |
| Model responds within 60 seconds | Reasonable response time | ✅ |
| No repetition in output | Clean, structured text | ✅ |

---

## 2. Complete Team Workflow (Person 1 → Person 2 → Person 3)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PERSON 1: Data Engineering                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT:  HuggingFace Amazon Reviews 2023                                   │
│          https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023  │
│                                                                             │
│  PROCESS:                                                                  │
│  1. Write spark/spark_preprocess.py (PySpark pipeline)                     │
│  2. Create AWS EMR cluster                                                 │
│  3. Submit Spark job → generates train.jsonl, val.jsonl, test.jsonl         │
│  4. Upload processed JSONL to S3: s3://<NETID>-ecom-chatbot/data/          │
│                                                                             │
│  OUTPUT:                                                                    │
│  ┌─ s3://<NETID>-ecom-chatbot/                                             │
│  │   ├── data/                                                            │
│  │   │   ├── train.jsonl   (80% of data)                                  │
│  │   │   ├── val.jsonl     (10% of data)                                  │
│  │   │   └── test.jsonl    (10% of data)                                  │
│  │   └── logs/                                                             │
│                                                                             │
│  DELIVER TO: Person 2 + Person 3                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │  s3://<NETID>-ecom-chatbot/data/
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PERSON 2: Model Fine-Tuning                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT:  McAuley-Lab/Amazon-Reviews-2023 (HuggingFace direct download)     │
│          OR: s3://<NETID>-ecom-chatbot/data/train.jsonl                     │
│                                                                             │
│  PROCESS:                                                                  │
│  1. Open training/finetune.ipynb in Google Colab                           │
│  2. Set Runtime → T4 GPU                                                    │
│  3. Run all blocks (BLOCK 1 → BLOCK 16)                                     │
│  4. BLOCK 2: Load 10,000 real reviews from HuggingFace                      │
│  5. BLOCK 4: Generate instruction-tuning examples (5 task types)          │
│  6. BLOCK 6-7: Load TinyLlama-1.1B + attach QLoRA adapters                 │
│  7. BLOCK 11: Fine-tune for 2 epochs (~33 minutes)                          │
│  8. BLOCK 12: Save LoRA adapters (~50 MB)                                  │
│  9. BLOCK 13: Export to GGUF q4_k_m (~668 MB)                              │
│  10. BLOCK 14: Download GGUF file to local machine                          │
│                                                                             │
│  OUTPUT:                                                                    │
│  ┌─ Local Computer (after BLOCK 14 download)                               │
│  │   └── tinyllama-chat.Q4_K_M.gguf  (668 MB)                              │
│  │                                                                        │
│  ┌─ Google Colab outputs/                                                 │
│  │   ├── ecom_chatbot_adapter/    (LoRA weights)                           │
│  │   └── ecom_chatbot_gguf_gguf_gguf/  (GGUF + Modelfile)                 │
│                                                                             │
│  DELIVER TO: Person 3 (via S3)                                             │
│                                                                             │
│  UPLOAD TO S3:                                                              │
│  ┌─ s3://<NETID>-ecom-chatbot/                                             │
│  │   └── model/                                                           │
│  │       └── tinyllama-chat.Q4_K_M.gguf                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │  s3://<NETID>-ecom-chatbot/model/
                                    │  + deployment/backend_rag.py
                                    │  + deployment/knowledge/*.md
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PERSON 3: Deployment                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT:                                                                     │
│  ┌─ tinyllama-chat.Q4_K_M.gguf  (668 MB) — from S3 or local upload         │
│  ├─ deployment/backend_rag.py                                              │
│  ├─ deployment/knowledge/*.md  (4 files)                                    │
│  └─ deployment/model_load_instructions.md                                   │
│                                                                             │
│  DEPLOYMENT OPTIONS:                                                        │
│                                                                             │
│  OPTION A: Manual Deployment (Step-by-Step)                                  │
│  ──────────────────────────────────────                                    │
│  1. SSH into EC2 instance                                                   │
│  2. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh          │
│  3. Download GGUF from S3: aws s3 cp ...                                   │
│  4. Create Modelfile                                                       │
│  5. Register model: ollama create ecom-chatbot -f Modelfile                │
│  6. Install RAG deps: pip install faiss-cpu sentence-transformers          │
│  7. Install OpenWebUI: pip install open-webui                               │
│  8. Access at http://<EC2-IP>:3000                                         │
│                                                                             │
│  OPTION B: Terraform + GitHub Actions (IaC) ✅ RECOMMENDED                  │
│  ───────────────────────────────────────────                               │
│  1. Terraform provisions EC2, VPC, S3, IAM in AWS                          │
│  2. user_data.sh auto-installs Ollama, RAG, OpenWebUI                      │
│  3. GitHub Actions: terraform validate → plan → apply                       │
│  4. Model auto-downloads from S3 via IAM role                              │
│                                                                             │
│  OUTPUT:                                                                    │
│  ┌─ EC2 Instance                                                           │
│  │   ├── Ollama running on port 11434                                       │
│  │   ├── OpenWebUI on port 3000                                             │
│  │   ├── RAG knowledge base loaded                                          │
│  │   └── Model: ecom-chatbot (registered)                                  │
│  │                                                                        │
│  FINAL URL: http://<EC2-Elastic-IP>:3000                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Architecture Design Diagram

![Architecture Diagram](architecture_diagram.svg)

**System Flow:**
1. **HuggingFace** → Person 1 loads raw Amazon Reviews 2023
2. **AWS EMR (PySpark)** → Person 1 preprocesses, deduplicates, splits data
3. **S3** → Processed JSONL stored, accessible to Person 2
4. **Google Colab (QLoRA)** → Person 2 fine-tunes TinyLlama-1.1B on real reviews
5. **GGUF Export** → Person 2 produces 668 MB quantized model
6. **S3 (model/)** → Person 2 uploads GGUF for Person 3
7. **AWS EC2 (Ollama)** → Person 3 runs model + RAG + OpenWebUI
8. **End User** →访问 http://EC2-IP:3000 for chatbot interface

---

## 4. Why Use .md Files Instead of Hard-Coding?

### The Problem with Hard-Coding

If you hard-code everything in Python/PyTorch, you get:
- **No visibility**: Nobody can read your code without running it
- **No documentation**: Future-you won't remember what the variables mean
- **No collaboration**: Team members can't understand your work without deep diving
- **No maintainability**: Changing one parameter means editing source code
- **No auditability**: For a university project, graders need to see HOW and WHY

### The Benefits of .md Documentation Files

| Benefit | Explanation | Example |
|---|---|---|
| **Human Readable** | Anyone can read a `.md` file instantly — no setup needed | `hyperparameters.md` shows lr=2e-4 with reasoning |
| **Separation of Concerns** | Code does computation, docs explain decisions | `backend_rag.py` runs RAG, `model_load_instructions.md` explains how |
| **Version Control Friendly** | Git tracks changes line-by-line, shows history | `deploy_commands.md` history shows who changed what |
| **Portable** | Works anywhere — no Python, no dependencies, just text | `submission_guide.md` works on Overleaf, GitHub, Colab |
| **Grader Friendly** | Professors can read rationale without running Colab | `Person2_Report_Sections.md` → copy-paste into LaTeX |
| **Collaboration** | Person 1, 2, 3 can all read and update shared docs | All 3 persons read `submission_guide.md` |
| **No Lock-In** | Markdown is the universal standard for technical docs | Works on Overleaf, GitHub, Obsidian, Notion, Colab |

### Real Example: hyperparameters.md vs. Hard-Coding

**Hard-coded (BAD for a project):**
```python
training_args = TrainingArguments(
    learning_rate=2e-4,  # what does 2e-4 mean?
    num_train_epochs=2,
    per_device_train_batch_size=4,
)
# No explanation of WHY these values
# No documentation for the report
```

**Documented approach (GOOD):**
```python
# hyperparameters.md (documentation):
# | Parameter | Value | Rationale |
# | Learning Rate | 2e-4 | Standard for LoRA; 1e-4 too slow, 5e-4 too unstable |
# | Epochs | 2 | Enough for convergence with 7K examples; 3+ risks overfitting |
# | Batch Size | 4 | T4 GPU VRAM limit; gradient accumulation gives effective batch 16 |
```

```python
# finetune.ipynb (code):
# Loading hyperparameters from documented config
LEARNING_RATE = 2e-4  # See: hyperparameters.md
EPOCHS = 2
BATCH_SIZE = 4
```

### When to Use .md vs. Code Comments

| Use .md files for | Use code comments for |
|---|---|
| Architecture decisions | Line-level implementation notes |
| Team coordination | Variable explanations within functions |
| Submission/reports | Bug workarounds |
| Configuration docs | TODO items |
| User/developer guides | Algorithmic explanations |

### The .md Files in This Project

| File | Purpose | Who Reads It |
|---|---|---|
| `README.md` | Full project overview + replication steps | Everyone |
| `docs/submission_guide.md` | Step-by-step submission instructions | Person 2 |
| `docs/Person2_Report_Sections.md` | Sections 3 & 5 of final report | Person 2 → Professor |
| `docs/file_guide.md` | File-by-file explanation | All 3 persons |
| `deployment/model_load_instructions.md` | How Person 3 loads the model | Person 3 |
| `deployment/deploy_commands.md` | All EC2 commands | Person 3 |
| `training/hyperparameters.md` | Hyperparameter rationale for report | Include in report |
| `training/eval_prompts.md` | Evaluation prompts + expected outputs | Include in report |

---

## 5. Terraform: What It Is and Why You Need It

### What is Terraform?

**Terraform** is an **Infrastructure as Code (IaC)** tool that lets you define your AWS infrastructure (VPC, EC2, S3, IAM, etc.) in code files, then create/destroy/update it automatically.

### Without Terraform (Manual Deployment — BAD)

```
1. Go to AWS Console
2. Click "Create VPC" → fill form → submit
3. Click "Create Subnet" → fill form → submit
4. Click "Create Internet Gateway" → ...
5. Click "Create Security Group" → ...
6. Click "Launch EC2" → fill form → submit
7. SSH in → manually run install commands
8. Repeat for every team member's environment
```

**Problems:**
- Manual = error-prone (wrong CIDR, missing rule)
- Not reproducible (different for each person)
- No version control (if you delete VPC, it's gone)
- No audit trail (who changed what?)
- No collaboration (if Person 1 creates it, Person 3 can't see how)

### With Terraform (IaC — GOOD)

```bash
# One command creates EVERYTHING:
cd terraform
terraform init
terraform apply -var-file=terraform.tfvars

# One command destroys EVERYTHING:
terraform destroy -var-file=terraform.tfvars
```

**Result:**
- ✅ Reproducible — same infrastructure every time
- ✅ Version controlled — Git tracks all changes
- ✅ Collaborative — Person 1, 2, 3 all use same code
- ✅ Audit trail — Git history shows who changed what
- ✅ Audit-ready for CISC 886 — graders can see exactly what was created

### Terraform Files in This Project

| File | What It Does |
|---|---|
| `terraform/provider.tf` | AWS provider + Terraform backend (S3 state storage) |
| `terraform/variables.tf` | All input variables with defaults |
| `terraform/terraform.tfvars.example` | Template — copy and fill in your values |
| `terraform/main.tf` | **The infrastructure code** — VPC, Subnet, IGW, SG, IAM, EC2, S3, EIP |
| `terraform/outputs.tf` | Shows EC2 IP, OpenWebUI URL, S3 path after apply |
| `terraform/user_data.sh` | Cloud-init script — runs on first boot to install everything |
| `.github/workflows/terraform.yml` | GitHub Actions — runs terraform validate/plan/apply automatically |

### How to Use Terraform (Step-by-Step)

#### Step 1: Install Terraform

```bash
# macOS
brew install terraform

# Linux (Ubuntu/Debian)
wget https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip
unzip terraform_1.7.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Verify
terraform --version  # Should show 1.7.0
```

#### Step 2: Configure AWS Credentials

```bash
aws configure
# Enter Access Key ID, Secret Access Key, default region (us-east-1)
```

#### Step 3: Create S3 Bucket for Terraform State

```bash
aws s3 mb s3://<NETID>-terraform-state --region us-east-1
```

#### Step 4: Fill in terraform.tfvars

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your actual values:
# - aws_region = "us-east-1"
# - allowed_ip = "203.0.113.42/32"  (your IP from whatismyip.com)
# - key_name = "your-key-name"
# - s3_bucket_name = "<NETID>-ecom-chatbot"
```

#### Step 5: Initialize Terraform

```bash
cd terraform
terraform init
# Downloads AWS provider, connects to S3 backend
```

#### Step 6: Plan (See What Will Be Created)

```bash
terraform plan -var-file=terraform.tfvars
# Shows everything Terraform WILL create without actually creating it
# Review this output before proceeding
```

#### Step 7: Apply (Create Infrastructure)

```bash
terraform apply -var-file=terraform.tfvars
# Type "yes" when prompted
# Wait ~3-5 minutes for EC2 to provision
# user_data.sh runs automatically inside EC2 (installs Ollama, etc.)
```

#### Step 8: Get the EC2 IP

```bash
terraform output ec2_public_ip
# Shows: "54.123.45.67"

terraform output openwebui_url
# Shows: "http://54.123.45.67:3000"
```

#### Step 9: Destroy (When Done)

```bash
terraform destroy -var-file=terraform.tfvars
# Type "yes" — destroys ALL AWS resources
# Saves you from paying for running instances
```

### Terraform Benefits Summary

| Benefit | Without Terraform | With Terraform |
|---|---|---|
| Reproducibility | ❌ Different every time | ✅ Same infra every run |
| Collaboration | ❌ Manual, untracked | ✅ Git-tracked, shared |
| Speed | ❌ 30-60 min manual | ✅ 5 min `terraform apply` |
| Cost Control | ❌ Easy to forget running instances | ✅ `terraform destroy` = clean slate |
| Auditability | ❌ No record of changes | ✅ Git history shows all changes |
| For Graders | ❌ What did you actually create? | ✅ `terraform plan` shows exact infra |

---

## 6. GitHub Actions CI/CD: Automation Explained

### What is CI/CD?

**CI (Continuous Integration)**: Every time you push code to GitHub, automated tests check that nothing is broken.

**CD (Continuous Deployment)**: After tests pass, the code automatically deploys to AWS.

### Without GitHub Actions (Manual Process)

```
1. Write code
2. Push to GitHub
3. SSH into EC2
4. Manually pull code
5. Manually run terraform apply
6. Manually check if it worked
7. Repeat for every change
```

### With GitHub Actions (Automated)

```
1. Write code
2. Push to GitHub
   ↓
3. GitHub Actions runs automatically:
   ├── terraform validate (check syntax)
   ├── terraform plan (show what will change)
   └── terraform apply (deploy to AWS)
   ↓
4. You get a notification: "Deployment successful"
```

### How It Works in This Project

#### `.github/workflows/terraform.yml`

```
Push to main branch OR Pull Request
          ↓
    ┌────────────────────────────────────────┐
    │ Job 1: terraform-validate              │
    │ ├─ Checkout code                       │
    │ ├─ terraform init                      │
    │ ├─ terraform fmt -check               │
    │ └─ terraform validate                  │
    └────────────────────────────────────────┘
          ↓ (if PR)
    ┌────────────────────────────────────────┐
    │ Job 2: terraform-plan                  │
    │ ├─ terraform init                      │
    │ ├─ terraform plan                      │
    │ └─ Comment plan on GitHub PR           │
    └────────────────────────────────────────┘
          ↓ (if push to main)
    ┌────────────────────────────────────────┐
    │ Job 3: terraform-apply                 │
    │ ├─ terraform init                      │
    │ ├─ terraform apply -auto-approve       │
    │ └─ Show EC2 IP in GitHub Actions log   │
    └────────────────────────────────────────┘
```

#### `.github/workflows/upload_model.yml`

```
User clicks "Run workflow" on GitHub
          ↓
    ┌────────────────────────────────────────┐
    │ Job: upload-model                      │
    │ ├─ Configure AWS credentials           │
    │ ├─ Upload GGUF to S3                  │
    │ ├─ Verify S3 upload                   │
    │ └─ Set commit status to "success"      │
    └────────────────────────────────────────┘
```

### Setting Up GitHub Actions Secrets

For GitHub Actions to work, you need to add AWS credentials:

1. Go to: https://github.com/EsraaMosaad/E-commerce-Business-Intelligence-Chatbot-/settings/secrets/actions
2. Click **"New repository secret"** and add:
   - `AWS_ROLE_ARN` = `arn:aws:iam::123456789012:role/GitHubActionsRole` (OIDP role)
   - `AWS_ACCESS_KEY_ID` = your access key (alternative to role)
   - `AWS_SECRET_ACCESS_KEY` = your secret key
3. Go to **Settings → Variables → Actions** and add:
   - `S3_BUCKET_NAME` = `<NETID>-ecom-chatbot`

---

## 7. File-by-File Usage Guide

### Training Files (Person 2)

| File | What It Does | How to Use |
|---|---|---|
| `training/finetune.ipynb` | Complete Colab notebook — loads real data, fine-tunes, exports GGUF | Upload to Colab, Runtime → T4 GPU, run all blocks |
| `training/hyperparameters.md` | All hyperparameters with rationale | Copy into Sections 3 & 5 of final report |
| `training/eval_prompts.md` | 5 evaluation prompts + expected outputs | Run BLOCK 15 in Colab, add real outputs |

### Spark Files (Person 1 — Included for Context)

| File | What It Does | How to Use |
|---|---|---|
| `spark/spark_preprocess.py` | Full PySpark pipeline for EMR | Person 1 runs on AWS EMR |
| `spark/run_commands.md` | EMR cluster + job submission commands | Person 1 copies and runs commands |

### Deployment Files (For Person 3)

| File | What It Does | How to Use |
|---|---|---|
| `deployment/backend_rag.py` | RAG layer: FAISS + Ollama + CLI chat | Copy to EC2: `python backend_rag.py --cli` |
| `deployment/model_load_instructions.md` | Step-by-step Ollama setup | Person 3 reads this |
| `deployment/deploy_commands.md` | All EC2 commands in one place | Person 3 copies commands |
| `deployment/knowledge/amazon_profile.md` | RAG context: Amazon company profile | Copied to EC2 at `knowledge/` |
| `deployment/knowledge/alibaba_profile.md` | RAG context: Alibaba company profile | Copied to EC2 at `knowledge/` |
| `deployment/knowledge/walmart_profile.md` | RAG context: Walmart company profile | Copied to EC2 at `knowledge/` |
| `deployment/knowledge/market_trends.md` | RAG context: E-commerce market trends | Copied to EC2 at `knowledge/` |

### Terraform Files (Person 3)

| File | What It Does | How to Use |
|---|---|---|
| `terraform/main.tf` | Infrastructure code (VPC, EC2, S3, IAM) | `terraform apply` creates everything |
| `terraform/variables.tf` | Input variables with defaults | Edit `terraform.tfvars` |
| `terraform/terraform.tfvars.example` | Template — copy to `terraform.tfvars` | Fill in your NETID, IP, key name |
| `terraform/user_data.sh` | Cloud-init: auto-installs Ollama, RAG, OpenWebUI | Runs automatically on EC2 first boot |
| `terraform/outputs.tf` | Shows EC2 IP, URL after apply | Run `terraform output` |

### GitHub Actions Files

| File | What It Does | How to Use |
|---|---|---|
| `.github/workflows/terraform.yml` | IaC pipeline: validate → plan → apply → destroy | Push to main — auto-runs |
| `.github/workflows/upload_model.yml` | Upload GGUF to S3 via GitHub | Click "Run workflow" in GitHub Actions |

### Documentation Files

| File | What It Does | How to Use |
|---|---|---|
| `README.md` | Full project overview + replication steps | First thing everyone reads |
| `docs/submission_guide.md` | Complete submission instructions | Main reference for Person 2 |
| `docs/Person2_Report_Sections.md` | Sections 3 & 5 for final report | Copy-paste into LaTeX |
| `docs/file_guide.md` | File-by-file explanation | Read to understand all files |
| `docs/architecture_diagram.svg` | Architecture flow diagram | Include in report |

---

## 8. How to Upload Everything to GitHub

### Step 1: Clone Your GitHub Repo

```bash
git clone https://github.com/EsraaMosaad/E-commerce-Business-Intelligence-Chatbot-.git
cd E-commerce-Business-Intelligence-Chatbot-
```

### Step 2: Copy All Files

Copy all files from `/workspace/ecom-chatbot/` to your local repo directory.

### Step 3: Create terraform.tfvars (NOT committed to Git)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# ⚠️ IMPORTANT: terraform.tfvars contains sensitive AWS credentials
# Add it to .gitignore if not already there:
echo "terraform.tfvars" >> ../.gitignore
```

### Step 4: Configure Git (If First Time)

```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

### Step 5: Add All Files and Commit

```bash
git add .
git status  # Check what will be committed
git commit -m "feat: complete e-commerce BI chatbot with QLoRA fine-tuning

- training/finetune.ipynb: Real data fine-tuning on Google Colab
- deployment/: RAG backend, Ollama setup, EC2 commands
- terraform/: Full IaC (VPC, EC2, S3, IAM, GitHub Actions)
- docs/: Architecture diagram, report sections, file guide
- Added architecture diagram with Mermaid SVG
- Added terraform.yml and upload_model.yml GitHub Actions workflows"
```

### Step 6: Push to GitHub

```bash
git push origin main
```

### Step 7: Verify Upload

Go to: https://github.com/EsraaMosaad/E-commerce-Business-Intelligence-Chatbot-/tree/main
Check that all files are visible.

### GitHub Actions Verification

Go to: **Actions** tab on your GitHub repo — you should see the workflows ready to run.

---

## Quick Reference: Key Commands

### Person 2 (Fine-Tuning)
```bash
# On Google Colab:
# 1. Upload finetune.ipynb
# 2. Runtime → T4 GPU
# 3. Run all blocks
# 4. Download GGUF from Colab file browser
# 5. Upload to S3:
aws s3 cp ~/Downloads/tinyllama-chat.Q4_K_M.gguf \
  s3://<NETID>-ecom-chatbot/model/
```

### Person 3 (Deployment)
```bash
# Option A: Terraform (Recommended)
cd terraform
terraform init
terraform apply -var-file=terraform.tfvars

# Option B: Manual
ssh -i key.pem ubuntu@<EC2-IP>
# ... see deployment/deploy_commands.md
```

### Verify Everything Works
```bash
# Test Ollama API
curl http://localhost:11434/api/generate -d '{
  "model": "ecom-chatbot",
  "prompt": "Give me a SWOT analysis for Amazon.",
  "stream": false
}'

# Test OpenWebUI (in browser)
# http://<EC2-Public-IP>:3000
```

---

*Author: MiniMax Agent (for Person 2)*
*Last updated: 2026-04-25*
*Course: CISC 886 — Cloud Computing | Queen's University*
