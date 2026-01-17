"""Pipelines API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from foundry.api.v1.deps import DbSession, CurrentUserDep, TenantId, MLEngineerUser
from foundry.domain.pipelines.service import PipelineService
from foundry.domain.pipelines.schemas import (
    PipelineCreate,
    PipelineUpdate,
    PipelineResponse,
    PipelineListResponse,
    PipelineRunResponse,
    PipelineRunListResponse,
    PipelineTaskResponse,
    PipelineTaskListResponse,
    TriggerPipelineRequest,
)
from foundry.infrastructure.database.models import PipelineStatus
from foundry.core.exceptions import NotFoundError, ConflictError, ValidationError

router = APIRouter()


# ============================================================================
# Pipeline Endpoints
# ============================================================================


@router.post("", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    data: PipelineCreate,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Create a new pipeline."""
    service = PipelineService(db, tenant_id)

    try:
        pipeline = await service.create_pipeline(data, current_user.id)
        response = PipelineResponse.model_validate(pipeline)

        # Get last run info
        last_run = await service.get_last_run(pipeline.id)
        if last_run:
            response.last_run_at = last_run.created_at
            response.last_run_status = last_run.status

        return response
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    tenant_id: TenantId,
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    enabled_only: bool = False,
):
    """List pipelines."""
    service = PipelineService(db, tenant_id)
    pipelines, total = await service.list_pipelines(
        offset=offset,
        limit=limit,
        enabled_only=enabled_only,
    )

    items = []
    for pipeline in pipelines:
        response = PipelineResponse.model_validate(pipeline)
        last_run = await service.get_last_run(pipeline.id)
        if last_run:
            response.last_run_at = last_run.created_at
            response.last_run_status = last_run.status
        items.append(response)

    return PipelineListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get pipeline by ID."""
    service = PipelineService(db, tenant_id)

    try:
        pipeline = await service.get_pipeline(pipeline_id)
        response = PipelineResponse.model_validate(pipeline)

        last_run = await service.get_last_run(pipeline.id)
        if last_run:
            response.last_run_at = last_run.created_at
            response.last_run_status = last_run.status

        return response
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: UUID,
    data: PipelineUpdate,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Update a pipeline."""
    service = PipelineService(db, tenant_id)

    try:
        pipeline = await service.update_pipeline(pipeline_id, data)
        return PipelineResponse.model_validate(pipeline)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(
    pipeline_id: UUID,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Delete a pipeline."""
    service = PipelineService(db, tenant_id)

    try:
        await service.delete_pipeline(pipeline_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


# ============================================================================
# Pipeline Run Endpoints
# ============================================================================


@router.post("/{pipeline_id}/trigger", response_model=PipelineRunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_pipeline(
    pipeline_id: UUID,
    data: TriggerPipelineRequest,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Trigger a pipeline run."""
    service = PipelineService(db, tenant_id)

    try:
        run = await service.trigger_pipeline(pipeline_id, data, current_user.id)
        return PipelineRunResponse.model_validate(run)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/{pipeline_id}/runs", response_model=PipelineRunListResponse)
async def list_pipeline_runs(
    pipeline_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
    status: PipelineStatus | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List runs for a pipeline."""
    service = PipelineService(db, tenant_id)
    runs, total = await service.list_pipeline_runs(
        pipeline_id=pipeline_id,
        status=status,
        offset=offset,
        limit=limit,
    )

    items = []
    for run in runs:
        response = PipelineRunResponse.model_validate(run)
        if run.start_time and run.end_time:
            response.duration_seconds = (run.end_time - run.start_time).total_seconds()
        items.append(response)

    return PipelineRunListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(
    run_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get pipeline run by ID."""
    service = PipelineService(db, tenant_id)

    try:
        run = await service.get_pipeline_run(run_id)
        response = PipelineRunResponse.model_validate(run)
        if run.start_time and run.end_time:
            response.duration_seconds = (run.end_time - run.start_time).total_seconds()
        return response
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/runs/{run_id}/cancel", response_model=PipelineRunResponse)
async def cancel_pipeline_run(
    run_id: UUID,
    current_user: MLEngineerUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Cancel a pipeline run."""
    service = PipelineService(db, tenant_id)

    try:
        run = await service.cancel_pipeline_run(run_id)
        return PipelineRunResponse.model_validate(run)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/runs/{run_id}/tasks", response_model=PipelineTaskListResponse)
async def get_pipeline_tasks(
    run_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get tasks for a pipeline run."""
    service = PipelineService(db, tenant_id)

    try:
        tasks = await service.get_pipeline_tasks(run_id)
        return PipelineTaskListResponse(
            items=[PipelineTaskResponse.model_validate(t) for t in tasks]
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
