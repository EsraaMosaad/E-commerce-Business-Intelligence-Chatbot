# terraform/main.tf (Complete Infrastructure)
# E-commerce BI Chatbot — Group 25fltp
# Creates: VPC + Subnet + EMR + EC2 + S3 + IAM + Security Groups

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "25fltp-terraform-state"
    key    = "ecom-chatbot/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "E-commerce-BI-Chatbot"
      Environment = var.environment
      Team        = "CISC886-Group25fltp"
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# VPC & Networking
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "25fltp-ecom-vpc"
    Project = "CISC886-E-commerce-BI-Chatbot"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "25fltp-ecom-igw"
  }
}

resource "aws_subnet" "public" {
  vpc                  = aws_vpc.main.id
  cidr_block           = var.public_subnet_cidr
  map_public_ip_on_launch = true
  availability_zone   = "${var.aws_region}a"

  tags = {
    Name = "25fltp-ecom-public-subnet"
  }
}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "25fltp-ecom-rt"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.main.id
}

# ─────────────────────────────────────────────────────────────────────────────
# Security Groups
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_security_group" "ec2_sg" {
  name        = "25fltp-ec2-sg"
  description = "Security group for E-commerce Chatbot EC2"
  vpc_id      = aws_vpc.main.id

  # SSH access — YOUR IP only
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
    description = "SSH from your IP"
  }

  # HTTP/HTTPS for OpenWebUI
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
    description = "OpenWebUI HTTP access"
  }

  # Ollama API — localhost only
  ingress {
    from_port   = 11434
    to_port     = 11434
    protocol    = "tcp"
    cidr_blocks = ["127.0.0.1/32"]
    description = "Ollama API localhost"
  }

  # Outbound: all traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "25fltp-ec2-sg"
  }
}

resource "aws_security_group" "emr_sg" {
  name        = "25fltp-emr-sg"
  description = "Security group for EMR cluster"
  vpc_id      = aws_vpc.main.id

  # SSH from within VPC
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "SSH from VPC"
  }

  # EMR internal communication
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "EMR internal"
  }

  # Outbound: all
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "25fltp-emr-sg"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# IAM Roles
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_iam_role" "ec2_s3_role" {
  name = "25fltp-ec2-s3-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = { Service = "ec2.amazonaws.com" }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ec2_s3_policy" {
  name = "25fltp-ec2-s3-policy"
  role = aws_iam_role.ec2_s3_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:GetObjectVersion", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::25fltp-ecom-chatbot",
          "arn:aws:s3:::25fltp-ecom-chatbot/*"
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "25fltp-ec2-profile"
  role = aws_iam_role.ec2_s3_role.id
}

resource "aws_iam_role" "emr_role" {
  name = "25fltp-emr-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = { Service = "ec2.amazonaws.com" }
      }
    ]
  })
}

resource "aws_iam_role_policy" "emr_policy" {
  name = "25fltp-emr-policy"
  role = aws_iam_role.emr_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          "arn:aws:s3:::25fltp-ecom-chatbot",
          "arn:aws:s3:::25fltp-ecom-chatbot/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "ec2:CreateTags",
          "ec2:RunInstances",
          "ec2:TerminateInstances"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "emr_service_policy" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
  role       = aws_iam_role.emr_role.name
}

resource "aws_iam_instance_profile" "emr_profile" {
  name = "25fltp-emr-profile"
  role = aws_iam_role.emr_role.id
}

# ─────────────────────────────────────────────────────────────────────────────
# EMR Cluster (Person 1: Data Preprocessing)
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_emr_cluster" "preprocessing" {
  name          = "25fltp-ecom-spark-cluster"
  release_label = "emr-7.1.0"
  applications   = ["Spark", "JupyterHub", "Hadoop"]
  service_role   = aws_iam_role.emr_role.arn

  ec2_attributes {
    subnet_id              = aws_subnet.public.id
    emr_managed_master_sg  = aws_security_group.emr_sg.id
    emr_managed_slave_sg   = aws_security_group.emr_sg.id
    instance_profile        = aws_iam_instance_profile.emr_profile.arn
  }

  master_instance_group {
    instance_type = var.emr_master_instance_type
    instance_count = 1
  }

  core_instance_group {
    instance_type = var.emr_core_instance_type
    instance_count = var.emr_core_instance_count
  }

  bootstrap_action {
    path = "s3://25fltp-ecom-chatbot/scripts/emr-bootstrap.sh"
    name = "Install Python dependencies"
  }

  configurations_json = jsonencode([
    {
      Classification = "spark-env"
      ConfigurationProperties = {
        PYSPARK_PYTHON = "/usr/bin/python3"
      }
    }
  ])

  tags = {
    Name    = "25fltp-ecom-spark"
    Project = "CISC886-E-commerce-BI-Chatbot"
  }

  # Auto-terminate after 2 hours to save cost
  termination_protection = false

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_emr_instance_fleet" "spark" {
  cluster_id = aws_emr_cluster.preprocessing.id
  instance_fleet_type = "MASTER"

  instance_type_configs {
    instance_type = var.emr_master_instance_type

    bid_price_as_percentage_of_on_demand_price = 100
    weighted_capacity = 1
  }

  launch_specifications {
    purchase_offering = "ON_DEMAND"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Bucket
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "chatbot" {
  bucket = "25fltp-ecom-chatbot"

  tags = {
    Name    = "25fltp-ecom-chatbot"
    Project = "CISC886-E-commerce-BI-Chatbot"
  }
}

resource "aws_s3_bucket_public_access_block" "chatbot" {
  bucket = aws_s3_bucket.chatbot.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "chatbot" {
  bucket = aws_s3_bucket.chatbot.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# EC2 Instance (Person 3: Deployment)
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_instance" "chatbot" {
  ami           = var.ami_id
  instance_type = var.instance_type
  subnet_id     = aws_subnet.public.id

  key_name   = var.key_name
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  user_data = templatefile("${path.module}/user_data.sh", {
    s3_bucket   = "25fltp-ecom-chatbot"
    model_path  = var.ollama_model_path
    environment = var.environment
  })

  root_block_device {
    volume_size = 100  # GB — larger for model + RAG + OS
    volume_type = "gp3"
  }

  tags = {
    Name = "25fltp-ecom-chatbot-ec2"
    Project = "CISC886-E-commerce-BI-Chatbot"
    Role = "LLM-Inference-Server"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_eip" "chatbot" {
  instance = aws_instance.chatbot.id
  domain   = "vpc"

  tags = {
    Name = "25fltp-ecom-eip"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Outputs
# ─────────────────────────────────────────────────────────────────────────────

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "subnet_id" {
  description = "Public Subnet ID"
  value       = aws_subnet.public.id
}

output "ec2_public_ip" {
  description = "EC2 Public IP for OpenWebUI"
  value       = aws_eip.chatbot.public_ip
}

output "openwebui_url" {
  description = "OpenWebUI URL"
  value       = "http://${aws_eip.chatbot.public_ip}:3000"
}

output "ollama_api_url" {
  description = "Ollama API URL (localhost)"
  value       = "http://localhost:11434"
}

output "emr_cluster_id" {
  description = "EMR Cluster ID for Spark preprocessing"
  value       = aws_emr_cluster.preprocessing.id
}

output "emr_master_dns" {
  description = "EMR Master Node DNS"
  value       = aws_emr_cluster.preprocessing.master_public_dns
}

output "s3_bucket" {
  description = "S3 Bucket Name"
  value       = aws_s3_bucket.chatbot.id
}

output "s3_model_path" {
  description = "S3 Model Path for GGUF upload"
  value       = "s3://25fltp-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf"
}

output "ssh_command" {
  description = "SSH command to connect to EC2"
  value       = "ssh -i <key>.pem ubuntu@${aws_eip.chatbot.public_ip}"
}