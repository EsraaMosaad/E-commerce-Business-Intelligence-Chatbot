import subprocess
import json
import sys

def get_terraform_output():
    print("Fetching dynamic IDs from Terraform...")
    res = subprocess.run(["terraform", "output", "-json"], cwd="terraform", capture_output=True, text=True)
    if res.returncode != 0:
        print("Error getting Terraform outputs. Make sure you ran 'terraform apply' first.")
        return None
    return json.loads(res.stdout)

# 1. Sync scripts to S3
print("Syncing scripts to S3...")
subprocess.run(["aws", "s3", "cp", "spark/spark_preprocess.py", "s3://25fltp-ecom-chatbot/code/spark_preprocess.py"])
subprocess.run(["aws", "s3", "cp", "spark/scripts/emr_bootstrap.sh", "s3://25fltp-ecom-chatbot/scripts/emr-bootstrap.sh"])

# 2. Get Dynamic IDs
outputs = get_terraform_output()
if not outputs: sys.exit(1)

SUBNET_ID = outputs['subnet_id']['value']
EMR_PROFILE = "25fltp_emr_profile"
SERVICE_ROLE = "25fltp_emr_service_role"
BUCKET = "25fltp-ecom-chatbot"

# 3. Define the "BIG DATA" 9 Categories
CATEGORIES = [
    "Electronics", "Books", "Home_and_Kitchen", 
    "Clothing_Shoes_and_Jewelry", "Toys_and_Games", "Sports_and_Outdoors",
    "Beauty_and_Personal_Care", "Grocery_and_Gourmet_Food", "Pet_Supplies"
]

# 4. Create the "Direct Download" steps (CLI Shorthand Format)
download_steps = []
for cat in CATEGORIES:
    url = f"https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw/review_categories/{cat}.jsonl"
    s3_path = f"s3://{BUCKET}/raw_input/{cat}/{cat}.jsonl"
    
    step = {
        "Name": f"Download-{cat}",
        "ActionOnFailure": "CONTINUE",
        "Jar": "command-runner.jar",
        "Args": ["bash", "-c", f"curl -L {url} | aws s3 cp - {s3_path}"]
    }
    download_steps.append(step)

# 5. Add the Preprocessing Step (CLI Shorthand Format)
preprocess_step = {
    "Name": "BIG-DATA-Preprocessing-9-Categories",
    "ActionOnFailure": "CONTINUE",
    "Jar": "command-runner.jar",
    "Args": [
        "spark-submit", "--deploy-mode", "cluster",
        "--conf", "spark.executor.memory=8G",
        "--conf", "spark.executor.cores=4",
        "--conf", "spark.driver.memory=8G",
        "--py-files", f"s3://{BUCKET}/code/spark_preprocess.py",
        f"s3://{BUCKET}/code/spark_preprocess.py",
        "--output-path", f"s3://{BUCKET}/processed",
        "--s3-bucket", BUCKET,
        "--categories"] + CATEGORIES + [
        "--max-per-category", "200000"
    ]
}

all_steps = download_steps + [preprocess_step]

# 6. Launch EMR Cluster
print(f"Launching BIG DATA Cluster (9 Categories, 3 Nodes)...")
cmd = [
    "aws", "emr", "create-cluster",
    "--name", "25fltp-ULTIMATE-BIG-DATA-PIPELINE",
    "--release-label", "emr-7.1.0",
    "--instance-type", "m5.xlarge",
    "--instance-count", "3",
    "--applications", "Name=Spark", "Name=Hadoop",
    "--ec2-attributes", f"KeyName=25fltp-ecom-key,SubnetId={SUBNET_ID},InstanceProfile={EMR_PROFILE}",
    "--service-role", SERVICE_ROLE,
    "--log-uri", f"s3://{BUCKET}/logs/",
    "--bootstrap-actions", f"Path=s3://{BUCKET}/scripts/emr-bootstrap.sh",
    "--steps", json.dumps(all_steps),
    "--region", "us-east-1"
]

res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode == 0:
    cluster_info = json.loads(res.stdout)
    print(f"✅ ULTIMATE Cluster Launching! Cluster ID: {cluster_info['ClusterId']}")
    print("EMR is now processing 9 categories.")
else:
    print("❌ EMR Error:", res.stderr)
