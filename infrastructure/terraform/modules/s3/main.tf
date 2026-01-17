# Foundry MLOps Platform - S3 Terraform Module
# ==============================================
# This module creates S3 buckets for artifacts, models, and features
# with encryption, versioning, lifecycle policies, and replication.

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
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

variable "account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "enable_versioning" {
  description = "Enable versioning for all buckets"
  type        = bool
  default     = true
}

variable "enable_replication" {
  description = "Enable cross-region replication"
  type        = bool
  default     = false
}

variable "replication_region" {
  description = "Region for replication destination"
  type        = string
  default     = "us-east-1"
}

variable "artifacts_lifecycle_days" {
  description = "Days before transitioning artifacts to IA storage"
  type        = number
  default     = 30
}

variable "artifacts_expiration_days" {
  description = "Days before expiring old artifact versions"
  type        = number
  default     = 365
}

variable "models_lifecycle_days" {
  description = "Days before transitioning old model versions to IA storage"
  type        = number
  default     = 90
}

variable "force_destroy" {
  description = "Allow bucket destruction even if not empty (use with caution)"
  type        = bool
  default     = false
}

variable "block_public_access" {
  description = "Block all public access to buckets"
  type        = bool
  default     = true
}

variable "allowed_vpce_ids" {
  description = "List of VPC Endpoint IDs allowed to access the buckets"
  type        = list(string)
  default     = []
}

variable "allowed_iam_arns" {
  description = "List of IAM ARNs allowed to access the buckets"
  type        = list(string)
  default     = []
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

  bucket_names = {
    artifacts = "${local.name}-artifacts-${var.account_id}"
    models    = "${local.name}-models-${var.account_id}"
    features  = "${local.name}-features-${var.account_id}"
    datasets  = "${local.name}-datasets-${var.account_id}"
  }

  common_tags = merge(
    var.tags,
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Service     = "s3"
    }
  )
}

# ==================================================
# KMS Key for Encryption
# ==================================================

resource "aws_kms_key" "s3" {
  description             = "KMS key for ${local.name} S3 bucket encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow S3 Service"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name}-s3-kms"
    }
  )
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${local.name}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

# ==================================================
# Artifacts Bucket
# ==================================================

resource "aws_s3_bucket" "artifacts" {
  bucket        = local.bucket_names.artifacts
  force_destroy = var.force_destroy

  tags = merge(
    local.common_tags,
    {
      Name    = local.bucket_names.artifacts
      Purpose = "artifacts"
    }
  )
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = var.block_public_access
  block_public_policy     = var.block_public_access
  ignore_public_acls      = var.block_public_access
  restrict_public_buckets = var.block_public_access
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = var.artifacts_lifecycle_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.artifacts_lifecycle_days * 3
      storage_class = "GLACIER"
    }
  }

  rule {
    id     = "expire-old-versions"
    status = var.enable_versioning ? "Enabled" : "Disabled"

    noncurrent_version_expiration {
      noncurrent_days = var.artifacts_expiration_days
    }

    noncurrent_version_transition {
      noncurrent_days = var.artifacts_lifecycle_days
      storage_class   = "STANDARD_IA"
    }
  }

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  rule {
    id     = "expire-delete-markers"
    status = var.enable_versioning ? "Enabled" : "Disabled"

    expiration {
      expired_object_delete_marker = true
    }
  }
}

resource "aws_s3_bucket_logging" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "artifacts/"
}

# ==================================================
# Models Bucket
# ==================================================

resource "aws_s3_bucket" "models" {
  bucket        = local.bucket_names.models
  force_destroy = var.force_destroy

  tags = merge(
    local.common_tags,
    {
      Name    = local.bucket_names.models
      Purpose = "models"
    }
  )
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id

  versioning_configuration {
    status = "Enabled"  # Always enabled for model artifacts
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "models" {
  bucket = aws_s3_bucket.models.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    id     = "transition-old-versions"
    status = "Enabled"

    noncurrent_version_transition {
      noncurrent_days = var.models_lifecycle_days
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_transition {
      noncurrent_days = var.models_lifecycle_days * 2
      storage_class   = "GLACIER"
    }
  }

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_logging" "models" {
  bucket = aws_s3_bucket.models.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "models/"
}

# ==================================================
# Features Bucket
# ==================================================

resource "aws_s3_bucket" "features" {
  bucket        = local.bucket_names.features
  force_destroy = var.force_destroy

  tags = merge(
    local.common_tags,
    {
      Name    = local.bucket_names.features
      Purpose = "features"
    }
  )
}

resource "aws_s3_bucket_versioning" "features" {
  bucket = aws_s3_bucket.features.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "features" {
  bucket = aws_s3_bucket.features.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "features" {
  bucket = aws_s3_bucket.features.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "features" {
  bucket = aws_s3_bucket.features.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 60
      storage_class = "STANDARD_IA"
    }
  }

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_logging" "features" {
  bucket = aws_s3_bucket.features.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "features/"
}

# ==================================================
# Datasets Bucket
# ==================================================

resource "aws_s3_bucket" "datasets" {
  bucket        = local.bucket_names.datasets
  force_destroy = var.force_destroy

  tags = merge(
    local.common_tags,
    {
      Name    = local.bucket_names.datasets
      Purpose = "datasets"
    }
  )
}

resource "aws_s3_bucket_versioning" "datasets" {
  bucket = aws_s3_bucket.datasets.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "datasets" {
  bucket = aws_s3_bucket.datasets.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "datasets" {
  bucket = aws_s3_bucket.datasets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "datasets" {
  bucket = aws_s3_bucket.datasets.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_logging" "datasets" {
  bucket = aws_s3_bucket.datasets.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "datasets/"
}

# ==================================================
# Logs Bucket
# ==================================================

resource "aws_s3_bucket" "logs" {
  bucket        = "${local.name}-s3-logs-${var.account_id}"
  force_destroy = var.force_destroy

  tags = merge(
    local.common_tags,
    {
      Name    = "${local.name}-s3-logs-${var.account_id}"
      Purpose = "logs"
    }
  )
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    expiration {
      days = 90
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }
}

resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ServerAccessLogsPolicy"
        Effect = "Allow"
        Principal = {
          Service = "logging.s3.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.logs.arn}/*"
        Condition = {
          ArnLike = {
            "aws:SourceArn" = [
              aws_s3_bucket.artifacts.arn,
              aws_s3_bucket.models.arn,
              aws_s3_bucket.features.arn,
              aws_s3_bucket.datasets.arn
            ]
          }
          StringEquals = {
            "aws:SourceAccount" = var.account_id
          }
        }
      }
    ]
  })
}

# ==================================================
# CORS Configuration (for direct uploads)
# ==================================================

resource "aws_s3_bucket_cors_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "HEAD"]
    allowed_origins = ["https://*.${var.project_name}.com"]
    expose_headers  = ["ETag", "x-amz-meta-*"]
    max_age_seconds = 3600
  }
}

# ==================================================
# Bucket Policies
# ==================================================

resource "aws_s3_bucket_policy" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid       = "EnforceHTTPS"
          Effect    = "Deny"
          Principal = "*"
          Action    = "s3:*"
          Resource = [
            aws_s3_bucket.artifacts.arn,
            "${aws_s3_bucket.artifacts.arn}/*"
          ]
          Condition = {
            Bool = {
              "aws:SecureTransport" = "false"
            }
          }
        }
      ],
      length(var.allowed_vpce_ids) > 0 ? [
        {
          Sid       = "VPCEndpointAccess"
          Effect    = "Deny"
          Principal = "*"
          Action    = "s3:*"
          Resource = [
            aws_s3_bucket.artifacts.arn,
            "${aws_s3_bucket.artifacts.arn}/*"
          ]
          Condition = {
            StringNotEquals = {
              "aws:sourceVpce" = var.allowed_vpce_ids
            }
          }
        }
      ] : []
    )
  })
}

# ==================================================
# Intelligent Tiering Configuration
# ==================================================

resource "aws_s3_bucket_intelligent_tiering_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  name   = "EntireBucket"

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }
}

# ==================================================
# Outputs
# ==================================================

output "artifacts_bucket_name" {
  description = "Name of the artifacts bucket"
  value       = aws_s3_bucket.artifacts.id
}

output "artifacts_bucket_arn" {
  description = "ARN of the artifacts bucket"
  value       = aws_s3_bucket.artifacts.arn
}

output "models_bucket_name" {
  description = "Name of the models bucket"
  value       = aws_s3_bucket.models.id
}

output "models_bucket_arn" {
  description = "ARN of the models bucket"
  value       = aws_s3_bucket.models.arn
}

output "features_bucket_name" {
  description = "Name of the features bucket"
  value       = aws_s3_bucket.features.id
}

output "features_bucket_arn" {
  description = "ARN of the features bucket"
  value       = aws_s3_bucket.features.arn
}

output "datasets_bucket_name" {
  description = "Name of the datasets bucket"
  value       = aws_s3_bucket.datasets.id
}

output "datasets_bucket_arn" {
  description = "ARN of the datasets bucket"
  value       = aws_s3_bucket.datasets.arn
}

output "logs_bucket_name" {
  description = "Name of the logs bucket"
  value       = aws_s3_bucket.logs.id
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for encryption"
  value       = aws_kms_key.s3.arn
}

output "kms_key_id" {
  description = "ID of the KMS key used for encryption"
  value       = aws_kms_key.s3.id
}
