"""Pydantic schemas for features domain."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Feature View Schemas
# ============================================================================


class FeatureDefinition(BaseModel):
    """Definition of a single feature."""

    name: str = Field(..., min_length=1, max_length=255)
    dtype: str = Field(..., min_length=1, max_length=50)  # int, float, string, etc.
    description: str | None = None
    default_value: Any | None = None


class SourceConfig(BaseModel):
    """Source configuration for feature view."""

    source_type: str  # "batch", "stream", "request"
    path: str | None = None  # For batch sources
    table: str | None = None  # For database sources
    timestamp_field: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class FeatureViewBase(BaseModel):
    """Base feature view schema."""

    name: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9_]+$")
    description: str | None = Field(None, max_length=5000)


class FeatureViewCreate(FeatureViewBase):
    """Schema for creating a feature view."""

    entities: list[str] = Field(..., min_length=1)
    features: list[FeatureDefinition]
    source_config: SourceConfig
    ttl_seconds: int | None = Field(None, ge=0)
    online_enabled: bool = True
    offline_enabled: bool = True


class FeatureViewUpdate(BaseModel):
    """Schema for updating a feature view."""

    description: str | None = None
    ttl_seconds: int | None = Field(None, ge=0)
    online_enabled: bool | None = None
    offline_enabled: bool | None = None


class FeatureViewResponse(FeatureViewBase):
    """Schema for feature view response."""

    id: UUID
    tenant_id: UUID
    entities: list[str]
    features: dict[str, Any]
    source_config: dict[str, Any]
    ttl_seconds: int | None
    online_enabled: bool
    offline_enabled: bool
    owner_id: UUID | None
    created_at: datetime
    updated_at: datetime
    materialization_status: str | None = None
    last_materialized_at: datetime | None = None

    model_config = {"from_attributes": True}


class FeatureViewListResponse(BaseModel):
    """Schema for paginated feature view list."""

    items: list[FeatureViewResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# Feature Value Schemas
# ============================================================================


class EntityKey(BaseModel):
    """Entity key for feature lookup."""

    entity_type: str
    entity_id: str


class FeatureValueRequest(BaseModel):
    """Schema for requesting feature values."""

    feature_view: str
    entities: list[EntityKey]
    features: list[str] | None = None  # None = all features


class FeatureValue(BaseModel):
    """Single feature value."""

    entity_key: EntityKey
    values: dict[str, Any]
    timestamp: datetime | None = None


class FeatureValueResponse(BaseModel):
    """Schema for feature value response."""

    feature_view: str
    results: list[FeatureValue]
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchFeatureRequest(BaseModel):
    """Schema for batch feature retrieval."""

    feature_views: list[str]
    entity_df_path: str  # S3 path to entity DataFrame
    output_path: str  # S3 path for output


class BatchFeatureResponse(BaseModel):
    """Schema for batch feature response."""

    job_id: str
    status: str
    output_path: str | None = None


# ============================================================================
# Materialization Schemas
# ============================================================================


class MaterializationRequest(BaseModel):
    """Schema for triggering materialization."""

    start_time: datetime | None = None
    end_time: datetime | None = None


class MaterializationJobResponse(BaseModel):
    """Schema for materialization job response."""

    id: UUID
    feature_view_id: UUID
    status: str  # "pending", "running", "success", "failed"
    start_time: datetime | None
    end_time: datetime | None
    records_processed: int | None
    error_message: str | None
    created_at: datetime


# ============================================================================
# Feature Statistics Schemas
# ============================================================================


class FeatureStats(BaseModel):
    """Statistics for a single feature."""

    feature_name: str
    count: int
    null_count: int
    unique_count: int | None = None
    mean: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None
    percentiles: dict[str, float] | None = None


class FeatureViewStatsResponse(BaseModel):
    """Schema for feature view statistics."""

    feature_view: str
    computed_at: datetime
    total_entities: int
    feature_stats: list[FeatureStats]
