# 📋 Submission Checklist — Group 25fltp E-commerce BI Chatbot

## Project Overview
- **Course**: CISC 886 — Cloud Computing
- **Group**: 25fltp
- **Project**: E-commerce Business Intelligence Chatbot
- **Architecture**: AWS (VPC + EMR + EC2 + S3) + Terraform + GitHub Actions
- **Fine-tuned Model**: TinyLlama-1.1B (QLoRA → GGUF → Ollama)

---

## Data Preprocessing (PySpark)

### Files Required
- [ ] `spark/spark_preprocess.py` — PySpark ETL pipeline for Amazon reviews
- [ ] `spark/run_commands.sh` — Manual EMR run commands
- [ ] `spark/scripts/emr_bootstrap.sh` — Bootstrap script for EMR nodes
- [ ] `terraform/main.tf` (EMR section) — Terraform EMR cluster definition
- [ ] `terraform/variables.tf` (EMR variables) — EMR instance types

### Steps to Execute
1. Copy `spark/spark_preprocess.py` to EMR master node
2. Or trigger via GitHub Actions → Terraform Apply → EMR cluster
3. Run: `spark-submit --master yarn --deploy-mode cluster spark_preprocess.py`
4. Outputs saved to: `s3://25fltp-ecom-chatbot/processed/`

### Verification
- [ ] EMR cluster created: `25fltp-ecom-spark-cluster`
- [ ] PySpark job completes successfully
- [ ] Processed data in S3: `s3://25fltp-ecom-chatbot/processed/`

---

## Model Fine-Tuning (QLoRA → GGUF)

### Files Required
- [ ] `training/finetune_all_categories.ipynb` — Unified notebook for all 9 categories
- [ ] `training/finetune.ipynb` — Original single-category notebook
- [ ] `docs/model_load_instructions.md` — How to load and test GGUF

### Steps to Execute (Local/Colab)
1. Open `training/finetune_all_categories.ipynb` in Google Colab
2. Run BLOCK 1-5: Install dependencies, load 9 categories × 10k samples
3. Run BLOCK 6-10: QLoRA fine-tuning with Unsloth
4. Run BLOCK 13: Export to GGUF (Quadruple-nested: `ecom_chatbot_gguf_gguf_gguf_gguf/`)
5. Run BLOCK 15: Test with SWOT/Competitor/Market Trends prompts
6. Upload GGUF to S3: `s3://25fltp-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf`

### Verification
- [ ] Training loss: 2.36 → 0.55 (convergence)
- [ ] GGUF file size: ~668 MB
- [ ] GGUF uploaded to S3
- [ ] Model inference produces structured BI responses

### Categories Covered (9/9)
| Category | Task Type | Query Examples |
|----------|-----------|----------------|
| Electronics | SWOT, Competitor, Market Trends | Product comparison, market analysis |
| Clothing_Shoes_and_Jewelry | Product Category, Customer Sentiment | Fashion trends, style analysis |
| Home_and_Kitchen | Review Intelligence, Pricing | Kitchen appliances, home goods |
| Books | Market Trends, Sentiment | Publishing trends, reader preferences |
| Sports_and_Outdoors | SWOT, Competitor | Sports gear, outdoor equipment |
| Beauty_and_Personal_Care | Customer Sentiment, Pricing | Beauty products, skincare |
| Toys_and_Games | Market Trends, Product Category | Toy trends, game analysis |
| Grocery_and_Gourmet_Food | Review Intelligence, SWOT | Food products, beverage market |
| Pet_Supplies | Competitor, Sentiment | Pet products, pet market |

---

## System Deployment (EC2 + Ollama + OpenWebUI)

### Files Required
- [ ] `terraform/main.tf` (EC2 section) — Complete infrastructure
- [ ] `terraform/variables.tf` — All variables including EMR
- [ ] `terraform/terraform.tfvars.example` — Template for deployment
- [ ] `terraform/user_data.sh` — Cloud-init for auto-provisioning
- [ ] `deployment/deploy_commands.md` — SSH commands and Modelfile
- [ ] `deployment/backend_rag.py` — RAG layer (FAISS + sentence-transformers)

### Steps to Execute (AWS Console or CLI)
1. Create key pair: `25fltp-ecom-key` in us-east-1
2. Copy `terraform/terraform.tfvars.example` → `terraform/terraform.tfvars`
3. Update `allowed_ip` to your IP (e.g., `"203.0.113.42/32"`)
4. Run: `cd terraform && terraform init && terraform apply`

### Terraform Outputs
```
ec2_public_ip    = "54.123.456.789"
openwebui_url   = "http://54.123.456.789:3000"
emr_cluster_id   = "j-XXXXXXXX"
s3_model_path    = "s3://25fltp-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf"
```

### SSH Access
```bash
ssh -i 25fltp-ecom-key.pem ubuntu@<ec2_public_ip>
```

### Verification
- [ ] EC2 instance running with public IP
- [ ] Ollama installed and model registered: `ollama list | grep ecom-chatbot`
- [ ] OpenWebUI accessible: `http://<ec2_public_ip>:3000`
- [ ] Model responds to BI queries (SWOT, Competitor, Market Trends)

---

## Infrastructure — Terraform & GitHub Actions

### Files Required
- [ ] `.github/workflows/terraform.yml` — CI/CD pipeline
- [ ] `.github/workflows/upload_model.yml` — Model upload workflow
- [ ] `terraform/main.tf` — Complete infrastructure
- [ ] `terraform/variables.tf` — All variables
- [ ] `terraform/terraform.tfvars.example` — Template

### GitHub Actions Setup
1. Go to: GitHub Repo → Settings → Secrets and Variables → Actions
2. Add secrets:
   - `AWS_ROLE_ARN` — AWS IAM role ARN for OIDC
   - `MY_IP` — Your IP address for SSH/HTTP access

### OIDC Provider Setup (AWS IAM)
1. Create OIDC identity provider in AWS IAM
2. Create role with trust policy for GitHub
3. Add permissions: EC2, EMR, S3, IAM, VPC
4. Use role ARN as `AWS_ROLE_ARN` secret

### Workflow Triggers
| Workflow | Trigger | Action |
|----------|---------|--------|
| `terraform.yml` | Push to main | Validate + Apply infrastructure |
| `terraform.yml` | PR | Validate + Plan (comment on PR) |
| `terraform.yml` | Branch delete | Destroy resources |
| `upload_model.yml` | Manual dispatch | Upload GGUF to S3 |

---

## Documentation Files

### Files Required
- [ ] `README.md` — Project overview and file structure
- [ ] `docs/submission_checklist.md` — This file
- [ ] `docs/architecture_diagram.svg` — Visual architecture

### README Sections to Verify
- [ ] Project title: "E-commerce BI Chatbot (Group 25fltp)"
- [ ] File structure includes: `terraform/`, `.github/workflows/`, `training/`, `docs/`
- [ ] Architecture diagram shows: Data → Fine-tuning → Deployment → IaC/CI/CD
- [ ] Team members listed with roles (Data, Fine-tuning, Deployment)

---

## Final Submission Structure

```
ecom-chatbot-25fltp/
├── README.md
├── .gitignore
├── training/
│   ├── finetune.ipynb                    # Original (Electronics only)
│   └── finetune_all_categories.ipynb     # NEW (All 9 categories)
├── terraform/
│   ├── main.tf                           # Complete infrastructure
│   ├── variables.tf                      # All variables + EMR
│   ├── terraform.tfvars.example          # Template
│   └── user_data.sh                      # Cloud-init script
├── spark/
│   ├── spark_preprocess.py               # PySpark ETL
│   ├── run_commands.sh                   # Manual EMR commands
│   └── scripts/
│       └── emr_bootstrap.sh             # Bootstrap for EMR nodes
├── deployment/
│   ├── deploy_commands.md                # SSH + Modelfile commands
│   ├── backend_rag.py                    # RAG layer (FAISS)
│   └── model_load_instructions.md        # GGUF loading guide
├── .github/
│   └── workflows/
│       ├── terraform.yml                 # CI/CD pipeline
│       └── upload_model.yml             # Model upload workflow
└── docs/
    ├── complete_guide.md                # Full workflow guide
    ├── file_guide.md                     # File explanation
    ├── submission_checklist.md          # This checklist
    └── architecture_diagram.svg         # Visual diagram
```

---

## AWS Resources Summary

| Resource | Name | Region | Purpose |
|----------|------|--------|---------|
| VPC | 25fltp-ecom-vpc | us-east-1 | Network isolation |
| Subnet | 25fltp-ecom-public-subnet | us-east-1 | EC2 + EMR deployment |
| EMR Cluster | 25fltp-ecom-spark-cluster | us-east-1 | PySpark data preprocessing |
| EC2 Instance | 25fltp-ecom-chatbot-ec2 | us-east-1 | Ollama + OpenWebUI |
| S3 Bucket | 25fltp-ecom-chatbot | us-east-1 | Model + data storage |
| S3 Bucket (State) | 25fltp-terraform-state | us-east-1 | Terraform backend |
| Security Group | 25fltp-ec2-sg | us-east-1 | SSH + HTTP access |
| Security Group | 25fltp-emr-sg | us-east-1 | EMR internal communication |
| IAM Role | 25fltp-ec2-s3-role | us-east-1 | EC2 → S3 access |
| IAM Role | 25fltp-emr-role | us-east-1 | EMR → S3 + EC2 access |

---

## Quick Start Commands

### 1. Fine-tune Model (Person 2)
```bash
# Open in Google Colab
# training/finetune_all_categories.ipynb
# Run BLOCK 1-15 sequentially
```

### 2. Deploy Infrastructure (Person 3)
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your IP
terraform init
terraform apply
```

### 3. Upload Model to S3 (Manual)
```bash
aws s3 cp outputs/ecom_chatbot_gguf_gguf_gguf_gguf/tinyllama-chat.Q4_K_M.gguf \
  s3://25fltp-ecom-chatbot/model/
```

### 4. Access Chatbot
```
OpenWebUI: http://<ec2_public_ip>:3000
SSH:       ssh -i 25fltp-ecom-key.pem ubuntu@<ec2_public_ip>
```

---

## Checklist for Professor Submission

### Code Files
- [ ] All Python files present and documented
- [ ] All Terraform files present with proper variable definitions
- [ ] All GitHub Actions workflows present
- [ ] All notebooks runnable (BLOCK 1-15 complete)

### Documentation
- [ ] README.md updated with Group 25fltp references
- [ ] Architecture diagram shows complete flow
- [ ] File guide explains each file's purpose
- [ ] Submission checklist (this file) completed

### Infrastructure
- [ ] Terraform validates: `terraform validate`
- [ ] GitHub Actions passes on PR
- [ ] All 3 persons' work integrated

### Model
- [ ] GGUF exported successfully (~668 MB)
- [ ] GGUF uploaded to S3
- [ ] Model inference tested with real queries

---

## Troubleshooting

### Terraform Issues
- **Error**: "S3 bucket not found" → Run `terraform init` first
- **Error**: "AMI not found" → Update `ami_id` in terraform.tfvars
- **Error**: "Key pair not found" → Create in AWS Console: EC2 → Key Pairs

### Model Issues
- **Error**: "GGUF path not found" → Check for quadruple-nesting: `ecom_chatbot_gguf_gguf_gguf_gguf/`
- **Error**: "Model not responding" → Run `ollama list` on EC2, check OpenWebUI logs

### EMR Issues
- **Error**: "Instance type not available" → Use m6i.xlarge instead
- **Error**: "Bootstrap action failed" → Check S3 path: `s3://25fltp-ecom-chatbot/scripts/emr-bootstrap.sh`

---

**Last Updated**: 2026-04-27
**Group**: 25fltp
**Version**: Final Submission