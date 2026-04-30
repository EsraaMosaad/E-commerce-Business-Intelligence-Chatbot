import subprocess
import json
import sys

# --- CONFIGURATION ---
BUCKET_NAME = "25fltp-ecom-chatbot"
EMR_PROFILE = "25fltp_emr_profile"
SERVICE_ROLE = "25fltp_emr_service_role"
REGION = "us-east-1"
# ---------------------

def get_terraform_outputs():
    """Fetches dynamic infrastructure IDs from Terraform state."""
    try:
        res = subprocess.run(
            ["terraform", "output", "-json"], 
            cwd="terraform", 
            capture_output=True, 
            text=True, 
            check=True
        )
        return json.loads(res.stdout)
    except Exception:
        print("[ERROR] Failed to read Terraform outputs. Make sure you ran 'terraform apply' first.")
        sys.exit(1)

def main():
    print("Starting FAST EMR Preprocessing Pipeline...")
    
    # 1. Upload the latest PySpark scripts to S3
    print("Uploading scripts to S3...")
    subprocess.run(["aws", "s3", "cp", "spark/spark_preprocess.py", f"s3://{BUCKET_NAME}/code/spark_preprocess.py"])
    subprocess.run(["aws", "s3", "cp", "spark/scripts/emr_bootstrap.sh", f"s3://{BUCKET_NAME}/scripts/emr-bootstrap.sh"])

    # 2. Get the Subnet ID from Terraform
    outputs = get_terraform_outputs()
    subnet_id = outputs['subnet_id']['value']

    # 3. Define Big Data parameters
    categories = [
        "Electronics", "Books", "Home_and_Kitchen", 
        "Clothing_Shoes_and_Jewelry", "Toys_and_Games", "Sports_and_Outdoors",
        "Beauty_and_Personal_Care", "Grocery_and_Gourmet_Food", "Pet_Supplies"
    ]
    max_samples = "50000"  # Massive scale (Total ~450,000)
    output_s3_path = f"s3://{BUCKET_NAME}/processed"

    print(f"Processing {len(categories)} categories ({max_samples} samples max each) to: {output_s3_path}")

    # 4. Configure the PySpark Step (No Downloads)
    spark_step = [{
        "Name": "BIG-DATA-Preprocessing-ONLY",
        "ActionOnFailure": "TERMINATE_CLUSTER",
        "Jar": "command-runner.jar",
        "Args": [
            "spark-submit", 
            "--deploy-mode", "client",
            "--conf", "spark.executor.memory=8G",
            "--conf", "spark.executor.cores=4",
            "--conf", "spark.driver.memory=8G",
            "--py-files", f"s3://{BUCKET_NAME}/code/spark_preprocess.py",
            f"s3://{BUCKET_NAME}/code/spark_preprocess.py",
            "--output-path", output_s3_path,
            "--s3-bucket", BUCKET_NAME,
            "--categories"
        ] + categories + ["--max-per-category", max_samples]
    }]

    # 5. Launch the EMR Cluster
    print("Provisioning EMR Cluster (3 Nodes, m6i.xlarge)...")
    cmd = [
        "aws", "emr", "create-cluster",
        "--name", "25fltp-FAST-PREPROCESS-PIPELINE",
        "--release-label", "emr-7.1.0",
        "--instance-type", "m6i.xlarge",
        "--instance-count", "3",
        "--ebs-root-volume-size", "100",
        "--applications", "Name=Spark", "Name=Hadoop",
        "--ec2-attributes", f"KeyName=25fltp-ecom-key,SubnetId={subnet_id},InstanceProfile={EMR_PROFILE}",
        "--service-role", SERVICE_ROLE,
        "--log-uri", f"s3://{BUCKET_NAME}/logs/",
        "--bootstrap-actions", f"Path=s3://{BUCKET_NAME}/scripts/emr-bootstrap.sh",
        "--auto-terminate", # Automatically shut down when done to save money!
        "--steps", json.dumps(spark_step),
        "--region", REGION
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if res.returncode == 0:
        cluster_info = json.loads(res.stdout)
        print(f"[SUCCESS] FAST Preprocessing cluster is launching with ID: {cluster_info['ClusterId']}")
        print("Check the AWS Console to monitor the progress.")
    else:
        print("[ERROR] Error launching EMR Cluster:")
        print(res.stderr)

if __name__ == "__main__":
    main()
