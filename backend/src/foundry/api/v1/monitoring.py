"""Monitoring API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from foundry.api.v1.deps import DbSession, CurrentUserDep, TenantId, MLEngineerUser
from foundry.domain.monitoring.service import MonitoringService
from foundry.domain.monitoring.schemas import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertRuleListResponse,
    AlertResponse,
    AlertListResponse,
    AlertAcknowledgeRequest,
    DriftReportResponse,
    PerformanceReportResponse,
)
from foundry.infrastructure.database.models import AlertSeverity
from foundry.core.exceptions import NotFoundError, ValidationError

router = APIRouter()


# ============================================================================
# Alert Rule Endpoints
# ============================================================================


@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    data: AlertRuleCreate,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Create a new alert rule."""
    service = MonitoringService(db, tenant_id)

    try:
        rule = await service.create_alert_rule(data)
        return AlertRuleResponse.model_validate(rule)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/alert-rules", response_model=AlertRuleListResponse)
async def list_alert_rules(
    tenant_id: TenantId,
    db: DbSession,
    deployment_id: UUID | None = None,
    enabled_only: bool = False,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List alert rules."""
    service = MonitoringService(db, tenant_id)
    rules, total = await service.list_alert_rules(
        deployment_id=deployment_id,
        enabled_only=enabled_only,
        offset=offset,
        limit=limit,
    )

    return AlertRuleListResponse(
        items=[AlertRuleResponse.model_validate(r) for r in rules],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get alert rule by ID."""
    service = MonitoringService(db, tenant_id)

    try:
        rule = await service.get_alert_rule(rule_id)
        return AlertRuleResponse.model_validate(rule)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: UUID,
    data: AlertRuleUpdate,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Update an alert rule."""
    service = MonitoringService(db, tenant_id)

    try:
        rule = await service.update_alert_rule(rule_id, data)
        return AlertRuleResponse.model_validate(rule)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: UUID,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Delete an alert rule."""
    service = MonitoringService(db, tenant_id)

    try:
        await service.delete_alert_rule(rule_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


# ============================================================================
# Alert Endpoints
# ============================================================================


@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    tenant_id: TenantId,
    db: DbSession,
    deployment_id: UUID | None = None,
    severity: AlertSeverity | None = None,
    acknowledged: bool | None = None,
    resolved: bool | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List alerts with filtering."""
    service = MonitoringService(db, tenant_id)
    alerts, total = await service.list_alerts(
        deployment_id=deployment_id,
        severity=severity,
        acknowledged=acknowledged,
        resolved=resolved,
        offset=offset,
        limit=limit,
    )

    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in alerts],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get alert by ID."""
    service = MonitoringService(db, tenant_id)

    try:
        alert = await service.get_alert(alert_id)
        return AlertResponse.model_validate(alert)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    data: AlertAcknowledgeRequest,
    current_user: CurrentUserDep,
    tenant_id: TenantId,
    db: DbSession,
):
    """Acknowledge an alert."""
    service = MonitoringService(db, tenant_id)

    try:
        alert = await service.acknowledge_alert(alert_id, current_user.id)
        return AlertResponse.model_validate(alert)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    current_user: CurrentUserDep,
    tenant_id: TenantId,
    db: DbSession,
):
    """Resolve an alert."""
    service = MonitoringService(db, tenant_id)

    try:
        alert = await service.resolve_alert(alert_id)
        return AlertResponse.model_validate(alert)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


# ============================================================================
# Drift Detection Endpoints
# ============================================================================


@router.get("/deployments/{deployment_id}/drift", response_model=DriftReportResponse)
async def get_drift_report(
    deployment_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get current drift report for a deployment."""
    service = MonitoringService(db, tenant_id)

    try:
        return await service.get_drift_report(deployment_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/deployments/{deployment_id}/performance", response_model=PerformanceReportResponse)
async def get_performance_report(
    deployment_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get current performance report for a deployment."""
    service = MonitoringService(db, tenant_id)

    try:
        return await service.get_performance_report(deployment_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
