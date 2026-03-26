variable "aws_region" {
  description = "AWS region to deploy SRE Copilot and call Bedrock from. Use ap-northeast-1 for APPI compliance."
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Name prefix used for all created AWS resources."
  type        = string
  default     = "sre-copilot"
}

variable "environment" {
  description = "Deployment environment tag (e.g. production, staging)."
  type        = string
  default     = "production"
}

variable "bedrock_model_id" {
  description = "AWS Bedrock model ID to invoke. Must be enabled in your account for the selected region."
  type        = string
  default     = "anthropic.claude-sonnet-4-6-20250514-v1:0"
}

variable "container_image" {
  description = "Docker image URI for the SRE Copilot container (e.g. 123456789012.dkr.ecr.us-east-1.amazonaws.com/sre-copilot:latest)."
  type        = string
}

variable "container_cpu" {
  description = "CPU units allocated to the ECS task (1024 = 1 vCPU)."
  type        = number
  default     = 512
}

variable "container_memory" {
  description = "Memory (MiB) allocated to the ECS task."
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Number of ECS task instances to run."
  type        = number
  default     = 1
}

variable "vpc_id" {
  description = "VPC ID where the ECS service will be deployed."
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the ECS service. Use private subnets with a NAT gateway."
  type        = list(string)
}

variable "anthropic_api_key_secret_arn" {
  description = "ARN of the AWS Secrets Manager secret containing ANTHROPIC_API_KEY (for voyage-3 embeddings). Leave empty to use stub embeddings."
  type        = string
  default     = ""
}

variable "slack_bot_token_secret_arn" {
  description = "ARN of the AWS Secrets Manager secret containing SLACK_BOT_TOKEN."
  type        = string
  default     = ""
}

variable "slack_signing_secret_arn" {
  description = "ARN of the AWS Secrets Manager secret containing SLACK_SIGNING_SECRET."
  type        = string
  default     = ""
}

variable "pagerduty_webhook_secret_arn" {
  description = "ARN of the AWS Secrets Manager secret containing PAGERDUTY_WEBHOOK_SECRET."
  type        = string
  default     = ""
}

variable "api_secret_key_arn" {
  description = "ARN of the AWS Secrets Manager secret containing API_SECRET_KEY."
  type        = string
  default     = ""
}

variable "incidents_channel" {
  description = "Slack channel to post triage messages (e.g. #incidents)."
  type        = string
  default     = "#incidents"
}

variable "efs_file_system_id" {
  description = "EFS file system ID for persistent SQLite and ChromaDB storage. If empty, data is ephemeral (lost on task replacement)."
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "CloudWatch log group retention period in days."
  type        = number
  default     = 30
}
