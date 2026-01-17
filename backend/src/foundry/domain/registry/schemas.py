"""Pydantic schemas for model registry domain."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from foundry.infrastructure.database.models import ModelStage


# ============================================================================
# Model Schemas
# ============================================================================


class ModelBase(BaseModel):
    """Base model schema."""

    name: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9_-]+$")
    description: str | None = Field(None, max_length=5000)
    tags: list[str] = Field(default_factory=list)


class ModelCreate(ModelBase):
    """Schema for creating a model."""

    pass


class ModelUpdate(BaseModel):
    """Schema for updating a model."""

    description: str | None = None
    tags: list[str] | None = None


class ModelResponse(ModelBase):
    """Schema for model response."""

    id: UUID
    tenant_id: UUID
    owner_id: UUID | None
    created_at: datetime
    updated_at: datetime
    version_count: int = 0
    latest_version: str | None = None
    production_version: str | None = None

    model_config = {"from_attributes": True}


class ModelListResponse(BaseModel):
    """Schema for paginated model list."""

    items: list[ModelResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# Model Version Schemas
# ============================================================================


class ModelSignature(BaseModel):
    """Model input/output signature."""

    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)


class ModelVersionCreate(BaseModel):
    """Schema for creating a model version."""

    version: str = Field(..., min_length=1, max_length=50)
    artifact_path: str = Field(..., min_length=1)
    run_id: UUID | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    signature: ModelSignature | None = None
    description: str | None = Field(None, max_length=5000)


class ModelVersionUpdate(BaseModel):
    """Schema for updating a model version."""

    description: str | None = None


class ModelVersionResponse(BaseModel):
    """Schema for model version response."""

    id: UUID
    model_id: UUID
    tenant_id: UUID
    version: str
    stage: ModelStage
    artifact_path: str
    run_id: UUID | None
    metrics: dict[str, Any]
    signature: dict[str, Any] | None
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelVersionListResponse(BaseModel):
    """Schema for paginated model version list."""

    items: list[ModelVersionResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# Stage Transition Schemas
# ============================================================================


class StageTransitionRequest(BaseModel):
    """Schema for stage transition request."""

    stage: ModelStage
    comment: str | None = Field(None, max_length=1000)
    archive_existing_versions: bool = False


class StageTransitionResponse(BaseModel):
    """Schema for stage transition response."""

    id: UUID
    model_version_id: UUID
    from_stage: ModelStage
    to_stage: ModelStage
    user_id: UUID | None
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StageTransitionHistoryResponse(BaseModel):
    """Schema for stage transition history."""

    items: list[StageTransitionResponse]


# ============================================================================
# Lineage Schemas
# ============================================================================


class RunSummary(BaseModel):
    """Summary of a run for lineage."""

    id: UUID
    experiment_id: UUID
    experiment_name: str
    parameters: dict[str, Any]
    metrics: dict[str, Any]


class ModelLineageResponse(BaseModel):
    """Schema for model version lineage."""

    model_version_id: UUID
    model_name: str
    version: str
    run: RunSummary | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    parent_versions: list[str] = Field(default_factory=list)
