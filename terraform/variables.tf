# terraform/variables.tf
# Input Variables for EC2 Deployment

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "instance_type" {
  description = "EC2 instance type for the chatbot"
  type        = string
  default     = "t3.large" # 2 vCPU, 8 GB RAM — sufficient for TinyLlama-1.1B GGUF
}

variable "ami_id" {
  description = "Ubuntu 22.04 AMI ID (update with your region-specific AMI)"
  type        = string
  default     = "ami-05575bertyyy0ca6e" # us-east-1 default — replace with your actual AMI
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "allowed_ip" {
  description = "Your IP address for SSH/HTTP access (CIDR notation)"
  type        = string
  default     = "0.0.0.0/0" # CHANGE THIS to your actual IP (e.g., "203.0.113.42/32")
}

variable "s3_bucket_name" {
  description = "S3 bucket name for storing the GGUF model"
  type        = string
  default     = "25fltp-ecom-chatbot"
}

variable "key_name" {
  description = "SSH key pair name (must exist in your AWS account)"
  type        = string
  default     = "25fltp-ecom-key"
}

variable "ollama_model_path" {
  description = "S3 path to the GGUF model file"
  type        = string
  default     = "model/tinyllama-chat.Q4_K_M.gguf"
}

# ─────────────────────────────────────────────────────────────────────────────
# EMR Instance Configuration
# ─────────────────────────────────────────────────────────────────────────────

variable "emr_master_instance_type" {
  description = "EMR master node instance type"
  type        = string
  default     = "m5.xlarge" # 4 vCPU, 16 GB RAM — sufficient for Spark driver
}

variable "emr_core_instance_type" {
  description = "EMR core/task node instance type"
  type        = string
  default     = "m5.xlarge" # 4 vCPU, 16 GB RAM — good for Spark executors
}

variable "emr_core_instance_count" {
  description = "Number of EMR core/task nodes"
  type        = number
  default     = 2  # 1 master + 2 core = 3 nodes total
}
