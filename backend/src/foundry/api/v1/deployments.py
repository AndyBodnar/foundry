"""Deployments API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from foundry.api.v1.deps import DbSession, CurrentUserDep, TenantId, MLEngineerUser
from foundry.domain.deployments.service import DeploymentService
from foundry.domain.deployments.schemas import (
    DeploymentCreate,
    DeploymentUpdate,
    DeploymentResponse,
    DeploymentListResponse,
    TrafficConfigUpdate,
    DeploymentHealthResponse,
    RollbackRequest,
    ABTestCreate,
    ABTestResponse,
    ABTestListResponse,
    ABTestCompleteRequest,
)
from foundry.infrastructure.database.models import DeploymentStatus, ABTestStatus
from foundry.core.exceptions import NotFoundError, ConflictError, ValidationError, DeploymentError

router = APIRouter()


# ============================================================================
# Deployment Endpoints
# ============================================================================


@router.post("", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    data: DeploymentCreate,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Create a new deployment."""
    service = DeploymentService(db, tenant_id)

    try:
        deployment = await service.create_deployment(data, current_user.id)
        return DeploymentResponse.model_validate(deployment)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("", response_model=DeploymentListResponse)
async def list_deployments(
    tenant_id: TenantId,
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: DeploymentStatus | None = None,
):
    """List deployments."""
    service = DeploymentService(db, tenant_id)
    deployments, total = await service.list_deployments(
        offset=offset,
        limit=limit,
        status=status,
    )

    return DeploymentListResponse(
        items=[DeploymentResponse.model_validate(d) for d in deployments],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get deployment by ID."""
    service = DeploymentService(db, tenant_id)

    try:
        deployment = await service.get_deployment(deployment_id)
        return DeploymentResponse.model_validate(deployment)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(
    deployment_id: UUID,
    data: DeploymentUpdate,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Update a deployment."""
    service = DeploymentService(db, tenant_id)

    try:
        deployment = await service.update_deployment(deployment_id, data)
        return DeploymentResponse.model_validate(deployment)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except DeploymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.delete("/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deployment(
    deployment_id: UUID,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Delete a deployment."""
    service = DeploymentService(db, tenant_id)

    try:
        await service.delete_deployment(deployment_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/{deployment_id}/traffic", response_model=DeploymentResponse)
async def update_traffic(
    deployment_id: UUID,
    data: TrafficConfigUpdate,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Update deployment traffic configuration."""
    service = DeploymentService(db, tenant_id)

    try:
        deployment = await service.update_traffic(deployment_id, data)
        return DeploymentResponse.model_validate(deployment)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.post("/{deployment_id}/rollback", response_model=DeploymentResponse)
async def rollback_deployment(
    deployment_id: UUID,
    data: RollbackRequest,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Rollback a deployment to a previous version."""
    service = DeploymentService(db, tenant_id)

    try:
        deployment = await service.rollback(deployment_id, data)
        return DeploymentResponse.model_validate(deployment)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except (ValidationError, DeploymentError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/{deployment_id}/health", response_model=DeploymentHealthResponse)
async def get_deployment_health(
    deployment_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get deployment health status."""
    service = DeploymentService(db, tenant_id)

    try:
        return await service.get_health(deployment_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


# ============================================================================
# A/B Test Endpoints
# ============================================================================


@router.post("/{deployment_id}/ab-tests", response_model=ABTestResponse, status_code=status.HTTP_201_CREATED)
async def create_ab_test(
    deployment_id: UUID,
    data: ABTestCreate,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Create a new A/B test for a deployment."""
    service = DeploymentService(db, tenant_id)

    try:
        ab_test = await service.create_ab_test(deployment_id, data)
        return ABTestResponse.model_validate(ab_test)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except (ValidationError, DeploymentError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/{deployment_id}/ab-tests", response_model=ABTestListResponse)
async def list_ab_tests(
    deployment_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
    status: ABTestStatus | None = None,
):
    """List A/B tests for a deployment."""
    service = DeploymentService(db, tenant_id)

    try:
        tests, total = await service.list_ab_tests(deployment_id, status)
        return ABTestListResponse(
            items=[ABTestResponse.model_validate(t) for t in tests],
            total=total,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/ab-tests/{test_id}", response_model=ABTestResponse)
async def get_ab_test(
    test_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get A/B test by ID."""
    service = DeploymentService(db, tenant_id)

    try:
        ab_test = await service.get_ab_test(test_id)
        return ABTestResponse.model_validate(ab_test)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/ab-tests/{test_id}/complete", response_model=ABTestResponse)
async def complete_ab_test(
    test_id: UUID,
    data: ABTestCompleteRequest,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Complete an A/B test and optionally apply the winner."""
    service = DeploymentService(db, tenant_id)

    try:
        ab_test = await service.complete_ab_test(test_id, data)
        return ABTestResponse.model_validate(ab_test)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.post("/ab-tests/{test_id}/cancel", response_model=ABTestResponse)
async def cancel_ab_test(
    test_id: UUID,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Cancel a running A/B test."""
    service = DeploymentService(db, tenant_id)

    try:
        ab_test = await service.cancel_ab_test(test_id)
        return ABTestResponse.model_validate(ab_test)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
