# E-commerce Business Intelligence Chatbot - Group 25fltp

**Course:** CISC 886 - Cloud Computing, Queen's University  
**Project:** End-to-end cloud-based e-commerce BI chatbot  
**Region:** `us-east-1`  
**Live demo:** `http://<ec2_public_ip>:3000`

This repository contains the full replication workflow for an AWS-based chatbot pipeline. The system preprocesses Amazon Reviews 2023 data with PySpark on Amazon EMR, fine-tunes TinyLlama-1.1B with QLoRA in Google Colab, exports the model to GGUF, and deploys it on EC2 with Ollama and OpenWebUI.

---

## 1. Repository Structure

```text
25fltp-ecom-chatbot/
├── README.md
├── scripts/
│   ├── run_emr.py                  # Optional: downloads raw category files then preprocesses
│   └── run_emr_fast.py             # Final used path: preprocessing-only EMR run
├── spark/
│   ├── spark_preprocess.py         # PySpark ETL and instruction-generation pipeline
│   └── scripts/
│       └── emr_bootstrap.sh        # EMR bootstrap dependencies
├── training/
│   └── finetune.ipynb              # QLoRA fine-tuning notebook
├── terraform/
│   ├── main.tf                     # VPC, subnet, SGs, IAM, S3, EC2
│   ├── variables.tf
│   ├── terraform.tfvars.example
│   └── user_data.sh                # EC2 bootstrap for Ollama/OpenWebUI
├── deployment/
│   ├── deploy_commands.md
│   ├── model_load_instructions.md
│   ├── backend_rag.py
│   └── knowledge/
└── img/
    └── architecture_diagram.gif
```

---

## 2. Prerequisites

Install and configure the following before running the pipeline:

- AWS CLI configured with `aws configure`
- Terraform
- Python 3.10+
- Existing AWS key pair named `25fltp-ecom-key`
- Google Colab with T4 GPU runtime
- Access to the S3 bucket name `25fltp-ecom-chatbot`

The expected AWS region is:

```bash
us-east-1
```

---

## 3. Phase 1 - Provision Base Infrastructure with Terraform

Start by creating the VPC, subnet, route table, security groups, S3 bucket, and IAM roles. The EC2 instance should be created after the fine-tuned GGUF model has been uploaded to S3.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
```

Apply the base infrastructure first:

```bash
terraform apply \
  -target=aws_vpc.main \
  -target=aws_internet_gateway.main \
  -target=aws_subnet.public \
  -target=aws_route_table.main \
  -target=aws_route_table_association.public \
  -target=aws_security_group.ec2_sg \
  -target=aws_security_group.emr_sg \
  -target=aws_s3_bucket.main \
  -target=aws_iam_role.emr_service_role \
  -target=aws_iam_role_policy_attachment.emr_service \
  -target=aws_iam_role.emr_ec2_role \
  -target=aws_iam_role_policy_attachment.emr_ec2 \
  -target=aws_iam_instance_profile.emr_profile \
  -target=aws_iam_instance_profile.ec2_profile
```

Check Terraform outputs:

```bash
terraform output
```

The EMR launcher reads the subnet ID from Terraform output, so this step must finish before running EMR.

---

## 4. Phase 2 - Prepare S3 Prefixes

Create the expected S3 prefixes. The PySpark pipeline reads raw category files from `raw_input/<category>/` and writes outputs to `processed/`.

```bash
cd ..
aws s3api put-object --bucket 25fltp-ecom-chatbot --key raw_input/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key processed/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key model/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key logs/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key scripts/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key code/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key deployment/
```

If the raw category files are not already staged in S3, use `scripts/run_emr.py`. It downloads the nine category JSONL files to `raw_input/` and then runs preprocessing.

```bash
python scripts/run_emr.py
```

If the raw category files are already staged in S3, use the faster preprocessing-only launcher used for the final run:

```bash
python scripts/run_emr_fast.py
```

The final run uses:

```text
Cluster name: 25fltp-FAST-PREPROCESS-PIPELINE
Release: emr-7.1.0
Applications: Spark, Hadoop
Instance type: m6i.xlarge
Instance count: 3
Max per category: 50,000
Output: s3://25fltp-ecom-chatbot/processed/
Auto-terminate: enabled
```

Monitor the EMR cluster:

```bash
aws emr list-clusters --active --region us-east-1
aws emr describe-cluster --cluster-id <cluster-id> --region us-east-1
```

Expected processed outputs:

```text
s3://25fltp-ecom-chatbot/processed/train.jsonl/
s3://25fltp-ecom-chatbot/processed/val.jsonl/
s3://25fltp-ecom-chatbot/processed/test.jsonl/
```

Final EDA statistics used in the report:

| Split | Samples | Avg. character length |
|---|---:|---:|
| Train | 360,277 | 285.91 |
| Validation | 44,874 | 284.65 |
| Test | 44,849 | 286.99 |
| Total | 450,000 | 285.85 |

---

## 5. Phase 3 - Fine-Tune the Model in Google Colab

Open the training notebook:

```text
training/finetune.ipynb
```

Use a T4 GPU runtime and run the notebook cells in order. The notebook downloads the processed JSONL data from S3, formats the text field, applies QLoRA adapters to TinyLlama, trains on a 70,000-record subset, evaluates the model, and exports the final model to GGUF.

Fine-tuning configuration:

| Parameter | Value |
|---|---|
| Base model | `unsloth/tinyllama-chat-bnb-4bit` |
| Fine-tuning method | QLoRA / PEFT |
| Training subset | 70,000 samples |
| Train/eval split | 63,000 / 7,000 |
| Batch size | 2 |
| Gradient accumulation | 4 |
| Effective batch size | 8 |
| Learning rate | `2e-4` |
| Epoch setting | 1 |
| Max optimizer steps | 300 |
| LoRA rank | 16 |
| LoRA alpha | 16 |
| LoRA dropout | 0 |
| Context length | 2048 |
| Final validation loss | 0.3908 |
| GGUF quantization | `Q4_K_M` |

After export, upload the GGUF model to S3:

```bash
aws s3 cp ./outputs/ecom_chatbot_gguf_gguf_gguf_gguf/tinyllama-chat.Q4_K_M.gguf \
  s3://25fltp-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf
```

If the nested Unsloth export path changes, locate the file with:

```bash
find ./outputs -name "*.gguf" -type f
```

---

## 6. Phase 4 - Upload Deployment Files to S3

The EC2 `user_data.sh` script expects the RAG backend and knowledge files under the `deployment/` prefix.

```bash
aws s3 cp deployment/backend_rag.py s3://25fltp-ecom-chatbot/deployment/backend_rag.py
aws s3 cp deployment/knowledge/ s3://25fltp-ecom-chatbot/deployment/knowledge/ --recursive
```

---

## 7. Phase 5 - Deploy EC2, Ollama, and OpenWebUI

After the GGUF model is in S3, apply the full Terraform configuration to create the EC2 chatbot server.

```bash
cd terraform
terraform apply
```

Terraform provisions the EC2 instance and passes `user_data.sh` to the server. The bootstrap script installs Ollama, downloads `tinyllama-chat.Q4_K_M.gguf` from S3, registers the model as `ecom-chatbot`, installs OpenWebUI and RAG dependencies, enables Ollama, and starts OpenWebUI on port 3000.

Get the public IP:

```bash
terraform output ec2_public_ip
```

Open the interface in a browser:

```text
http://<ec2_public_ip>:3000
```

---

## 8. Phase 6 - Verification Commands

SSH into the EC2 instance:

```bash
ssh -i 25fltp-ecom-key.pem ubuntu@<ec2_public_ip>
```

Verify the model is registered in Ollama:

```bash
ollama list
```

Expected model name:

```text
ecom-chatbot:latest
```

Test the Ollama API:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "ecom-chatbot",
  "prompt": "Perform a SWOT analysis for a new organic coffee brand entering the Amazon US market.",
  "stream": false
}'
```

Check OpenWebUI:

```bash
ps aux | grep open-webui | grep -v grep
curl -I http://localhost:3000
```

---

## 9. AWS Cost Summary

This cost table reflects the short project execution window, not a full monthly production deployment.

| Service | Usage estimate | Approx. cost |
|---|---|---:|
| Amazon EMR | 3-node `m6i.xlarge` cluster for about 0.5 hours | $0.36 |
| Amazon EC2 | `t3.xlarge` instance for about 4 hours of deployment/testing | $0.66 |
| Amazon S3 | About 136 GB stored briefly for raw data, processed data, logs, and model artifacts | $0.73 |
| Data transfer | Minimal same-region transfer in `us-east-1` | $0.00 |
| **Total** | Short execution estimate | **$1.75** |

The AWS Pricing Calculator screenshot in the report shows a monthly reference estimate of about $98.86. The project execution estimate is lower because EMR and EC2 were used for short windows and EMR was terminated after preprocessing.

---

## 10. Troubleshooting

### EMR fails because raw files are missing

Use the downloader pipeline:

```bash
python scripts/run_emr.py
```

Or manually upload category files under:

```text
s3://25fltp-ecom-chatbot/raw_input/<Category>/<Category>.jsonl
```

### GGUF file is not found

```bash
find ./outputs -name "*.gguf" -type f
```

Then upload the discovered `.gguf` file to:

```text
s3://25fltp-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf
```

### Ollama is not responding

```bash
sudo systemctl status ollama
sudo systemctl restart ollama
curl http://localhost:11434/api/tags
```

### OpenWebUI is not visible in the browser

Confirm the process is running and that port 3000 is open in the EC2 security group:

```bash
ps aux | grep open-webui | grep -v grep
curl -I http://localhost:3000
```

---

## 11. References

- TinyLlama: Zhang et al., 2024
- LoRA: Hu et al., 2022
- QLoRA: Dettmers et al., 2023
- Amazon Reviews 2023: Hou et al., 2024
- Unsloth: https://unsloth.ai
- Ollama: https://ollama.com
- OpenWebUI: https://openwebui.com
