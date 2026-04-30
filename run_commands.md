# 🚀 Project Run Commands: E-commerce BI Chatbot (Group 25fltp)

This guide contains the step-by-step commands to run the entire pipeline for the project, from data preprocessing to model fine-tuning and deployment.

---

## Phase 1: Base Infrastructure (Terraform)
Before running EMR, you must deploy the network, security groups, IAM roles, and S3 bucket. We will deploy everything *except* the EC2 instance for now (since it needs the model from later steps).

### 1. Setup Terraform Variables
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Open terraform.tfvars and update allowed_ip with your IP
```

### 2. Apply Base Infrastructure
Use the `-target` flag or simply comment out the `aws_instance.web_server` in `main.tf`, then run:
```bash
terraform init

# Apply all base infrastructure except EC2
terraform apply -target=aws_vpc.main \
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

---

## Phase 2: Data Preprocessing (AWS EMR & PySpark)

### 1. Initial S3 Setup
Ensure your folders are created in the S3 bucket created by Terraform:
```bash
cd ..
aws s3api put-object --bucket 25fltp-ecom-chatbot --key raw/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key processed/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key model/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key logs/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key scripts/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key code/
```

### 2. Upload Spark Scripts
```bash
aws s3 cp spark/spark_preprocess.py s3://25fltp-ecom-chatbot/code/spark_preprocess.py
aws s3 cp spark/scripts/emr_bootstrap.sh s3://25fltp-ecom-chatbot/scripts/emr-bootstrap.sh
```

### 3. Launch EMR Cluster & Run PySpark Job
Use the provided Python script to automatically fetch dynamic IDs from Terraform and launch the configured EMR cluster:
```bash
python scripts/run_emr.py
```
This script will automatically sync the necessary files to S3, launch the cluster, and start the processing of the 9 categories.
Check EMR job status:
```bash
aws emr describe-cluster --cluster-id <cluster-id> --query 'Cluster.Status'
```

---

## Phase 3: Model Fine-Tuning (Google Colab)

1. Open `training/finetune_all_categories.ipynb` in Google Colab.
2. Run blocks 1-5 to install dependencies and load the processed dataset (from the 9 categories).
3. Run blocks 6-10 for QLoRA fine-tuning with Unsloth.
4. Run block 13 to export the trained model to GGUF format (`Q4_K_M`).
5. Run block 15 to test inference with BI prompts (SWOT, Trends).

### Upload GGUF Model to S3
Once you have the `.gguf` file locally or on Colab, push it to S3:
```bash
aws s3 cp outputs/ecom_chatbot_gguf_gguf_gguf_gguf/tinyllama-chat.Q4_K_M.gguf s3://25fltp-ecom-chatbot/model/
```

---

## Phase 4: Deploy Chatbot (Terraform EC2)

Now that the GGUF model is safely in S3, deploy the EC2 instance which will download the model on startup.

```bash
cd terraform
# Apply the rest of the infrastructure (which is just the EC2 instance now)
terraform apply
```
*Note the output values: `ec2_public_ip` and `openwebui_url`.*

---

## Phase 5: Access & Verify the Chatbot



### 1. Access OpenWebUI
Once the EC2 instance is fully initialized (may take a few minutes for Ollama and the model to load via the user_data script), access the web UI:
```bash
# Navigate in your browser to:
http://<ec2_public_ip>:3000
```

### 2. SSH into EC2 (Troubleshooting)
If you need to verify the model is loaded in Ollama or check backend logs:
```bash
ssh -i 25fltp-ecom-key.pem ubuntu@<ec2_public_ip>

# Check if model is loaded:
ollama list
```
