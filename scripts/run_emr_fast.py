import subprocess
import json
import sys

def get_terraform_output():
    res = subprocess.run(["terraform", "output", "-json"], cwd="terraform", capture_output=True, text=True)
    if res.returncode != 0:
        return None
    return json.loads(res.stdout)

# 1. Sync the latest Spark code to S3
print("Syncing preprocessing script to S3...")
subprocess.run(["aws", "s3", "cp", "spark/spark_preprocess.py", "s3://25fltp-ecom-chatbot/code/spark_preprocess.py"])

# 2. Get Dynamic IDs
outputs = get_terraform_output()
if not outputs: sys.exit(1)

SUBNET_ID = outputs['subnet_id']['value']
EMR_PROFILE = "25fltp_emr_profile"
SERVICE_ROLE = "25fltp_emr_service_role"
BUCKET = "25fltp-ecom-chatbot"

# 3. Define the 9 Categories
CATEGORIES = [
    "Electronics", "Books", "Home_and_Kitchen", 
    "Clothing_Shoes_and_Jewelry", "Toys_and_Games", "Sports_and_Outdoors",
    "Beauty_and_Personal_Care", "Grocery_and_Gourmet_Food", "Pet_Supplies"
]

# 4. ONLY the Preprocessing Step (No Downloads)
preprocess_step = [{
    "Name": "BIG-DATA-Preprocessing-ONLY",
    "ActionOnFailure": "TERMINATE_CLUSTER",
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
}]

# 5. Launch EMR Cluster
print(f"Launching Preprocessing-ONLY Cluster...")
cmd = [
    "aws", "emr", "create-cluster",
    "--name", "25fltp-FAST-PREPROCESS-PIPELINE",
    "--release-label", "emr-7.1.0",
    "--instance-type", "m5.xlarge",
    "--instance-count", "3",
    "--applications", "Name=Spark", "Name=Hadoop",
    "--ec2-attributes", f"KeyName=25fltp-ecom-key,SubnetId={SUBNET_ID},InstanceProfile={EMR_PROFILE}",
    "--service-role", SERVICE_ROLE,
    "--auto-terminate", # This will shut down the cluster when finished to save money
    "--steps", json.dumps(preprocess_step),
    "--region", "us-east-1"
]

res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode == 0:
    cluster_info = json.loads(res.stdout)
    print(f"✅ Fast Cluster Launching! Cluster ID: {cluster_info['ClusterId']}")
else:
    print("❌ EMR Error:", res.stderr)
