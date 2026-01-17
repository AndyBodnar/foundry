"""Pydantic schemas for experiments domain."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from foundry.infrastructure.database.models import RunStatus


# ============================================================================
# Experiment Schemas
# ============================================================================


class ExperimentBase(BaseModel):
    """Base experiment schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    tags: list[str] = Field(default_factory=list)


class ExperimentCreate(ExperimentBase):
    """Schema for creating an experiment."""

    pass


class ExperimentUpdate(BaseModel):
    """Schema for updating an experiment."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    tags: list[str] | None = None


class ExperimentResponse(ExperimentBase):
    """Schema for experiment response."""

    id: UUID
    tenant_id: UUID
    owner_id: UUID | None
    created_at: datetime
    updated_at: datetime
    run_count: int = 0

    model_config = {"from_attributes": True}


class ExperimentListResponse(BaseModel):
    """Schema for paginated experiment list."""

    items: list[ExperimentResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# Run Schemas
# ============================================================================


class RunBase(BaseModel):
    """Base run schema."""

    name: str | None = Field(None, max_length=255)
    tags: list[str] = Field(default_factory=list)


class RunCreate(RunBase):
    """Schema for creating a run."""

    parameters: dict[str, Any] = Field(default_factory=dict)
    git_commit: str | None = Field(None, max_length=40)
    source_name: str | None = Field(None, max_length=255)


class RunUpdate(BaseModel):
    """Schema for updating a run."""

    name: str | None = Field(None, max_length=255)
    status: RunStatus | None = None
    tags: list[str] | None = None


class RunResponse(RunBase):
    """Schema for run response."""

    id: UUID
    experiment_id: UUID
    tenant_id: UUID
    status: RunStatus
    parameters: dict[str, Any]
    metrics: dict[str, Any]
    start_time: datetime | None
    end_time: datetime | None
    git_commit: str | None
    source_name: str | None
    user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    duration_seconds: float | None = None

    model_config = {"from_attributes": True}


class RunListResponse(BaseModel):
    """Schema for paginated run list."""

    items: list[RunResponse]
    total: int
    offset: int
    limit: int


class RunStatusUpdate(BaseModel):
    """Schema for updating run status."""

    status: RunStatus
    end_time: datetime | None = None
    error_message: str | None = None


# ============================================================================
# Metric Schemas
# ============================================================================


class MetricValue(BaseModel):
    """Single metric value."""

    key: str = Field(..., min_length=1, max_length=255)
    value: float
    step: int = 0
    timestamp: datetime | None = None


class MetricLogRequest(BaseModel):
    """Schema for logging metrics."""

    metrics: list[MetricValue]


class MetricHistoryResponse(BaseModel):
    """Schema for metric history."""

    key: str
    values: list[dict[str, Any]]  # [{value, step, timestamp}, ...]


# ============================================================================
# Parameter Schemas
# ============================================================================


class ParamValue(BaseModel):
    """Single parameter value."""

    key: str = Field(..., min_length=1, max_length=255)
    value: Any


class ParamLogRequest(BaseModel):
    """Schema for logging parameters."""

    parameters: list[ParamValue]


# ============================================================================
# Artifact Schemas
# ============================================================================


class ArtifactUploadRequest(BaseModel):
    """Schema for artifact upload metadata."""

    name: str = Field(..., min_length=1, max_length=255)
    artifact_type: str = Field(..., min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactResponse(BaseModel):
    """Schema for artifact response."""

    id: UUID
    run_id: UUID
    name: str
    artifact_type: str
    path: str
    size_bytes: int | None
    checksum: str | None
    metadata: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ArtifactListResponse(BaseModel):
    """Schema for artifact list."""

    items: list[ArtifactResponse]
    total: int


# ============================================================================
# Run Comparison Schemas
# ============================================================================


class RunCompareRequest(BaseModel):
    """Schema for run comparison request."""

    run_ids: list[UUID] = Field(..., min_length=2, max_length=10)
    metric_keys: list[str] | None = None
    param_keys: list[str] | None = None


class RunMetricComparison(BaseModel):
    """Metrics for a single run in comparison."""

    run_id: UUID
    run_name: str | None
    metrics: dict[str, float]
    parameters: dict[str, Any]


class RunCompareResponse(BaseModel):
    """Schema for run comparison response."""

    runs: list[RunMetricComparison]
    metric_keys: list[str]
    param_keys: list[str]
