# terraform/outputs.tf
# Terraform Output Values

output "vpc_id" {
  description = "ID of the VPC created"
  value       = aws_vpc.main.id
}

output "ec2_instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.chatbot.id
}

output "security_group_id" {
  description = "Security Group ID"
  value       = aws_security_group.chatbot.id
}

output "iam_role_arn" {
  description = "IAM Role ARN for EC2"
  value       = aws_iam_role.ec2_s3_access.arn
}
