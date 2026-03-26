terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.app_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── CloudWatch Log Group ───────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.app_name}/${var.environment}"
  retention_in_days = var.log_retention_days
}

# ── ECS Cluster ────────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}

# ── Security Group ─────────────────────────────────────────────────────────────
# Restrict inbound to port 8000 only. In production, place a load balancer in
# front and restrict this SG to only accept traffic from the ALB SG.

resource "aws_security_group" "ecs_task" {
  name        = "${var.app_name}-ecs-task-${var.environment}"
  description = "SRE Copilot ECS task security group"
  vpc_id      = var.vpc_id

  ingress {
    description = "FastAPI port"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    # In production: restrict to ALB security group instead of 0.0.0.0/0
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound (needed for Bedrock, ECR, CloudWatch, Secrets Manager)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.app_name}-ecs-task-${var.environment}"
  }
}

# ── ECS Task Definition ────────────────────────────────────────────────────────

locals {
  # Build the secrets list dynamically — only include ARNs that are set
  secrets = concat(
    var.anthropic_api_key_secret_arn != "" ? [{
      name      = "ANTHROPIC_API_KEY"
      valueFrom = var.anthropic_api_key_secret_arn
    }] : [],
    var.slack_bot_token_secret_arn != "" ? [{
      name      = "SLACK_BOT_TOKEN"
      valueFrom = var.slack_bot_token_secret_arn
    }] : [],
    var.slack_signing_secret_arn != "" ? [{
      name      = "SLACK_SIGNING_SECRET"
      valueFrom = var.slack_signing_secret_arn
    }] : [],
    var.pagerduty_webhook_secret_arn != "" ? [{
      name      = "PAGERDUTY_WEBHOOK_SECRET"
      valueFrom = var.pagerduty_webhook_secret_arn
    }] : [],
    var.api_secret_key_arn != "" ? [{
      name      = "API_SECRET_KEY"
      valueFrom = var.api_secret_key_arn
    }] : [],
  )

  # EFS volume config — only added when efs_file_system_id is set
  efs_volumes = var.efs_file_system_id != "" ? [
    {
      name = "sre-copilot-data"
      efs_volume_configuration = {
        file_system_id          = var.efs_file_system_id
        root_directory          = "/"
        transit_encryption      = "ENABLED"
        authorization_config    = { iam = "ENABLED" }
      }
    }
  ] : []

  mount_points = var.efs_file_system_id != "" ? [
    { sourceVolume = "sre-copilot-data", containerPath = "/data", readOnly = false }
  ] : []
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.app_name}-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.container_cpu
  memory                   = var.container_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  dynamic "volume" {
    for_each = local.efs_volumes
    content {
      name = volume.value.name
      efs_volume_configuration {
        file_system_id     = volume.value.efs_volume_configuration.file_system_id
        root_directory     = volume.value.efs_volume_configuration.root_directory
        transit_encryption = volume.value.efs_volume_configuration.transit_encryption
        authorization_config {
          iam = volume.value.efs_volume_configuration.authorization_config.iam
        }
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = var.app_name
      image     = var.container_image
      essential = true

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "DEPLOYMENT_MODE", value = "bedrock" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "BEDROCK_MODEL", value = var.bedrock_model_id },
        { name = "APP_ENV", value = "production" },
        { name = "LOG_LEVEL", value = "INFO" },
        { name = "INCIDENTS_CHANNEL", value = var.incidents_channel },
        { name = "DATABASE_URL", value = "/data/sre_copilot.db" },
        { name = "CHROMA_PERSIST_DIR", value = "/data/chroma" },
        { name = "DATA_DIR", value = "/data" },
      ]

      secrets = local.secrets

      mountPoints = local.mount_points

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 20
      }

      # Run as non-root (matches the appuser in the Dockerfile)
      user = "1000"

      readonlyRootFilesystem = false
    }
  ])

  tags = {
    Name = "${var.app_name}-${var.environment}"
  }
}

# ── ECS Service ────────────────────────────────────────────────────────────────

resource "aws_ecs_service" "app" {
  name                               = "${var.app_name}-${var.environment}"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.app.arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  platform_version                   = "LATEST"
  health_check_grace_period_seconds  = 30

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.ecs_task.id]
    assign_public_ip = false
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_controller {
    type = "ECS"
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# ── Outputs ────────────────────────────────────────────────────────────────────

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.app.name
}

output "task_role_arn" {
  description = "ARN of the ECS task IAM role (has Bedrock invoke permission)"
  value       = aws_iam_role.ecs_task.arn
}

output "execution_role_arn" {
  description = "ARN of the ECS execution IAM role"
  value       = aws_iam_role.ecs_execution.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for application logs"
  value       = aws_cloudwatch_log_group.app.name
}
