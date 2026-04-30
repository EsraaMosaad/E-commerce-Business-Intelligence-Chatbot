# terraform.tfvars - Group 25fltp
aws_region        = "us-east-1"
environment      = "dev"
instance_type    = "t3.large"
ami_id           = "ami-055744d747c0a1c6e"  # Ubuntu 22.04 LTS in us-east-1 (verified)
vpc_cidr         = "10.0.0.0/16"
public_subnet_cidr = "10.0.1.0/24"

# Restricted to your current IP for security
allowed_ip        = "41.218.155.30/32"

s3_bucket_name   = "25fltp-ecom-chatbot"
key_name         = "25fltp-ecom-key"
ollama_model_path = "model/tinyllama-chat.Q4_K_M.gguf"

# EMR Configuration
emr_master_instance_type  = "m6i.2xlarge"
emr_core_instance_type    = "m6i.2xlarge"
emr_core_instance_count   = 2
