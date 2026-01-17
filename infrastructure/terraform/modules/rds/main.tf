# Foundry MLOps Platform - RDS PostgreSQL Terraform Module
# ===========================================================
# This module creates a production-ready PostgreSQL RDS instance
# with Multi-AZ, encryption, automated backups, and monitoring.

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
  description = "VPC ID where RDS will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the DB subnet group"
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "List of security group IDs allowed to connect to RDS"
  type        = list(string)
  default     = []
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to connect to RDS"
  type        = list(string)
  default     = []
}

variable "database_name" {
  description = "Name of the initial database"
  type        = string
  default     = "foundry"
}

variable "master_username" {
  description = "Master username for the database"
  type        = string
  default     = "foundry_admin"
  sensitive   = true
}

variable "master_password" {
  description = "Master password for the database (if not provided, one will be generated)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.1"
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 100
}

variable "max_allocated_storage" {
  description = "Maximum allocated storage in GB for autoscaling"
  type        = number
  default     = 1000
}

variable "storage_type" {
  description = "Storage type (gp3, io1, io2)"
  type        = string
  default     = "gp3"
}

variable "iops" {
  description = "Provisioned IOPS (for io1/io2 storage)"
  type        = number
  default     = 3000
}

variable "storage_throughput" {
  description = "Storage throughput in MiBps (for gp3)"
  type        = number
  default     = 125
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = true
}

variable "backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  default     = 30
}

variable "backup_window" {
  description = "Preferred backup window"
  type        = string
  default     = "03:00-04:00"
}

variable "maintenance_window" {
  description = "Preferred maintenance window"
  type        = string
  default     = "Sun:04:00-Sun:05:00"
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on deletion"
  type        = bool
  default     = false
}

variable "performance_insights_enabled" {
  description = "Enable Performance Insights"
  type        = bool
  default     = true
}

variable "performance_insights_retention_period" {
  description = "Performance Insights retention period in days"
  type        = number
  default     = 7
}

variable "monitoring_interval" {
  description = "Enhanced monitoring interval in seconds (0 to disable)"
  type        = number
  default     = 60
}

variable "create_read_replica" {
  description = "Create a read replica"
  type        = bool
  default     = false
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
      Service     = "rds"
    }
  )
}

# ==================================================
# Random Password (if not provided)
# ==================================================

resource "random_password" "master" {
  count = var.master_password == "" ? 1 : 0

  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# ==================================================
# DB Subnet Group
# ==================================================

resource "aws_db_subnet_group" "main" {
  name        = "${local.name}-db-subnet-group"
  description = "Database subnet group for ${local.name}"
  subnet_ids  = var.subnet_ids

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-db-subnet-group"
    }
  )
}

# ==================================================
# Security Group
# ==================================================

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds-sg"
  description = "Security group for ${local.name} RDS"
  vpc_id      = var.vpc_id

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-rds-sg"
    }
  )
}

resource "aws_security_group_rule" "rds_ingress_sg" {
  count = length(var.allowed_security_group_ids)

  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = var.allowed_security_group_ids[count.index]
  security_group_id        = aws_security_group.rds.id
  description              = "Allow PostgreSQL from security group"
}

resource "aws_security_group_rule" "rds_ingress_cidr" {
  count = length(var.allowed_cidr_blocks) > 0 ? 1 : 0

  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = var.allowed_cidr_blocks
  security_group_id = aws_security_group.rds.id
  description       = "Allow PostgreSQL from CIDR blocks"
}

resource "aws_security_group_rule" "rds_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.rds.id
  description       = "Allow all outbound traffic"
}

# ==================================================
# Parameter Group
# ==================================================

resource "aws_db_parameter_group" "main" {
  name        = "${local.name}-pg16-params"
  family      = "postgres16"
  description = "Parameter group for ${local.name} PostgreSQL 16"

  # Performance parameters
  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/4096}"
  }

  parameter {
    name  = "effective_cache_size"
    value = "{DBInstanceClassMemory*3/4096}"
  }

  parameter {
    name  = "maintenance_work_mem"
    value = "1048576"  # 1GB
  }

  parameter {
    name  = "work_mem"
    value = "65536"  # 64MB
  }

  # WAL settings
  parameter {
    name  = "wal_buffers"
    value = "65536"  # 64MB
  }

  parameter {
    name  = "checkpoint_completion_target"
    value = "0.9"
  }

  # Query planning
  parameter {
    name  = "random_page_cost"
    value = "1.1"
  }

  parameter {
    name  = "effective_io_concurrency"
    value = "200"
  }

  # Logging
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries > 1 second
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  # Extensions
  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements,pgaudit"
  }

  parameter {
    name  = "pg_stat_statements.track"
    value = "all"
  }

  tags = local.common_tags

  lifecycle {
    create_before_destroy = true
  }
}

# ==================================================
# KMS Key for Encryption
# ==================================================

resource "aws_kms_key" "rds" {
  description             = "KMS key for ${local.name} RDS encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-rds-kms"
    }
  )
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${local.name}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

# ==================================================
# IAM Role for Enhanced Monitoring
# ==================================================

resource "aws_iam_role" "rds_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0

  name = "${local.name}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0

  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ==================================================
# RDS Instance
# ==================================================

resource "aws_db_instance" "main" {
  identifier = "${local.name}-postgres"

  # Engine
  engine               = "postgres"
  engine_version       = var.engine_version
  instance_class       = var.instance_class
  parameter_group_name = aws_db_parameter_group.main.name

  # Storage
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = var.storage_type
  iops                  = var.storage_type == "gp3" || var.storage_type == "io1" || var.storage_type == "io2" ? var.iops : null
  storage_throughput    = var.storage_type == "gp3" ? var.storage_throughput : null
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.rds.arn

  # Database
  db_name  = var.database_name
  username = var.master_username
  password = var.master_password != "" ? var.master_password : random_password.master[0].result
  port     = 5432

  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = var.multi_az

  # Backup
  backup_retention_period = var.backup_retention_period
  backup_window           = var.backup_window
  copy_tags_to_snapshot   = true
  delete_automated_backups = false

  # Maintenance
  maintenance_window        = var.maintenance_window
  auto_minor_version_upgrade = true
  apply_immediately         = false

  # Protection
  deletion_protection = var.deletion_protection
  skip_final_snapshot = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${local.name}-final-snapshot"

  # Monitoring
  performance_insights_enabled          = var.performance_insights_enabled
  performance_insights_retention_period = var.performance_insights_retention_period
  performance_insights_kms_key_id       = aws_kms_key.rds.arn
  monitoring_interval                   = var.monitoring_interval
  monitoring_role_arn                   = var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null
  enabled_cloudwatch_logs_exports       = ["postgresql", "upgrade"]

  # IAM Auth
  iam_database_authentication_enabled = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-postgres"
    }
  )

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      password
    ]
  }
}

# ==================================================
# Read Replica (Optional)
# ==================================================

resource "aws_db_instance" "replica" {
  count = var.create_read_replica ? 1 : 0

  identifier = "${local.name}-postgres-replica"

  # Replica settings
  replicate_source_db = aws_db_instance.main.identifier
  instance_class      = var.instance_class

  # Storage
  storage_type       = var.storage_type
  iops               = var.storage_type == "gp3" || var.storage_type == "io1" || var.storage_type == "io2" ? var.iops : null
  storage_throughput = var.storage_type == "gp3" ? var.storage_throughput : null
  storage_encrypted  = true
  kms_key_id         = aws_kms_key.rds.arn

  # Network
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = false

  # Maintenance
  auto_minor_version_upgrade = true
  apply_immediately          = false

  # Monitoring
  performance_insights_enabled          = var.performance_insights_enabled
  performance_insights_retention_period = var.performance_insights_retention_period
  performance_insights_kms_key_id       = aws_kms_key.rds.arn
  monitoring_interval                   = var.monitoring_interval
  monitoring_role_arn                   = var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-postgres-replica"
    }
  )

  depends_on = [aws_db_instance.main]
}

# ==================================================
# Secrets Manager
# ==================================================

resource "aws_secretsmanager_secret" "rds" {
  name        = "${local.name}/rds/credentials"
  description = "RDS credentials for ${local.name}"
  kms_key_id  = aws_kms_key.rds.arn

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "rds" {
  secret_id = aws_secretsmanager_secret.rds.id

  secret_string = jsonencode({
    username = var.master_username
    password = var.master_password != "" ? var.master_password : random_password.master[0].result
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    database = var.database_name
    engine   = "postgres"
  })
}

# ==================================================
# CloudWatch Alarms
# ==================================================

resource "aws_cloudwatch_metric_alarm" "cpu" {
  alarm_name          = "${local.name}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization is high"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "storage" {
  alarm_name          = "${local.name}-rds-storage-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 10737418240  # 10GB in bytes
  alarm_description   = "RDS free storage space is low"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "connections" {
  alarm_name          = "${local.name}-rds-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 500
  alarm_description   = "RDS database connections are high"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }

  tags = local.common_tags
}

# ==================================================
# Outputs
# ==================================================

output "db_instance_id" {
  description = "The RDS instance ID"
  value       = aws_db_instance.main.id
}

output "db_instance_arn" {
  description = "The ARN of the RDS instance"
  value       = aws_db_instance.main.arn
}

output "db_instance_endpoint" {
  description = "The connection endpoint"
  value       = aws_db_instance.main.endpoint
}

output "db_instance_address" {
  description = "The hostname of the RDS instance"
  value       = aws_db_instance.main.address
}

output "db_instance_port" {
  description = "The database port"
  value       = aws_db_instance.main.port
}

output "db_name" {
  description = "The database name"
  value       = aws_db_instance.main.db_name
}

output "db_security_group_id" {
  description = "The security group ID"
  value       = aws_security_group.rds.id
}

output "db_secret_arn" {
  description = "The ARN of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.rds.arn
}

output "db_kms_key_arn" {
  description = "The ARN of the KMS key"
  value       = aws_kms_key.rds.arn
}

output "db_replica_endpoint" {
  description = "The read replica connection endpoint"
  value       = var.create_read_replica ? aws_db_instance.replica[0].endpoint : null
}
