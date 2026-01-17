"""Pydantic schemas for monitoring domain."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from foundry.infrastructure.database.models import AlertSeverity, AlertCondition


# ============================================================================
# Alert Rule Schemas
# ============================================================================


class AlertRuleBase(BaseModel):
    """Base alert rule schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    metric: str = Field(..., min_length=1, max_length=255)
    condition: AlertCondition
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING


class AlertRuleCreate(AlertRuleBase):
    """Schema for creating an alert rule."""

    deployment_id: UUID | None = None
    notification_channels: list[str] = Field(default_factory=list)
    cooldown_minutes: int = Field(default=15, ge=1, le=1440)
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    metric: str | None = None
    condition: AlertCondition | None = None
    threshold: float | None = None
    severity: AlertSeverity | None = None
    notification_channels: list[str] | None = None
    cooldown_minutes: int | None = Field(None, ge=1, le=1440)
    enabled: bool | None = None


class AlertRuleResponse(AlertRuleBase):
    """Schema for alert rule response."""

    id: UUID
    tenant_id: UUID
    deployment_id: UUID | None
    notification_channels: list[str]
    cooldown_minutes: int
    enabled: bool
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertRuleListResponse(BaseModel):
    """Schema for paginated alert rule list."""

    items: list[AlertRuleResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# Alert Schemas
# ============================================================================


class AlertResponse(BaseModel):
    """Schema for alert instance response."""

    id: UUID
    rule_id: UUID
    deployment_id: UUID | None
    tenant_id: UUID
    severity: AlertSeverity
    metric_value: float
    threshold_value: float
    message: str
    acknowledged: bool
    acknowledged_at: datetime | None
    acknowledged_by: UUID | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """Schema for paginated alert list."""

    items: list[AlertResponse]
    total: int
    offset: int
    limit: int


class AlertAcknowledgeRequest(BaseModel):
    """Schema for acknowledging an alert."""

    comment: str | None = Field(None, max_length=1000)


# ============================================================================
# Drift Schemas
# ============================================================================


class FeatureDriftScore(BaseModel):
    """Drift score for a single feature."""

    feature_name: str
    drift_score: float
    drift_method: str
    status: str  # "none", "warning", "critical"
    baseline_stats: dict[str, Any] = Field(default_factory=dict)
    current_stats: dict[str, Any] = Field(default_factory=dict)


class DriftReportResponse(BaseModel):
    """Schema for drift report."""

    deployment_id: UUID
    report_time: datetime
    overall_drift_score: float
    overall_status: str
    feature_drifts: list[FeatureDriftScore]
    prediction_drift: FeatureDriftScore | None = None
    sample_count: int
    baseline_sample_count: int


class DriftHistoryRequest(BaseModel):
    """Schema for drift history query."""

    deployment_id: UUID
    feature_name: str | None = None
    start_time: datetime
    end_time: datetime


class DriftHistoryPoint(BaseModel):
    """Single point in drift history."""

    timestamp: datetime
    drift_score: float
    status: str


class DriftHistoryResponse(BaseModel):
    """Schema for drift history response."""

    deployment_id: UUID
    feature_name: str | None
    data: list[DriftHistoryPoint]


# ============================================================================
# Performance Metrics Schemas
# ============================================================================


class PerformanceMetric(BaseModel):
    """Single performance metric."""

    name: str
    value: float
    timestamp: datetime


class PerformanceReportResponse(BaseModel):
    """Schema for performance report."""

    deployment_id: UUID
    report_time: datetime
    metrics: dict[str, float]  # accuracy, precision, recall, f1, etc.
    confusion_matrix: list[list[int]] | None = None
    sample_count: int


class MetricTimeseriesRequest(BaseModel):
    """Schema for metric timeseries query."""

    deployment_id: UUID
    metric_name: str
    start_time: datetime
    end_time: datetime
    granularity: str = "1h"  # 1m, 5m, 1h, 1d


class MetricTimeseriesResponse(BaseModel):
    """Schema for metric timeseries response."""

    deployment_id: UUID
    metric_name: str
    data: list[PerformanceMetric]
