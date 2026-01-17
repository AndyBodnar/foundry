"""Initial schema for Foundry MLOps Platform

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-01-17

This migration creates the complete database schema for the Foundry MLOps Platform,
including tables for:
- Multi-tenancy (tenants, users, memberships)
- Experiment tracking (experiments, runs, artifacts, metrics)
- Model registry (registered_models, model_versions, stage_transitions)
- Feature store (feature_views, feature_services, materialization_jobs)
- Deployments (deployments, deployment_versions, ab_tests)
- Monitoring (alert_rules, drift_scores)
- Audit (audit_logs)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, ARRAY

# Revision identifiers
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for Foundry MLOps Platform."""

    # =========================================================================
    # EXTENSIONS
    # =========================================================================
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # =========================================================================
    # ENUM TYPES
    # =========================================================================
    op.execute("""
        CREATE TYPE tenant_status AS ENUM ('ACTIVE', 'SUSPENDED', 'DELETED');
    """)

    op.execute("""
        CREATE TYPE membership_role AS ENUM ('OWNER', 'ADMIN', 'MEMBER', 'VIEWER');
    """)

    op.execute("""
        CREATE TYPE run_status AS ENUM (
            'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'KILLED', 'SCHEDULED'
        );
    """)

    op.execute("""
        CREATE TYPE model_stage AS ENUM ('NONE', 'STAGING', 'PRODUCTION', 'ARCHIVED');
    """)

    op.execute("""
        CREATE TYPE deployment_status AS ENUM (
            'PENDING', 'DEPLOYING', 'RUNNING', 'FAILED', 'STOPPED', 'SCALING'
        );
    """)

    op.execute("""
        CREATE TYPE alert_severity AS ENUM ('INFO', 'WARNING', 'ERROR', 'CRITICAL');
    """)

    op.execute("""
        CREATE TYPE alert_condition AS ENUM (
            'GREATER_THAN', 'LESS_THAN', 'EQUALS', 'NOT_EQUALS',
            'GREATER_THAN_OR_EQUALS', 'LESS_THAN_OR_EQUALS'
        );
    """)

    op.execute("""
        CREATE TYPE drift_status AS ENUM ('NO_DRIFT', 'WARNING', 'DRIFT_DETECTED');
    """)

    op.execute("""
        CREATE TYPE materialization_status AS ENUM (
            'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
        );
    """)

    op.execute("""
        CREATE TYPE ab_test_status AS ENUM (
            'DRAFT', 'RUNNING', 'COMPLETED', 'CANCELLED'
        );
    """)

    # =========================================================================
    # TENANTS TABLE
    # =========================================================================
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("status", sa.Enum("ACTIVE", "SUSPENDED", "DELETED",
                                    name="tenant_status", create_type=False),
                  server_default="ACTIVE"),
        sa.Column("settings", JSONB, server_default="{}"),
        sa.Column("quotas", JSONB, server_default="{}"),
        sa.Column("billing_email", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_tenants_slug", "tenants", ["slug"])
    op.create_index("idx_tenants_status", "tenants", ["status"])

    # =========================================================================
    # USERS TABLE
    # =========================================================================
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("is_superuser", sa.Boolean, server_default="false"),
        sa.Column("email_verified", sa.Boolean, server_default="false"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_is_active", "users", ["is_active"])

    # =========================================================================
    # TENANT MEMBERSHIPS TABLE
    # =========================================================================
    op.create_table(
        "tenant_memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Enum("OWNER", "ADMIN", "MEMBER", "VIEWER",
                                  name="membership_role", create_type=False),
                  server_default="MEMBER"),
        sa.Column("invited_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("joined_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
    )
    op.create_index("idx_memberships_tenant_id", "tenant_memberships", ["tenant_id"])
    op.create_index("idx_memberships_user_id", "tenant_memberships", ["user_id"])

    # =========================================================================
    # API KEYS TABLE
    # =========================================================================
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("scopes", ARRAY(sa.String), server_default="{}"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index("idx_api_keys_key_prefix", "api_keys", ["key_prefix"])

    # =========================================================================
    # EXPERIMENTS TABLE
    # =========================================================================
    op.create_table(
        "experiments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("tags", ARRAY(sa.String), server_default="{}"),
        sa.Column("created_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("is_archived", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_experiment_name"),
    )
    op.create_index("idx_experiments_tenant_id", "experiments", ["tenant_id"])
    op.create_index("idx_experiments_name", "experiments", ["name"])
    op.create_index("idx_experiments_tags", "experiments", ["tags"],
                   postgresql_using="gin")

    # =========================================================================
    # RUNS TABLE
    # =========================================================================
    op.create_table(
        "runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("experiment_id", UUID(as_uuid=True),
                  sa.ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("status", sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED",
                                    "KILLED", "SCHEDULED",
                                    name="run_status", create_type=False),
                  server_default="PENDING"),
        sa.Column("parameters", JSONB, server_default="{}"),
        sa.Column("metrics", JSONB, server_default="{}"),
        sa.Column("tags", ARRAY(sa.String), server_default="{}"),
        sa.Column("git_commit", sa.String(40)),
        sa.Column("git_branch", sa.String(255)),
        sa.Column("git_repo_url", sa.String(500)),
        sa.Column("source_name", sa.String(255)),
        sa.Column("source_type", sa.String(50)),
        sa.Column("entry_point", sa.String(255)),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("parent_run_id", UUID(as_uuid=True),
                  sa.ForeignKey("runs.id", ondelete="SET NULL")),
        sa.Column("start_time", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("end_time", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_runs_experiment_id", "runs", ["experiment_id"])
    op.create_index("idx_runs_tenant_id", "runs", ["tenant_id"])
    op.create_index("idx_runs_status", "runs", ["status"])
    op.create_index("idx_runs_start_time", "runs", ["start_time"])

    # =========================================================================
    # ARTIFACTS TABLE
    # =========================================================================
    op.create_table(
        "artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("run_id", UUID(as_uuid=True),
                  sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("path", sa.String(1000), nullable=False),
        sa.Column("artifact_type", sa.String(50)),
        sa.Column("size_bytes", sa.BigInteger),
        sa.Column("checksum", sa.String(64)),
        sa.Column("artifact_metadata", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_artifacts_run_id", "artifacts", ["run_id"])
    op.create_index("idx_artifacts_tenant_id", "artifacts", ["tenant_id"])

    # =========================================================================
    # METRIC HISTORY TABLE
    # =========================================================================
    op.create_table(
        "metric_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("run_id", UUID(as_uuid=True),
                  sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("step", sa.Integer, server_default="0"),
        sa.Column("timestamp", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_metric_history_run_id", "metric_history", ["run_id"])
    op.create_index("idx_metric_history_key", "metric_history", ["key"])
    op.create_index("idx_metric_history_run_key", "metric_history",
                   ["run_id", "key"])

    # =========================================================================
    # REGISTERED MODELS TABLE
    # =========================================================================
    op.create_table(
        "registered_models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("tags", ARRAY(sa.String), server_default="{}"),
        sa.Column("created_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_registered_model_name"),
    )
    op.create_index("idx_registered_models_tenant_id", "registered_models",
                   ["tenant_id"])
    op.create_index("idx_registered_models_name", "registered_models", ["name"])

    # =========================================================================
    # MODEL VERSIONS TABLE
    # =========================================================================
    op.create_table(
        "model_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("model_id", UUID(as_uuid=True),
                  sa.ForeignKey("registered_models.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("stage", sa.Enum("NONE", "STAGING", "PRODUCTION", "ARCHIVED",
                                   name="model_stage", create_type=False),
                  server_default="NONE"),
        sa.Column("artifact_path", sa.String(1000), nullable=False),
        sa.Column("run_id", UUID(as_uuid=True),
                  sa.ForeignKey("runs.id", ondelete="SET NULL")),
        sa.Column("metrics", JSONB, server_default="{}"),
        sa.Column("signature", JSONB),
        sa.Column("input_schema", JSONB),
        sa.Column("output_schema", JSONB),
        sa.Column("description", sa.Text),
        sa.Column("created_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("model_id", "version", name="uq_model_version"),
    )
    op.create_index("idx_model_versions_model_id", "model_versions", ["model_id"])
    op.create_index("idx_model_versions_tenant_id", "model_versions", ["tenant_id"])
    op.create_index("idx_model_versions_stage", "model_versions", ["stage"])

    # =========================================================================
    # STAGE TRANSITIONS TABLE
    # =========================================================================
    op.create_table(
        "stage_transitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("model_version_id", UUID(as_uuid=True),
                  sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_stage", sa.Enum("NONE", "STAGING", "PRODUCTION", "ARCHIVED",
                                        name="model_stage", create_type=False)),
        sa.Column("to_stage", sa.Enum("NONE", "STAGING", "PRODUCTION", "ARCHIVED",
                                      name="model_stage", create_type=False),
                  nullable=False),
        sa.Column("comment", sa.Text),
        sa.Column("transitioned_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("transitioned_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_stage_transitions_model_version_id", "stage_transitions",
                   ["model_version_id"])

    # =========================================================================
    # FEATURE VIEWS TABLE
    # =========================================================================
    op.create_table(
        "feature_views",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("entities", ARRAY(sa.String), nullable=False),
        sa.Column("features", JSONB, nullable=False),
        sa.Column("source_config", JSONB, nullable=False),
        sa.Column("online_enabled", sa.Boolean, server_default="true"),
        sa.Column("offline_enabled", sa.Boolean, server_default="true"),
        sa.Column("ttl_seconds", sa.Integer),
        sa.Column("tags", ARRAY(sa.String), server_default="{}"),
        sa.Column("created_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_feature_view_name"),
    )
    op.create_index("idx_feature_views_tenant_id", "feature_views", ["tenant_id"])
    op.create_index("idx_feature_views_name", "feature_views", ["name"])

    # =========================================================================
    # FEATURE SERVICES TABLE
    # =========================================================================
    op.create_table(
        "feature_services",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("feature_view_ids", ARRAY(UUID(as_uuid=True)), nullable=False),
        sa.Column("features_config", JSONB, server_default="{}"),
        sa.Column("tags", ARRAY(sa.String), server_default="{}"),
        sa.Column("created_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_feature_service_name"),
    )
    op.create_index("idx_feature_services_tenant_id", "feature_services",
                   ["tenant_id"])

    # =========================================================================
    # MATERIALIZATION JOBS TABLE
    # =========================================================================
    op.create_table(
        "materialization_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("feature_view_id", UUID(as_uuid=True),
                  sa.ForeignKey("feature_views.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED",
                                    name="materialization_status", create_type=False),
                  server_default="PENDING"),
        sa.Column("start_time", sa.DateTime(timezone=True)),
        sa.Column("end_time", sa.DateTime(timezone=True)),
        sa.Column("records_processed", sa.BigInteger, server_default="0"),
        sa.Column("error_message", sa.Text),
        sa.Column("triggered_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_materialization_jobs_feature_view_id",
                   "materialization_jobs", ["feature_view_id"])
    op.create_index("idx_materialization_jobs_status", "materialization_jobs",
                   ["status"])

    # =========================================================================
    # DEPLOYMENTS TABLE
    # =========================================================================
    op.create_table(
        "deployments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.Enum("PENDING", "DEPLOYING", "RUNNING", "FAILED",
                                    "STOPPED", "SCALING",
                                    name="deployment_status", create_type=False),
                  server_default="PENDING"),
        sa.Column("endpoint_url", sa.String(500)),
        sa.Column("config", JSONB, nullable=False),
        sa.Column("traffic_config", JSONB, nullable=False),
        sa.Column("scaling_config", JSONB, server_default="{}"),
        sa.Column("resource_config", JSONB, server_default="{}"),
        sa.Column("health_check_config", JSONB, server_default="{}"),
        sa.Column("created_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_deployment_name"),
    )
    op.create_index("idx_deployments_tenant_id", "deployments", ["tenant_id"])
    op.create_index("idx_deployments_status", "deployments", ["status"])

    # =========================================================================
    # DEPLOYMENT VERSIONS TABLE
    # =========================================================================
    op.create_table(
        "deployment_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("deployment_id", UUID(as_uuid=True),
                  sa.ForeignKey("deployments.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("model_version_id", UUID(as_uuid=True),
                  sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("traffic_percentage", sa.Integer, nullable=False),
        sa.Column("is_primary", sa.Boolean, server_default="false"),
        sa.Column("status", sa.Enum("PENDING", "DEPLOYING", "RUNNING", "FAILED",
                                    "STOPPED", "SCALING",
                                    name="deployment_status", create_type=False),
                  server_default="PENDING"),
        sa.Column("replicas", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_deployment_versions_deployment_id", "deployment_versions",
                   ["deployment_id"])
    op.create_index("idx_deployment_versions_model_version_id",
                   "deployment_versions", ["model_version_id"])

    # =========================================================================
    # AB TESTS TABLE
    # =========================================================================
    op.create_table(
        "ab_tests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("deployment_id", UUID(as_uuid=True),
                  sa.ForeignKey("deployments.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.Enum("DRAFT", "RUNNING", "COMPLETED", "CANCELLED",
                                    name="ab_test_status", create_type=False),
                  server_default="DRAFT"),
        sa.Column("control_version_id", UUID(as_uuid=True),
                  sa.ForeignKey("model_versions.id", ondelete="SET NULL")),
        sa.Column("treatment_version_id", UUID(as_uuid=True),
                  sa.ForeignKey("model_versions.id", ondelete="SET NULL")),
        sa.Column("control_traffic_pct", sa.Integer, server_default="50"),
        sa.Column("treatment_traffic_pct", sa.Integer, server_default="50"),
        sa.Column("success_metric", sa.String(255)),
        sa.Column("minimum_sample_size", sa.Integer),
        sa.Column("confidence_level", sa.Float, server_default="0.95"),
        sa.Column("start_time", sa.DateTime(timezone=True)),
        sa.Column("end_time", sa.DateTime(timezone=True)),
        sa.Column("winner_version_id", UUID(as_uuid=True),
                  sa.ForeignKey("model_versions.id", ondelete="SET NULL")),
        sa.Column("results", JSONB, server_default="{}"),
        sa.Column("created_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_ab_tests_deployment_id", "ab_tests", ["deployment_id"])
    op.create_index("idx_ab_tests_status", "ab_tests", ["status"])

    # =========================================================================
    # ALERT RULES TABLE
    # =========================================================================
    op.create_table(
        "alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deployment_id", UUID(as_uuid=True),
                  sa.ForeignKey("deployments.id", ondelete="CASCADE")),
        sa.Column("model_version_id", UUID(as_uuid=True),
                  sa.ForeignKey("model_versions.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("metric", sa.String(255), nullable=False),
        sa.Column("condition", sa.Enum("GREATER_THAN", "LESS_THAN", "EQUALS",
                                       "NOT_EQUALS", "GREATER_THAN_OR_EQUALS",
                                       "LESS_THAN_OR_EQUALS",
                                       name="alert_condition", create_type=False),
                  nullable=False),
        sa.Column("threshold", sa.Float, nullable=False),
        sa.Column("severity", sa.Enum("INFO", "WARNING", "ERROR", "CRITICAL",
                                      name="alert_severity", create_type=False),
                  server_default="WARNING"),
        sa.Column("evaluation_window_seconds", sa.Integer, server_default="300"),
        sa.Column("cooldown_seconds", sa.Integer, server_default="300"),
        sa.Column("notification_channels", JSONB, server_default="[]"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_alert_rules_tenant_id", "alert_rules", ["tenant_id"])
    op.create_index("idx_alert_rules_deployment_id", "alert_rules", ["deployment_id"])
    op.create_index("idx_alert_rules_enabled", "alert_rules", ["enabled"])

    # =========================================================================
    # ALERT HISTORY TABLE
    # =========================================================================
    op.create_table(
        "alert_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("alert_rule_id", UUID(as_uuid=True),
                  sa.ForeignKey("alert_rules.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("triggered_value", sa.Float, nullable=False),
        sa.Column("threshold_value", sa.Float, nullable=False),
        sa.Column("severity", sa.Enum("INFO", "WARNING", "ERROR", "CRITICAL",
                                      name="alert_severity", create_type=False)),
        sa.Column("message", sa.Text),
        sa.Column("acknowledged_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("triggered_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_alert_history_alert_rule_id", "alert_history",
                   ["alert_rule_id"])
    op.create_index("idx_alert_history_triggered_at", "alert_history",
                   ["triggered_at"])

    # =========================================================================
    # DRIFT SCORES TABLE
    # =========================================================================
    op.create_table(
        "drift_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("deployment_id", UUID(as_uuid=True),
                  sa.ForeignKey("deployments.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_name", sa.String(255)),
        sa.Column("drift_score", sa.Float, nullable=False),
        sa.Column("drift_method", sa.String(50)),
        sa.Column("status", sa.Enum("NO_DRIFT", "WARNING", "DRIFT_DETECTED",
                                    name="drift_status", create_type=False),
                  server_default="NO_DRIFT"),
        sa.Column("baseline_stats", JSONB, server_default="{}"),
        sa.Column("current_stats", JSONB, server_default="{}"),
        sa.Column("calculated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_drift_scores_deployment_id", "drift_scores",
                   ["deployment_id"])
    op.create_index("idx_drift_scores_calculated_at", "drift_scores",
                   ["calculated_at"])
    op.create_index("idx_drift_scores_status", "drift_scores", ["status"])

    # =========================================================================
    # AUDIT LOGS TABLE
    # =========================================================================
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="SET NULL")),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100)),
        sa.Column("resource_id", UUID(as_uuid=True)),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("details", JSONB, server_default="{}"),
        sa.Column("ip_address", INET),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("request_id", UUID(as_uuid=True)),
        sa.Column("timestamp", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("idx_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("idx_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("idx_audit_logs_resource", "audit_logs",
                   ["resource_type", "resource_id"])

    # =========================================================================
    # PIPELINES TABLE
    # =========================================================================
    op.create_table(
        "pipelines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("dag_definition", JSONB, nullable=False),
        sa.Column("schedule", sa.String(100)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("tags", ARRAY(sa.String), server_default="{}"),
        sa.Column("created_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_pipeline_name"),
    )
    op.create_index("idx_pipelines_tenant_id", "pipelines", ["tenant_id"])

    # =========================================================================
    # PIPELINE RUNS TABLE
    # =========================================================================
    op.create_table(
        "pipeline_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("pipeline_id", UUID(as_uuid=True),
                  sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED",
                                    "KILLED", "SCHEDULED",
                                    name="run_status", create_type=False),
                  server_default="PENDING"),
        sa.Column("trigger_type", sa.String(50)),
        sa.Column("parameters", JSONB, server_default="{}"),
        sa.Column("start_time", sa.DateTime(timezone=True)),
        sa.Column("end_time", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("triggered_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()")),
    )
    op.create_index("idx_pipeline_runs_pipeline_id", "pipeline_runs", ["pipeline_id"])
    op.create_index("idx_pipeline_runs_status", "pipeline_runs", ["status"])

    # =========================================================================
    # UPDATE TRIGGERS
    # =========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Apply update trigger to tables with updated_at
    tables_with_updated_at = [
        "tenants", "users", "experiments", "registered_models",
        "model_versions", "feature_views", "feature_services",
        "deployments", "deployment_versions", "ab_tests",
        "alert_rules", "pipelines"
    ]

    for table in tables_with_updated_at:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    """Drop all tables and types."""

    # Drop triggers first
    tables_with_updated_at = [
        "tenants", "users", "experiments", "registered_models",
        "model_versions", "feature_views", "feature_services",
        "deployments", "deployment_versions", "ab_tests",
        "alert_rules", "pipelines"
    ]

    for table in tables_with_updated_at:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")

    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop tables in reverse dependency order
    op.drop_table("pipeline_runs")
    op.drop_table("pipelines")
    op.drop_table("audit_logs")
    op.drop_table("drift_scores")
    op.drop_table("alert_history")
    op.drop_table("alert_rules")
    op.drop_table("ab_tests")
    op.drop_table("deployment_versions")
    op.drop_table("deployments")
    op.drop_table("materialization_jobs")
    op.drop_table("feature_services")
    op.drop_table("feature_views")
    op.drop_table("stage_transitions")
    op.drop_table("model_versions")
    op.drop_table("registered_models")
    op.drop_table("metric_history")
    op.drop_table("artifacts")
    op.drop_table("runs")
    op.drop_table("experiments")
    op.drop_table("api_keys")
    op.drop_table("tenant_memberships")
    op.drop_table("users")
    op.drop_table("tenants")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS ab_test_status;")
    op.execute("DROP TYPE IF EXISTS materialization_status;")
    op.execute("DROP TYPE IF EXISTS drift_status;")
    op.execute("DROP TYPE IF EXISTS alert_condition;")
    op.execute("DROP TYPE IF EXISTS alert_severity;")
    op.execute("DROP TYPE IF EXISTS deployment_status;")
    op.execute("DROP TYPE IF EXISTS model_stage;")
    op.execute("DROP TYPE IF EXISTS run_status;")
    op.execute("DROP TYPE IF EXISTS membership_role;")
    op.execute("DROP TYPE IF EXISTS tenant_status;")
