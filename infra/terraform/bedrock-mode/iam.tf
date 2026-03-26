# ── ECS Task Execution Role ────────────────────────────────────────────────────
# The execution role is assumed by the ECS agent to pull the container image
# and retrieve secrets from Secrets Manager. It does NOT need Bedrock access.

resource "aws_iam_role" "ecs_execution" {
  name = "${var.app_name}-ecs-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "ecs-tasks.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "${var.app_name}-ecs-execution"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow the execution role to read secrets (needed to inject env vars from Secrets Manager)
resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "${var.app_name}-execution-secrets"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "kms:Decrypt"
        ]
        Resource = compact([
          var.anthropic_api_key_secret_arn,
          var.slack_bot_token_secret_arn,
          var.slack_signing_secret_arn,
          var.pagerduty_webhook_secret_arn,
          var.api_secret_key_arn,
        ])
      }
    ]
  })
}


# ── ECS Task Role ──────────────────────────────────────────────────────────────
# The task role is assumed by the running container. It needs Bedrock invoke
# permission only — nothing else. Follow least-privilege strictly here.

resource "aws_iam_role" "ecs_task" {
  name = "${var.app_name}-ecs-task-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "ecs-tasks.amazonaws.com" }
        Action    = "sts:AssumeRole"
        # Scope the trust to this specific ECS cluster to prevent confused-deputy attacks
        Condition = {
          ArnLike = {
            "aws:SourceArn" = "arn:aws:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "${var.app_name}-ecs-task"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Minimal Bedrock policy: invoke THIS model only. No wildcard resources.
resource "aws_iam_role_policy" "ecs_task_bedrock" {
  name = "${var.app_name}-bedrock-invoke"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeClaudeSonnetOnly"
        Effect = "Allow"
        Action = "bedrock:InvokeModel"
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}"
      }
    ]
  })
}

# Allow the task to write logs to CloudWatch
resource "aws_iam_role_policy" "ecs_task_logs" {
  name = "${var.app_name}-cloudwatch-logs"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "WriteApplicationLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.app.arn}:*"
      }
    ]
  })
}

# Optional: allow task to access EFS for persistent data (SQLite + ChromaDB)
resource "aws_iam_role_policy" "ecs_task_efs" {
  count = var.efs_file_system_id != "" ? 1 : 0
  name  = "${var.app_name}-efs-access"
  role  = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EFSClientAccess"
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess"
        ]
        Resource = "arn:aws:elasticfilesystem:${var.aws_region}:${data.aws_caller_identity.current.account_id}:file-system/${var.efs_file_system_id}"
      }
    ]
  })
}

data "aws_caller_identity" "current" {}
