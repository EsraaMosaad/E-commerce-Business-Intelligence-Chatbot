# terraform/provider.tf
# Terraform and AWS Provider Configuration

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "<NETID>-terraform-state"
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
      Owner       = "CISC886-Team"
    }
  }
}
