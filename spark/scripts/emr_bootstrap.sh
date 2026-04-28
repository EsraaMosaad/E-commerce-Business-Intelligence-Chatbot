#!/bin/bash
# spark/scripts/emr_bootstrap.sh
# EMR Bootstrap Action — installs Python dependencies on all nodes
# Referenced in terraform/main.tf: s3://25fltp-ecom-chatbot/scripts/emr-bootstrap.sh
# Upload this to S3: aws s3 cp spark/scripts/emr_bootstrap.sh s3://25fltp-ecom-chatbot/scripts/

set -e

echo "====== EMR Bootstrap: Installing Python dependencies ======"
echo "Node: $(hostname), Started: $(date)"

# Update package list
yum update -y --security 2>/dev/null || apt-get update -y 2>/dev/null

# Install Python 3 and pip (EMR Amazon Linux)
yum install -y python3 python3-pip 2>/dev/null || apt-get install -y python3 python3-pip

# Install PySpark-compatible packages
pip3 install --quiet \
    pandas \
    numpy \
    pyarrow \
    fastparquet \
    requests \
    transformers \
    datasets \
    boto3 \
    scikit-learn

# Symlink python3 to python if needed
which python || ln -s /usr/bin/python3 /usr/bin/python

echo "====== Bootstrap Complete at $(date) ======"