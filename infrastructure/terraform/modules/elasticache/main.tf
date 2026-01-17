# Foundry MLOps Platform - ElastiCache Redis Terraform Module
# =============================================================
# This module creates a production-ready Redis cluster using ElastiCache
# with cluster mode, encryption, and automatic failover.

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# ==================================================
# Variables
# ==================================================

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "foundry"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where ElastiCache will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the ElastiCache subnet group"
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "List of security group IDs allowed to connect to Redis"
  type        = list(string)
  default     = []
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to connect to Redis"
  type        = list(string)
  default     = []
}

variable "node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.r6g.large"
}

variable "engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.1"
}

variable "num_cache_clusters" {
  description = "Number of cache clusters (nodes) in the replication group"
  type        = number
  default     = 3
}

variable "automatic_failover_enabled" {
  description = "Enable automatic failover"
  type        = bool
  default     = true
}

variable "multi_az_enabled" {
  description = "Enable Multi-AZ"
  type        = bool
  default     = true
}

variable "auth_token" {
  description = "Auth token for Redis (if not provided, one will be generated)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "at_rest_encryption_enabled" {
  description = "Enable at-rest encryption"
  type        = bool
  default     = true
}

variable "transit_encryption_enabled" {
  description = "Enable in-transit encryption"
  type        = bool
  default     = true
}

variable "snapshot_retention_limit" {
  description = "Number of days to retain snapshots"
  type        = number
  default     = 7
}

variable "snapshot_window" {
  description = "Preferred snapshot window"
  type        = string
  default     = "03:00-04:00"
}

variable "maintenance_window" {
  description = "Preferred maintenance window"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "apply_immediately" {
  description = "Apply changes immediately"
  type        = bool
  default     = false
}

variable "notification_topic_arn" {
  description = "SNS topic ARN for notifications"
  type        = string
  default     = ""
}

variable "log_delivery_configuration" {
  description = "Enable slow log and engine log delivery to CloudWatch"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}

# ==================================================
# Local Values
# ==================================================

locals {
  name = "${var.project_name}-${var.environment}"

  common_tags = merge(
    var.tags,
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Service     = "elasticache"
    }
  )
}

# ==================================================
# Random Auth Token (if not provided)
# ==================================================

resource "random_password" "auth_token" {
  count = var.auth_token == "" && var.transit_encryption_enabled ? 1 : 0

  length           = 64
  special          = true
  override_special = "!&#$^<>-"
}

# ==================================================
# Subnet Group
# ==================================================

resource "aws_elasticache_subnet_group" "main" {
  name        = "${local.name}-redis-subnet-group"
  description = "Redis subnet group for ${local.name}"
  subnet_ids  = var.subnet_ids

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-redis-subnet-group"
    }
  )
}

# ==================================================
# Security Group
# ==================================================

resource "aws_security_group" "redis" {
  name        = "${local.name}-redis-sg"
  description = "Security group for ${local.name} Redis"
  vpc_id      = var.vpc_id

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-redis-sg"
    }
  )
}

resource "aws_security_group_rule" "redis_ingress_sg" {
  count = length(var.allowed_security_group_ids)

  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  source_security_group_id = var.allowed_security_group_ids[count.index]
  security_group_id        = aws_security_group.redis.id
  description              = "Allow Redis from security group"
}

resource "aws_security_group_rule" "redis_ingress_cidr" {
  count = length(var.allowed_cidr_blocks) > 0 ? 1 : 0

  type              = "ingress"
  from_port         = 6379
  to_port           = 6379
  protocol          = "tcp"
  cidr_blocks       = var.allowed_cidr_blocks
  security_group_id = aws_security_group.redis.id
  description       = "Allow Redis from CIDR blocks"
}

resource "aws_security_group_rule" "redis_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.redis.id
  description       = "Allow all outbound traffic"
}

# ==================================================
# Parameter Group
# ==================================================

resource "aws_elasticache_parameter_group" "main" {
  name        = "${local.name}-redis7-params"
  family      = "redis7"
  description = "Parameter group for ${local.name} Redis 7"

  # Memory management
  parameter {
    name  = "maxmemory-policy"
    value = "volatile-lru"
  }

  # Append-only file persistence
  parameter {
    name  = "appendonly"
    value = "yes"
  }

  parameter {
    name  = "appendfsync"
    value = "everysec"
  }

  # Slow log
  parameter {
    name  = "slowlog-log-slower-than"
    value = "10000"  # 10ms
  }

  parameter {
    name  = "slowlog-max-len"
    value = "128"
  }

  # Client output buffer limits
  parameter {
    name  = "client-output-buffer-limit-normal-hard-limit"
    value = "0"
  }

  parameter {
    name  = "client-output-buffer-limit-normal-soft-limit"
    value = "0"
  }

  # TCP keepalive
  parameter {
    name  = "tcp-keepalive"
    value = "300"
  }

  # Timeout
  parameter {
    name  = "timeout"
    value = "0"  # Disable timeout
  }

  tags = local.common_tags

  lifecycle {
    create_before_destroy = true
  }
}

# ==================================================
# KMS Key for Encryption
# ==================================================

resource "aws_kms_key" "redis" {
  count = var.at_rest_encryption_enabled ? 1 : 0

  description             = "KMS key for ${local.name} Redis encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-redis-kms"
    }
  )
}

resource "aws_kms_alias" "redis" {
  count = var.at_rest_encryption_enabled ? 1 : 0

  name          = "alias/${local.name}-redis"
  target_key_id = aws_kms_key.redis[0].key_id
}

# ==================================================
# CloudWatch Log Groups
# ==================================================

resource "aws_cloudwatch_log_group" "slow_log" {
  count = var.log_delivery_configuration ? 1 : 0

  name              = "/aws/elasticache/${local.name}/slow-log"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "engine_log" {
  count = var.log_delivery_configuration ? 1 : 0

  name              = "/aws/elasticache/${local.name}/engine-log"
  retention_in_days = 30

  tags = local.common_tags
}

# ==================================================
# Replication Group (Redis Cluster)
# ==================================================

resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${local.name}-redis"
  description          = "Redis cluster for ${local.name}"

  # Engine
  engine               = "redis"
  engine_version       = var.engine_version
  node_type            = var.node_type
  parameter_group_name = aws_elasticache_parameter_group.main.name
  port                 = 6379

  # Cluster configuration
  num_cache_clusters         = var.num_cache_clusters
  automatic_failover_enabled = var.automatic_failover_enabled && var.num_cache_clusters > 1
  multi_az_enabled           = var.multi_az_enabled && var.num_cache_clusters > 1

  # Network
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  # Security
  at_rest_encryption_enabled = var.at_rest_encryption_enabled
  transit_encryption_enabled = var.transit_encryption_enabled
  auth_token                 = var.transit_encryption_enabled ? (var.auth_token != "" ? var.auth_token : random_password.auth_token[0].result) : null
  kms_key_id                 = var.at_rest_encryption_enabled ? aws_kms_key.redis[0].arn : null

  # Backup
  snapshot_retention_limit = var.snapshot_retention_limit
  snapshot_window          = var.snapshot_window

  # Maintenance
  maintenance_window = var.maintenance_window
  apply_immediately  = var.apply_immediately

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  # Notifications
  notification_topic_arn = var.notification_topic_arn != "" ? var.notification_topic_arn : null

  # Log delivery
  dynamic "log_delivery_configuration" {
    for_each = var.log_delivery_configuration ? [1] : []
    content {
      destination      = aws_cloudwatch_log_group.slow_log[0].name
      destination_type = "cloudwatch-logs"
      log_format       = "json"
      log_type         = "slow-log"
    }
  }

  dynamic "log_delivery_configuration" {
    for_each = var.log_delivery_configuration ? [1] : []
    content {
      destination      = aws_cloudwatch_log_group.engine_log[0].name
      destination_type = "cloudwatch-logs"
      log_format       = "json"
      log_type         = "engine-log"
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-redis"
    }
  )

  lifecycle {
    ignore_changes = [
      num_cache_clusters  # Managed by auto-scaling
    ]
  }
}

# ==================================================
# Secrets Manager
# ==================================================

resource "aws_secretsmanager_secret" "redis" {
  name        = "${local.name}/redis/credentials"
  description = "Redis credentials for ${local.name}"
  kms_key_id  = var.at_rest_encryption_enabled ? aws_kms_key.redis[0].arn : null

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "redis" {
  secret_id = aws_secretsmanager_secret.redis.id

  secret_string = jsonencode({
    host       = aws_elasticache_replication_group.main.primary_endpoint_address
    port       = 6379
    auth_token = var.transit_encryption_enabled ? (var.auth_token != "" ? var.auth_token : random_password.auth_token[0].result) : null
    ssl        = var.transit_encryption_enabled
  })
}

# ==================================================
# CloudWatch Alarms
# ==================================================

resource "aws_cloudwatch_metric_alarm" "cpu" {
  alarm_name          = "${local.name}-redis-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "EngineCPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 75
  alarm_description   = "Redis CPU utilization is high"

  dimensions = {
    CacheClusterId = "${local.name}-redis-001"
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "memory" {
  alarm_name          = "${local.name}-redis-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Redis memory usage is high"

  dimensions = {
    CacheClusterId = "${local.name}-redis-001"
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "connections" {
  alarm_name          = "${local.name}-redis-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CurrConnections"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 5000
  alarm_description   = "Redis connections are high"

  dimensions = {
    CacheClusterId = "${local.name}-redis-001"
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "evictions" {
  alarm_name          = "${local.name}-redis-evictions-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Sum"
  threshold           = 1000
  alarm_description   = "Redis evictions are high"

  dimensions = {
    CacheClusterId = "${local.name}-redis-001"
  }

  tags = local.common_tags
}

# ==================================================
# Outputs
# ==================================================

output "replication_group_id" {
  description = "The ID of the ElastiCache replication group"
  value       = aws_elasticache_replication_group.main.id
}

output "replication_group_arn" {
  description = "The ARN of the ElastiCache replication group"
  value       = aws_elasticache_replication_group.main.arn
}

output "primary_endpoint_address" {
  description = "The primary endpoint address"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "reader_endpoint_address" {
  description = "The reader endpoint address"
  value       = aws_elasticache_replication_group.main.reader_endpoint_address
}

output "port" {
  description = "The Redis port"
  value       = 6379
}

output "security_group_id" {
  description = "The security group ID"
  value       = aws_security_group.redis.id
}

output "secret_arn" {
  description = "The ARN of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.redis.arn
}

output "kms_key_arn" {
  description = "The ARN of the KMS key"
  value       = var.at_rest_encryption_enabled ? aws_kms_key.redis[0].arn : null
}

output "configuration_endpoint_address" {
  description = "The configuration endpoint address (for cluster mode)"
  value       = aws_elasticache_replication_group.main.configuration_endpoint_address
}
