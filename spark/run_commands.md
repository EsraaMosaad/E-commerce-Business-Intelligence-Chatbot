# AWS EMR — Cluster Setup & Job Submission Commands
# =====================================================
# Run these commands after setting up your AWS credentials

# Prerequisites

# 1. Configure AWS CLI (do once)
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)

# 2. Create S3 bucket (replace 25fltp with your Queen's NetID)
aws s3 mb s3://25fltp-ecom-chatbot

# 3. Create directory structure on S3
aws s3api put-object --bucket 25fltp-ecom-chatbot --key raw/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key processed/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key model/
aws s3api put-object --bucket 25fltp-ecom-chatbot --key logs/


# Option A: Submit Spark Job via AWS CLI

# 1. Copy preprocessing script to S3
aws s3 cp spark/spark_preprocess.py s3://25fltp-ecom-chatbot/code/spark_preprocess.py

# 2. Create EMR cluster (m6i.2xlarge = 8 vCPU, 32 GB RAM)
aws emr create-cluster --name "25fltp-ecom-chatbot-preprocess" --release-label emr-7.1.0 --instance-type m6i.2xlarge --instance-count 3 --applications Name=Spark Name=Hadoop Name=JupyterEnterpriseGateway --ec2-attributes KeyName=25fltp-ecom-key,SubnetId=subnet-09ae981901f2a9451,InstanceProfile=25fltp-emr-profile --service-role 25fltp-emr-role --bootstrap-actions 'Path=s3://25fltp-ecom-chatbot/scripts/emr-bootstrap.sh' --steps 'Type=Spark,Name=PreprocessAmazonReviews,ActionOnFailure=CONTINUE,Args=["--deploy-mode","cluster","--conf","spark.executor.memory=16G","--conf","spark.executor.cores=4","--conf","spark.driver.memory=8G","--conf","spark.sql.shuffle.partitions=400","--py-files","s3://25fltp-ecom-chatbot/code/spark_preprocess.py","s3://25fltp-ecom-chatbot/code/spark_preprocess.py","--output-dir","s3://25fltp-ecom-chatbot/processed","--s3-bucket","s3://25fltp-ecom-chatbot","--categories","Electronics","Clothing_Shoes_and_Jewelry","Home_and_Kitchen","Books","Sports_and_Outdoors","Beauty_and_Personal_Care","Toys_and_Games","Grocery_and_Gourmet_Food","Pet_Supplies","--max-per-category","200000"]' --region us-east-1

# 3. Monitor cluster status
aws emr describe-cluster --cluster-id <cluster-id> --query 'Cluster.Status'

# 4. List cluster steps
aws emr list-steps --cluster-id <cluster-id>


# Option B: SSH into Master Node

# 1. Get master public DNS
aws emr describe-cluster --cluster-id <cluster-id> \
  --query 'Cluster.MasterPublicDnsName' --output text

# 2. SSH into master node
ssh -i 25fltp-ecom-key.pem ubuntu@<master-dns>

# 3. On master node: install dependencies
pip install pyspark datasets pandas pyarrow

# 4. On master node: clone repo
git clone https://github.com/EsraaMosaad/E-commerce-Business-Intelligence-Chatbot-.git
cd E-commerce-Business-Intelligence-Chatbot-

# 5. Run preprocessing locally on EMR master
python spark/spark_preprocess.py \
  --output-dir ./processed \
  --categories Electronics Clothing_Shoes_and_Jewelry Home_and_Kitchen \
               Books Sports_and_Outdoors Beauty_and_Personal_Care \
               Toys_and_Games Grocery_and_Gourmet_Food Pet_Supplies \
  --max-per-category 200000

# 6. Upload results to S3
aws s3 cp ./processed/train.jsonl s3://25fltp-ecom-chatbot/processed/train.jsonl
aws s3 cp ./processed/val.jsonl s3://25fltp-ecom-chatbot/processed/val.jsonl
aws s3 cp ./processed/test.jsonl s3://25fltp-ecom-chatbot/processed/test.jsonl

# 7. Download to local repo (for Colab access)
aws s3 cp s3://25fltp-ecom-chatbot/processed/train_sample.jsonl ./data/processed/train_sample.jsonl


# ── Option C: Download Directly from HuggingFace (Recommended for Prototype) ─

# For quick prototype testing, skip Spark and load directly from HuggingFace:
# See: training/finetune.ipynb (BLOCK 3 — Load Dataset from HuggingFace)
# This approach works directly on Colab without EMR:
#   from datasets import load_dataset
#   ds = load_dataset("McAuley-Lab/Amazon-Reviews-2023", "raw_review_Electronics", split="full")


# ── Verify Output ──────────────────────────────────────────

# Check train.jsonl
aws s3 cp s3://25fltp-ecom-chatbot/processed/train.jsonl - | head -1 | python3 -m json.tool

# Count lines
aws s3 cp s3://25fltp-ecom-chatbot/processed/train.jsonl - | wc -l
aws s3 cp s3://25fltp-ecom-chatbot/processed/val.jsonl - | wc -l
aws s3 cp s3://25fltp-ecom-chatbot/processed/test.jsonl - | wc -l

# Download full dataset locally
aws s3 sync s3://25fltp-ecom-chatbot/processed/ ./processed/


# ── Troubleshooting ────────────────────────────────────────

# View Spark logs
aws emr describe-step --cluster-id <cluster-id> --step-id <step-id> \
  --query 'Step.Status'

# SSH tunnel for Spark UI
ssh -i 25fltp-ecom-key.pem -L 20888:<cluster-id>:20888 ubuntu@<master-dns>

# Resize cluster
aws emr modify-instance-groups \
  --cluster-id <cluster-id> \
  --instance-groups \
    InstanceGroupId=<group-id>,InstanceCount=20

# Terminate cluster
aws emr terminate-clusters --cluster-id <cluster-id>
