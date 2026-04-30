# terraform/main.tf
provider "aws" {
  region = "us-east-1"
}

# ── 1. NETWORK ─────────────────────────────────────────────────────────────
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { 
    Name = "25fltp-ecom-vpc-FINAL" 
    Project = "Amazon-BI-Chatbot"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "us-east-1a"
  tags = { Name = "25fltp-ecom-public-subnet" }
}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.main.id
}

# ── 2. SECURITY GROUPS ─────────────────────────────────────────────────────
resource "aws_security_group" "ec2_sg" {
  name   = "25fltp-ec2-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "emr_sg" {
  name   = "25fltp-emr-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port = 0
    to_port   = 65535
    protocol  = "tcp"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── 3. STORAGE (S3) ────────────────────────────────────────────────────────
resource "aws_s3_bucket" "main" {
  bucket        = "25fltp-ecom-chatbot"
  force_destroy = true
}

# ── 4. IAM ROLES ───────────────────────────────────────────────────────────
resource "aws_iam_role" "emr_service_role" {
  name = "25fltp_emr_service_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "elasticmapreduce.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "emr_service" {
  role       = aws_iam_role.emr_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
}

resource "aws_iam_role" "emr_ec2_role" {
  name = "25fltp_emr_ec2_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "emr_ec2" {
  role       = aws_iam_role.emr_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
}

resource "aws_iam_instance_profile" "emr_profile" {
  name = "25fltp_emr_profile"
  role = aws_iam_role.emr_ec2_role.name
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "25fltp_ec2_profile"
  role = aws_iam_role.emr_ec2_role.name
}

# ── 5. OUTPUTS ─────────────────────────────────────────────────────────────
output "vpc_id" { value = aws_vpc.main.id }
output "subnet_id" { value = aws_subnet.public.id }
output "emr_sg_id" { value = aws_security_group.emr_sg.id }
output "ec2_sg_id" { value = aws_security_group.ec2_sg.id }
output "s3_bucket" { value = aws_s3_bucket.main.bucket }
