"""Pydantic schemas for deployments domain."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from foundry.infrastructure.database.models import DeploymentStatus, ABTestStatus


# ============================================================================
# Deployment Schemas
# ============================================================================


class DeploymentConfig(BaseModel):
    """Deployment configuration."""

    cpu_request: str = Field(default="500m")
    cpu_limit: str = Field(default="2")
    memory_request: str = Field(default="1Gi")
    memory_limit: str = Field(default="4Gi")
    env_vars: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=60, ge=1, le=300)


class TrafficConfig(BaseModel):
    """Traffic routing configuration."""

    model_version_id: UUID
    weight: int = Field(ge=0, le=100)


class DeploymentBase(BaseModel):
    """Base deployment schema."""

    name: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(None, max_length=5000)


class DeploymentCreate(DeploymentBase):
    """Schema for creating a deployment."""

    model_version_id: UUID
    config: DeploymentConfig = Field(default_factory=DeploymentConfig)
    replicas: int = Field(default=1, ge=1, le=100)
    min_replicas: int = Field(default=1, ge=1, le=100)
    max_replicas: int = Field(default=10, ge=1, le=100)

    @field_validator("max_replicas")
    @classmethod
    def validate_max_replicas(cls, v: int, info) -> int:
        """Ensure max_replicas >= min_replicas."""
        if "min_replicas" in info.data and v < info.data["min_replicas"]:
            raise ValueError("max_replicas must be >= min_replicas")
        return v


class DeploymentUpdate(BaseModel):
    """Schema for updating a deployment."""

    description: str | None = None
    config: DeploymentConfig | None = None
    replicas: int | None = Field(None, ge=1, le=100)
    min_replicas: int | None = Field(None, ge=1, le=100)
    max_replicas: int | None = Field(None, ge=1, le=100)


class DeploymentResponse(DeploymentBase):
    """Schema for deployment response."""

    id: UUID
    tenant_id: UUID
    status: DeploymentStatus
    config: dict[str, Any]
    traffic_config: dict[str, Any]
    endpoint_url: str | None
    model_version_id: UUID | None
    replicas: int
    min_replicas: int
    max_replicas: int
    owner_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeploymentListResponse(BaseModel):
    """Schema for paginated deployment list."""

    items: list[DeploymentResponse]
    total: int
    offset: int
    limit: int


class TrafficConfigUpdate(BaseModel):
    """Schema for updating traffic configuration."""

    traffic: list[TrafficConfig]

    @field_validator("traffic")
    @classmethod
    def validate_traffic_weights(cls, v: list[TrafficConfig]) -> list[TrafficConfig]:
        """Ensure traffic weights sum to 100."""
        total_weight = sum(t.weight for t in v)
        if total_weight != 100:
            raise ValueError(f"Traffic weights must sum to 100, got {total_weight}")
        return v


class DeploymentHealthResponse(BaseModel):
    """Schema for deployment health check."""

    deployment_id: UUID
    status: DeploymentStatus
    healthy: bool
    replicas_ready: int
    replicas_desired: int
    last_check: datetime
    error_message: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class RollbackRequest(BaseModel):
    """Schema for rollback request."""

    target_version_id: UUID | None = None  # None = rollback to previous
    reason: str | None = Field(None, max_length=1000)


# ============================================================================
# A/B Test Schemas
# ============================================================================


class ABTestCreate(BaseModel):
    """Schema for creating an A/B test."""

    name: str = Field(..., min_length=1, max_length=255)
    control_version_id: UUID
    treatment_version_id: UUID
    control_traffic_percent: int = Field(default=50, ge=1, le=99)

    @field_validator("control_traffic_percent")
    @classmethod
    def validate_traffic(cls, v: int) -> int:
        """Validate traffic split."""
        if v < 1 or v > 99:
            raise ValueError("Control traffic must be between 1 and 99")
        return v


class ABTestUpdate(BaseModel):
    """Schema for updating an A/B test."""

    control_traffic_percent: int | None = Field(None, ge=1, le=99)


class ABTestResponse(BaseModel):
    """Schema for A/B test response."""

    id: UUID
    deployment_id: UUID
    tenant_id: UUID
    name: str
    status: ABTestStatus
    control_version_id: UUID
    treatment_version_id: UUID
    control_traffic_percent: int
    treatment_traffic_percent: int
    start_time: datetime
    end_time: datetime | None
    winner_version_id: UUID | None
    metrics: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ABTestListResponse(BaseModel):
    """Schema for A/B test list."""

    items: list[ABTestResponse]
    total: int


class ABTestCompleteRequest(BaseModel):
    """Schema for completing an A/B test."""

    winner_version_id: UUID
    apply_winner: bool = True
