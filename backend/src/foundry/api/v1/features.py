"""Feature Store API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from foundry.api.v1.deps import DbSession, Cache, CurrentUserDep, TenantId, DataScientistUser
from foundry.domain.features.service import FeatureService
from foundry.domain.features.schemas import (
    FeatureViewCreate,
    FeatureViewUpdate,
    FeatureViewResponse,
    FeatureViewListResponse,
    FeatureValueRequest,
    FeatureValueResponse,
)
from foundry.core.exceptions import NotFoundError, ConflictError

router = APIRouter()


# ============================================================================
# Feature View Endpoints
# ============================================================================


@router.post("/views", response_model=FeatureViewResponse, status_code=status.HTTP_201_CREATED)
async def create_feature_view(
    data: FeatureViewCreate,
    current_user: DataScientistUser,
    tenant_id: TenantId,
    db: DbSession,
    cache: Cache,
):
    """Create a new feature view."""
    service = FeatureService(db, tenant_id, cache)

    try:
        fv = await service.create_feature_view(data, current_user.id)
        return FeatureViewResponse.model_validate(fv)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.get("/views", response_model=FeatureViewListResponse)
async def list_feature_views(
    tenant_id: TenantId,
    db: DbSession,
    cache: Cache,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    online_only: bool = False,
):
    """List feature views."""
    service = FeatureService(db, tenant_id, cache)
    feature_views, total = await service.list_feature_views(
        offset=offset,
        limit=limit,
        online_only=online_only,
    )

    return FeatureViewListResponse(
        items=[FeatureViewResponse.model_validate(fv) for fv in feature_views],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/views/{feature_view_id}", response_model=FeatureViewResponse)
async def get_feature_view(
    feature_view_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
    cache: Cache,
):
    """Get feature view by ID."""
    service = FeatureService(db, tenant_id, cache)

    try:
        fv = await service.get_feature_view(feature_view_id)
        response = FeatureViewResponse.model_validate(fv)

        # Get freshness info
        freshness = await service.get_freshness(fv.name)
        response.last_materialized_at = freshness.get("last_updated")

        return response
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/views/{feature_view_id}", response_model=FeatureViewResponse)
async def update_feature_view(
    feature_view_id: UUID,
    data: FeatureViewUpdate,
    current_user: DataScientistUser,
    tenant_id: TenantId,
    db: DbSession,
    cache: Cache,
):
    """Update a feature view."""
    service = FeatureService(db, tenant_id, cache)

    try:
        fv = await service.update_feature_view(feature_view_id, data)
        return FeatureViewResponse.model_validate(fv)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.delete("/views/{feature_view_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature_view(
    feature_view_id: UUID,
    current_user: DataScientistUser,
    tenant_id: TenantId,
    db: DbSession,
    cache: Cache,
):
    """Delete a feature view."""
    service = FeatureService(db, tenant_id, cache)

    try:
        await service.delete_feature_view(feature_view_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


# ============================================================================
# Online Feature Serving
# ============================================================================


@router.post("/online", response_model=FeatureValueResponse)
async def get_online_features(
    data: FeatureValueRequest,
    tenant_id: TenantId,
    db: DbSession,
    cache: Cache,
):
    """
    Get online feature values for entities.

    This is the low-latency endpoint for real-time feature serving.
    Features are fetched from Redis cache.
    """
    service = FeatureService(db, tenant_id, cache)

    try:
        return await service.get_online_features(data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/views/{name}/freshness")
async def get_feature_freshness(
    name: str,
    tenant_id: TenantId,
    db: DbSession,
    cache: Cache,
):
    """Get freshness metadata for a feature view."""
    service = FeatureService(db, tenant_id, cache)

    try:
        return await service.get_freshness(name)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
