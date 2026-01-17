"""Experiments API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status

from foundry.api.v1.deps import (
    DbSession,
    Cache,
    Storage,
    CurrentUserDep,
    TenantId,
    DataScientistUser,
)
from foundry.domain.experiments.service import ExperimentService
from foundry.domain.experiments.schemas import (
    ExperimentCreate,
    ExperimentUpdate,
    ExperimentResponse,
    ExperimentListResponse,
    RunCreate,
    RunUpdate,
    RunResponse,
    RunListResponse,
    RunStatusUpdate,
    MetricLogRequest,
    ParamLogRequest,
    ArtifactUploadRequest,
    ArtifactResponse,
    ArtifactListResponse,
    MetricHistoryResponse,
    RunCompareRequest,
    RunCompareResponse,
)
from foundry.infrastructure.database.models import RunStatus
from foundry.core.exceptions import NotFoundError

router = APIRouter()


# ============================================================================
# Experiment Endpoints
# ============================================================================


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    data: ExperimentCreate,
    current_user: DataScientistUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Create a new experiment."""
    service = ExperimentService(db, tenant_id)
    experiment = await service.create_experiment(data, current_user.id)

    response = ExperimentResponse.model_validate(experiment)
    response.run_count = 0
    return response


@router.get("", response_model=ExperimentListResponse)
async def list_experiments(
    tenant_id: TenantId,
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = None,
    tags: list[str] | None = Query(None),
):
    """List experiments with optional filtering."""
    service = ExperimentService(db, tenant_id)
    experiments, total = await service.list_experiments(
        offset=offset,
        limit=limit,
        search=search,
        tags=tags,
    )

    items = []
    for exp in experiments:
        response = ExperimentResponse.model_validate(exp)
        response.run_count = await service.get_experiment_run_count(exp.id)
        items.append(response)

    return ExperimentListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get experiment by ID."""
    service = ExperimentService(db, tenant_id)

    try:
        experiment = await service.get_experiment(experiment_id)
        response = ExperimentResponse.model_validate(experiment)
        response.run_count = await service.get_experiment_run_count(experiment.id)
        return response
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: UUID,
    data: ExperimentUpdate,
    current_user: DataScientistUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Update an experiment."""
    service = ExperimentService(db, tenant_id)

    try:
        experiment = await service.update_experiment(experiment_id, data)
        response = ExperimentResponse.model_validate(experiment)
        response.run_count = await service.get_experiment_run_count(experiment.id)
        return response
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(
    experiment_id: UUID,
    current_user: DataScientistUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Delete an experiment."""
    service = ExperimentService(db, tenant_id)

    try:
        await service.delete_experiment(experiment_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


# ============================================================================
# Run Endpoints
# ============================================================================


@router.post("/{experiment_id}/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    experiment_id: UUID,
    data: RunCreate,
    current_user: DataScientistUser,
    tenant_id: TenantId,
    db: DbSession,
):
    """Create a new run for an experiment."""
    service = ExperimentService(db, tenant_id)

    try:
        run = await service.create_run(experiment_id, data, current_user.id)
        return RunResponse.model_validate(run)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/{experiment_id}/runs", response_model=RunListResponse)
async def list_runs(
    experiment_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: RunStatus | None = None,
):
    """List runs for an experiment."""
    service = ExperimentService(db, tenant_id)
    runs, total = await service.list_runs(
        experiment_id=experiment_id,
        offset=offset,
        limit=limit,
        status=status,
    )

    return RunListResponse(
        items=[RunResponse.model_validate(r) for r in runs],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get run by ID."""
    service = ExperimentService(db, tenant_id)

    try:
        run = await service.get_run(run_id)
        response = RunResponse.model_validate(run)
        if run.start_time and run.end_time:
            response.duration_seconds = (run.end_time - run.start_time).total_seconds()
        return response
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/runs/{run_id}/status", response_model=RunResponse)
async def update_run_status(
    run_id: UUID,
    data: RunStatusUpdate,
    tenant_id: TenantId,
    db: DbSession,
):
    """Update run status."""
    service = ExperimentService(db, tenant_id)

    try:
        run = await service.update_run_status(run_id, data)
        return RunResponse.model_validate(run)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


# ============================================================================
# Metrics & Parameters
# ============================================================================


@router.post("/runs/{run_id}/metrics", response_model=RunResponse)
async def log_metrics(
    run_id: UUID,
    data: MetricLogRequest,
    tenant_id: TenantId,
    db: DbSession,
):
    """Log metrics for a run."""
    service = ExperimentService(db, tenant_id)

    try:
        run = await service.log_metrics(run_id, data)
        return RunResponse.model_validate(run)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/runs/{run_id}/params", response_model=RunResponse)
async def log_parameters(
    run_id: UUID,
    data: ParamLogRequest,
    tenant_id: TenantId,
    db: DbSession,
):
    """Log parameters for a run."""
    service = ExperimentService(db, tenant_id)

    try:
        run = await service.log_parameters(run_id, data)
        return RunResponse.model_validate(run)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/runs/{run_id}/metrics/{key}", response_model=MetricHistoryResponse)
async def get_metric_history(
    run_id: UUID,
    key: str,
    tenant_id: TenantId,
    db: DbSession,
):
    """Get metric history for a run."""
    service = ExperimentService(db, tenant_id)

    try:
        history = await service.get_metric_history(run_id, key)
        return MetricHistoryResponse(
            key=key,
            values=[
                {"value": h.value, "step": h.step, "timestamp": h.timestamp}
                for h in history
            ],
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


# ============================================================================
# Artifacts
# ============================================================================


@router.post("/runs/{run_id}/artifacts", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def upload_artifact(
    run_id: UUID,
    file: UploadFile,
    tenant_id: TenantId,
    db: DbSession,
    storage: Storage,
    name: str = Query(...),
    artifact_type: str = Query(...),
):
    """Upload an artifact for a run."""
    service = ExperimentService(db, tenant_id, storage)

    content = await file.read()
    data = ArtifactUploadRequest(
        name=name,
        artifact_type=artifact_type,
    )

    try:
        artifact = await service.upload_artifact(
            run_id,
            data,
            content,
            file.content_type or "application/octet-stream",
        )
        return ArtifactResponse.model_validate(artifact)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/runs/{run_id}/artifacts", response_model=ArtifactListResponse)
async def list_artifacts(
    run_id: UUID,
    tenant_id: TenantId,
    db: DbSession,
):
    """List artifacts for a run."""
    service = ExperimentService(db, tenant_id)

    try:
        artifacts = await service.list_artifacts(run_id)
        return ArtifactListResponse(
            items=[ArtifactResponse.model_validate(a) for a in artifacts],
            total=len(artifacts),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


# ============================================================================
# Run Comparison
# ============================================================================


@router.post("/runs/compare", response_model=RunCompareResponse)
async def compare_runs(
    data: RunCompareRequest,
    tenant_id: TenantId,
    db: DbSession,
):
    """Compare multiple runs."""
    service = ExperimentService(db, tenant_id)

    try:
        return await service.compare_runs(data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
