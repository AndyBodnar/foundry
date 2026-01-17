"""Model Registry API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from foundry.api.v1.deps import DbSession, CurrentUserDep, TenantId, MLEngineerUser
from foundry.domain.registry.service import RegistryService
from foundry.domain.registry.schemas import (
    ModelCreate,
    ModelUpdate,
    ModelResponse,
    ModelListResponse,
    ModelVersionCreate,
    ModelVersionResponse,
    ModelVersionListResponse,
    StageTransitionRequest,
    StageTransitionResponse,
    StageTransitionHistoryResponse,
    ModelLineageResponse,
)
from foundry.infrastructure.database.models import ModelStage
from foundry.core.exceptions import NotFoundError, ConflictError, ModelStageTransitionError

router = APIRouter()


# ============================================================================
# Model Endpoints
# ============================================================================


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def register_model(
    data: ModelCreate,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Register a new model."""
    service = RegistryService(db, tenant_id)

    try:
        model = await service.create_model(data, current_user.id)
        response = ModelResponse.model_validate(model)
        response.version_count = 0
        return response
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.get("", response_model=ModelListResponse)
async def list_models(
    tenant_id: TenantId,
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = None,
    tags: list[str] | None = Query(None),
):
    """List registered models."""
    service = RegistryService(db, tenant_id)
    models, total = await service.list_models(
        offset=offset,
        limit=limit,
        search=search,
        tags=tags,
    )

    items = []
    for model in models:
        response = ModelResponse.model_validate(model)
        response.version_count = await service.get_model_version_count(model.id)

        latest = await service.get_latest_version(model.id)
        response.latest_version = latest.version if latest else None

        prod = await service.get_production_version(model.id)
        response.production_version = prod.version if prod else None

        items.append(response)

    return ModelListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{name}", response_model=ModelResponse)
async def get_model(
    name: str,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get model by name."""
    service = RegistryService(db, tenant_id)

    try:
        model = await service.get_model_by_name(name)
        response = ModelResponse.model_validate(model)
        response.version_count = await service.get_model_version_count(model.id)

        latest = await service.get_latest_version(model.id)
        response.latest_version = latest.version if latest else None

        prod = await service.get_production_version(model.id)
        response.production_version = prod.version if prod else None

        return response
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/{name}", response_model=ModelResponse)
async def update_model(
    name: str,
    data: ModelUpdate,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Update a model."""
    service = RegistryService(db, tenant_id)

    try:
        model = await service.update_model(name, data)
        response = ModelResponse.model_validate(model)
        response.version_count = await service.get_model_version_count(model.id)
        return response
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    name: str,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Delete a model."""
    service = RegistryService(db, tenant_id)

    try:
        await service.delete_model(name)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


# ============================================================================
# Model Version Endpoints
# ============================================================================


@router.post("/{name}/versions", response_model=ModelVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    name: str,
    data: ModelVersionCreate,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Create a new model version."""
    service = RegistryService(db, tenant_id)

    try:
        version = await service.create_version(name, data)
        return ModelVersionResponse.model_validate(version)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.get("/{name}/versions", response_model=ModelVersionListResponse)
async def list_versions(
    name: str,
    tenant_id: TenantId,
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    stage: ModelStage | None = None,
):
    """List versions for a model."""
    service = RegistryService(db, tenant_id)

    try:
        versions, total = await service.list_versions(
            name,
            offset=offset,
            limit=limit,
            stage=stage,
        )
        return ModelVersionListResponse(
            items=[ModelVersionResponse.model_validate(v) for v in versions],
            total=total,
            offset=offset,
            limit=limit,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/{name}/versions/{version}", response_model=ModelVersionResponse)
async def get_version(
    name: str,
    version: str,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get a specific model version."""
    service = RegistryService(db, tenant_id)

    try:
        model_version = await service.get_version(name, version)
        return ModelVersionResponse.model_validate(model_version)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/{name}/versions/{version}/stage", response_model=ModelVersionResponse)
async def transition_stage(
    name: str,
    version: str,
    data: StageTransitionRequest,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Transition a model version to a new stage."""
    service = RegistryService(db, tenant_id)

    try:
        model_version = await service.transition_stage(
            name,
            version,
            data,
            current_user.id,
        )
        return ModelVersionResponse.model_validate(model_version)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ModelStageTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/{name}/versions/{version}/history", response_model=StageTransitionHistoryResponse)
async def get_stage_history(
    name: str,
    version: str,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get stage transition history for a model version."""
    service = RegistryService(db, tenant_id)

    try:
        transitions = await service.get_stage_history(name, version)
        return StageTransitionHistoryResponse(
            items=[StageTransitionResponse.model_validate(t) for t in transitions]
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/{name}/versions/{version}/lineage", response_model=ModelLineageResponse)
async def get_lineage(
    name: str,
    version: str,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get lineage information for a model version."""
    service = RegistryService(db, tenant_id)

    try:
        return await service.get_lineage(name, version)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
