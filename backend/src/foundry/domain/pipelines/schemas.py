"""Pydantic schemas for pipelines domain."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from foundry.infrastructure.database.models import PipelineStatus


# ============================================================================
# Pipeline Schemas
# ============================================================================


class TaskDefinition(BaseModel):
    """Definition of a task in a pipeline."""

    task_id: str = Field(..., min_length=1, max_length=255)
    task_type: str = Field(..., min_length=1, max_length=100)
    config: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


class DAGDefinition(BaseModel):
    """DAG definition for a pipeline."""

    tasks: list[TaskDefinition]
    default_args: dict[str, Any] = Field(default_factory=dict)


class PipelineBase(BaseModel):
    """Base pipeline schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)


class PipelineCreate(PipelineBase):
    """Schema for creating a pipeline."""

    dag_definition: DAGDefinition
    schedule: str | None = Field(None, max_length=100)  # Cron expression
    enabled: bool = True


class PipelineUpdate(BaseModel):
    """Schema for updating a pipeline."""

    description: str | None = None
    dag_definition: DAGDefinition | None = None
    schedule: str | None = None
    enabled: bool | None = None


class PipelineResponse(PipelineBase):
    """Schema for pipeline response."""

    id: UUID
    tenant_id: UUID
    dag_definition: dict[str, Any]
    schedule: str | None
    enabled: bool
    owner_id: UUID | None
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None = None
    last_run_status: PipelineStatus | None = None

    model_config = {"from_attributes": True}


class PipelineListResponse(BaseModel):
    """Schema for paginated pipeline list."""

    items: list[PipelineResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# Pipeline Run Schemas
# ============================================================================


class TriggerPipelineRequest(BaseModel):
    """Schema for triggering a pipeline run."""

    parameters: dict[str, Any] = Field(default_factory=dict)
    trigger_type: str = Field(default="manual", max_length=50)


class PipelineRunResponse(BaseModel):
    """Schema for pipeline run response."""

    id: UUID
    pipeline_id: UUID
    tenant_id: UUID
    status: PipelineStatus
    trigger_type: str
    start_time: datetime | None
    end_time: datetime | None
    parameters: dict[str, Any]
    error_message: str | None
    triggered_by: UUID | None
    created_at: datetime
    updated_at: datetime
    duration_seconds: float | None = None

    model_config = {"from_attributes": True}


class PipelineRunListResponse(BaseModel):
    """Schema for paginated pipeline run list."""

    items: list[PipelineRunResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# Pipeline Task Schemas
# ============================================================================


class PipelineTaskResponse(BaseModel):
    """Schema for pipeline task response."""

    id: UUID
    pipeline_run_id: UUID
    tenant_id: UUID
    task_id: str
    status: PipelineStatus
    start_time: datetime | None
    end_time: datetime | None
    error_message: str | None
    logs: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PipelineTaskListResponse(BaseModel):
    """Schema for pipeline task list."""

    items: list[PipelineTaskResponse]


# ============================================================================
# Pipeline Trigger Configuration
# ============================================================================


class DriftTriggerConfig(BaseModel):
    """Configuration for drift-based pipeline trigger."""

    deployment_id: UUID
    drift_threshold: float = Field(default=0.3, ge=0, le=1)
    check_interval_minutes: int = Field(default=60, ge=1)


class ScheduleTriggerConfig(BaseModel):
    """Configuration for schedule-based pipeline trigger."""

    cron_expression: str
    timezone: str = "UTC"


class DataArrivalTriggerConfig(BaseModel):
    """Configuration for data arrival pipeline trigger."""

    source_path: str
    min_records: int = Field(default=1000, ge=1)
    check_interval_minutes: int = Field(default=15, ge=1)


class PipelineTriggerCreate(BaseModel):
    """Schema for creating a pipeline trigger."""

    pipeline_id: UUID
    trigger_type: str  # "drift", "schedule", "data_arrival"
    config: dict[str, Any]
    enabled: bool = True


class PipelineTriggerResponse(BaseModel):
    """Schema for pipeline trigger response."""

    id: UUID
    pipeline_id: UUID
    trigger_type: str
    config: dict[str, Any]
    enabled: bool
    last_triggered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
