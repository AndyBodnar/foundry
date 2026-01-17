"""SQLAlchemy database models for all domain entities."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from foundry.infrastructure.database.base import (
    Base,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


# ============================================================================
# Enums
# ============================================================================


class TenantStatus(str, PyEnum):
    """Tenant account status."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class UserRole(str, PyEnum):
    """User role within a tenant."""

    VIEWER = "VIEWER"
    DATA_SCIENTIST = "DATA_SCIENTIST"
    ML_ENGINEER = "ML_ENGINEER"
    ADMIN = "ADMIN"


class RunStatus(str, PyEnum):
    """Experiment run status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ModelStage(str, PyEnum):
    """Model version stage in the lifecycle."""

    NONE = "NONE"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


class DeploymentStatus(str, PyEnum):
    """Deployment status."""

    PENDING = "PENDING"
    DEPLOYING = "DEPLOYING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    ROLLING_BACK = "ROLLING_BACK"


class AlertSeverity(str, PyEnum):
    """Alert severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertCondition(str, PyEnum):
    """Alert condition operators."""

    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"


class PipelineStatus(str, PyEnum):
    """Pipeline execution status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ABTestStatus(str, PyEnum):
    """A/B test status."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ============================================================================
# Tenant & User Models
# ============================================================================


class Tenant(Base, UUIDMixin, TimestampMixin):
    """Tenant (organization) model."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus),
        default=TenantStatus.ACTIVE,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    quotas: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="tenant_memberships",
        back_populates="tenants",
    )
    memberships: Mapped[list["TenantMembership"]] = relationship(
        "TenantMembership",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )


class User(Base, UUIDMixin, TimestampMixin):
    """User model."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    tenants: Mapped[list["Tenant"]] = relationship(
        "Tenant",
        secondary="tenant_memberships",
        back_populates="users",
    )
    memberships: Mapped[list["TenantMembership"]] = relationship(
        "TenantMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class TenantMembership(Base, UUIDMixin, TimestampMixin):
    """Tenant membership (user-tenant association with role)."""

    __tablename__ = "tenant_memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.VIEWER,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="memberships")


class APIKey(Base, UUIDMixin, TimestampMixin):
    """API key for programmatic access."""

    __tablename__ = "api_keys"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)  # First chars for identification
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")


# ============================================================================
# Experiment Models
# ============================================================================


class Experiment(Base, UUIDMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """Experiment model - logical grouping of runs."""

    __tablename__ = "experiments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_experiment_name"),
        Index("ix_experiments_tenant_name", "tenant_id", "name"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    owner_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    runs: Mapped[list["Run"]] = relationship(
        "Run",
        back_populates="experiment",
        cascade="all, delete-orphan",
    )


class Run(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Experiment run model - single training execution."""

    __tablename__ = "runs"
    __table_args__ = (
        Index("ix_runs_experiment_status", "experiment_id", "status"),
    )

    experiment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus),
        default=RunStatus.PENDING,
        index=True,
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    git_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="runs")
    artifacts: Mapped[list["Artifact"]] = relationship(
        "Artifact",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    metric_history: Mapped[list["MetricHistory"]] = relationship(
        "MetricHistory",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class Artifact(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Artifact model - files produced during a run."""

    __tablename__ = "artifacts"

    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)  # model, dataset, image, etc.
    path: Mapped[str] = mapped_column(Text, nullable=False)  # S3 path
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA256
    artifact_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="artifacts")


class MetricHistory(Base, UUIDMixin, TenantMixin):
    """Metric history model - metric values over steps/epochs."""

    __tablename__ = "metric_history"
    __table_args__ = (
        Index("ix_metric_history_run_key", "run_id", "key"),
    )

    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="metric_history")


# ============================================================================
# Model Registry Models
# ============================================================================


class RegisteredModel(Base, UUIDMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """Registered model - a model with multiple versions."""

    __tablename__ = "registered_models"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_model_name"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    owner_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    versions: Mapped[list["ModelVersion"]] = relationship(
        "ModelVersion",
        back_populates="model",
        cascade="all, delete-orphan",
    )


class ModelVersion(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Model version - specific version with artifact."""

    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("model_id", "version", name="uq_model_version"),
        Index("ix_model_versions_model_stage", "model_id", "stage"),
    )

    model_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("registered_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    stage: Mapped[ModelStage] = mapped_column(
        Enum(ModelStage),
        default=ModelStage.NONE,
        index=True,
    )
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    signature: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # Input/output schema
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    model: Mapped["RegisteredModel"] = relationship("RegisteredModel", back_populates="versions")
    stage_transitions: Mapped[list["StageTransition"]] = relationship(
        "StageTransition",
        back_populates="model_version",
        cascade="all, delete-orphan",
    )


class StageTransition(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Stage transition history for model versions."""

    __tablename__ = "stage_transitions"

    model_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_stage: Mapped[ModelStage] = mapped_column(Enum(ModelStage), nullable=False)
    to_stage: Mapped[ModelStage] = mapped_column(Enum(ModelStage), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    model_version: Mapped["ModelVersion"] = relationship(
        "ModelVersion",
        back_populates="stage_transitions",
    )


# ============================================================================
# Deployment Models
# ============================================================================


class Deployment(Base, UUIDMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """Deployment model - active serving endpoint."""

    __tablename__ = "deployments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_deployment_name"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus),
        default=DeploymentStatus.PENDING,
        index=True,
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    traffic_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    endpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    replicas: Mapped[int] = mapped_column(Integer, default=1)
    min_replicas: Mapped[int] = mapped_column(Integer, default=1)
    max_replicas: Mapped[int] = mapped_column(Integer, default=10)
    owner_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    ab_tests: Mapped[list["ABTest"]] = relationship(
        "ABTest",
        back_populates="deployment",
        cascade="all, delete-orphan",
    )
    alert_rules: Mapped[list["AlertRule"]] = relationship(
        "AlertRule",
        back_populates="deployment",
        cascade="all, delete-orphan",
    )


class ABTest(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """A/B test model - traffic experiment between model versions."""

    __tablename__ = "ab_tests"

    deployment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("deployments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ABTestStatus] = mapped_column(
        Enum(ABTestStatus),
        default=ABTestStatus.RUNNING,
    )
    control_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    treatment_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    control_traffic_percent: Mapped[int] = mapped_column(Integer, default=50)
    treatment_traffic_percent: Mapped[int] = mapped_column(Integer, default=50)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    winner_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Relationships
    deployment: Mapped["Deployment"] = relationship("Deployment", back_populates="ab_tests")


# ============================================================================
# Monitoring Models
# ============================================================================


class AlertRule(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Alert rule model - threshold-based alerting."""

    __tablename__ = "alert_rules"

    deployment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("deployments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric: Mapped[str] = mapped_column(String(255), nullable=False)
    condition: Mapped[AlertCondition] = mapped_column(Enum(AlertCondition), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity),
        default=AlertSeverity.WARNING,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_channels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=15)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    deployment: Mapped["Deployment"] = relationship("Deployment", back_populates="alert_rules")


class Alert(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Alert instance - triggered alert event."""

    __tablename__ = "alerts"

    rule_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deployment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("deployments.id", ondelete="SET NULL"),
        nullable=True,
    )
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================================================
# Pipeline Models
# ============================================================================


class Pipeline(Base, UUIDMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """Pipeline model - DAG definition."""

    __tablename__ = "pipelines"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_pipeline_name"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dag_definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Cron expression
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    runs: Mapped[list["PipelineRun"]] = relationship(
        "PipelineRun",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )


class PipelineRun(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Pipeline run model - single execution of a pipeline."""

    __tablename__ = "pipeline_runs"

    pipeline_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus),
        default=PipelineStatus.PENDING,
        index=True,
    )
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)  # scheduled, manual, trigger
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="runs")
    tasks: Mapped[list["PipelineTask"]] = relationship(
        "PipelineTask",
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
    )


class PipelineTask(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Pipeline task model - individual task within a pipeline run."""

    __tablename__ = "pipeline_tasks"

    pipeline_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus),
        default=PipelineStatus.PENDING,
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    pipeline_run: Mapped["PipelineRun"] = relationship("PipelineRun", back_populates="tasks")


# ============================================================================
# Audit Log Model
# ============================================================================


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Audit log model - tracks all significant events."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_tenant_timestamp", "tenant_id", "timestamp"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )


# ============================================================================
# Feature Store Models (Optional - if using built-in feature store)
# ============================================================================


class FeatureView(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Feature view model - definition of features with source."""

    __tablename__ = "feature_views"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_feature_view_name"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entities: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # Feature definitions
    source_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ttl_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    online_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    offline_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
