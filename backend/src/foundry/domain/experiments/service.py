"""Experiment service - business logic for experiment tracking."""

from datetime import datetime, timezone
from typing import Any, BinaryIO, Sequence
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from foundry.core.exceptions import NotFoundError, ConflictError, ValidationError
from foundry.infrastructure.database.models import (
    Experiment,
    Run,
    Artifact,
    MetricHistory,
    RunStatus,
)
from foundry.infrastructure.storage.s3 import S3Storage
from foundry.domain.experiments.schemas import (
    ExperimentCreate,
    ExperimentUpdate,
    RunCreate,
    RunUpdate,
    RunStatusUpdate,
    MetricLogRequest,
    ParamLogRequest,
    ArtifactUploadRequest,
    RunCompareRequest,
    RunCompareResponse,
    RunMetricComparison,
)


class ExperimentService:
    """Service for experiment and run management."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        storage: S3Storage | None = None,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.storage = storage

    # ========================================================================
    # Experiment Operations
    # ========================================================================

    async def create_experiment(
        self,
        data: ExperimentCreate,
        owner_id: UUID | None = None,
    ) -> Experiment:
        """Create a new experiment."""
        # Check for duplicate name within tenant
        existing = await self.session.execute(
            select(Experiment).where(
                Experiment.tenant_id == self.tenant_id,
                Experiment.name == data.name,
                Experiment.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                "Experiment",
                f"Experiment with name '{data.name}' already exists",
            )

        experiment = Experiment(
            tenant_id=self.tenant_id,
            name=data.name,
            description=data.description,
            tags=data.tags,
            owner_id=owner_id,
        )
        self.session.add(experiment)
        await self.session.flush()
        await self.session.refresh(experiment)
        return experiment

    async def get_experiment(self, experiment_id: UUID) -> Experiment:
        """Get experiment by ID."""
        result = await self.session.execute(
            select(Experiment).where(
                Experiment.id == experiment_id,
                Experiment.tenant_id == self.tenant_id,
                Experiment.deleted_at.is_(None),
            )
        )
        experiment = result.scalar_one_or_none()
        if not experiment:
            raise NotFoundError("Experiment", str(experiment_id))
        return experiment

    async def get_experiment_by_name(self, name: str) -> Experiment:
        """Get experiment by name."""
        result = await self.session.execute(
            select(Experiment).where(
                Experiment.tenant_id == self.tenant_id,
                Experiment.name == name,
                Experiment.deleted_at.is_(None),
            )
        )
        experiment = result.scalar_one_or_none()
        if not experiment:
            raise NotFoundError("Experiment", name)
        return experiment

    async def list_experiments(
        self,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        tags: list[str] | None = None,
    ) -> tuple[Sequence[Experiment], int]:
        """List experiments with pagination and filtering."""
        # Build base query
        base_conditions = [
            Experiment.tenant_id == self.tenant_id,
            Experiment.deleted_at.is_(None),
        ]

        if search:
            base_conditions.append(
                Experiment.name.ilike(f"%{search}%")
            )

        if tags:
            base_conditions.append(
                Experiment.tags.contains(tags)
            )

        # Get total count
        count_query = select(func.count(Experiment.id)).where(and_(*base_conditions))
        total = (await self.session.execute(count_query)).scalar() or 0

        # Get experiments
        query = (
            select(Experiment)
            .where(and_(*base_conditions))
            .order_by(Experiment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        experiments = result.scalars().all()

        return experiments, total

    async def update_experiment(
        self,
        experiment_id: UUID,
        data: ExperimentUpdate,
    ) -> Experiment:
        """Update an experiment."""
        experiment = await self.get_experiment(experiment_id)

        # Check for name conflict if name is being changed
        if data.name and data.name != experiment.name:
            existing = await self.session.execute(
                select(Experiment).where(
                    Experiment.tenant_id == self.tenant_id,
                    Experiment.name == data.name,
                    Experiment.deleted_at.is_(None),
                    Experiment.id != experiment_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(
                    "Experiment",
                    f"Experiment with name '{data.name}' already exists",
                )

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(experiment, field, value)

        await self.session.flush()
        await self.session.refresh(experiment)
        return experiment

    async def delete_experiment(self, experiment_id: UUID) -> None:
        """Soft delete an experiment."""
        experiment = await self.get_experiment(experiment_id)
        experiment.soft_delete()
        await self.session.flush()

    async def get_experiment_run_count(self, experiment_id: UUID) -> int:
        """Get the number of runs for an experiment."""
        result = await self.session.execute(
            select(func.count(Run.id)).where(
                Run.experiment_id == experiment_id,
                Run.tenant_id == self.tenant_id,
            )
        )
        return result.scalar() or 0

    # ========================================================================
    # Run Operations
    # ========================================================================

    async def create_run(
        self,
        experiment_id: UUID,
        data: RunCreate,
        user_id: UUID | None = None,
    ) -> Run:
        """Create a new run for an experiment."""
        # Verify experiment exists
        await self.get_experiment(experiment_id)

        run = Run(
            tenant_id=self.tenant_id,
            experiment_id=experiment_id,
            name=data.name,
            status=RunStatus.PENDING,
            parameters=data.parameters,
            metrics={},
            tags=data.tags,
            git_commit=data.git_commit,
            source_name=data.source_name,
            user_id=user_id,
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> Run:
        """Get run by ID."""
        result = await self.session.execute(
            select(Run).where(
                Run.id == run_id,
                Run.tenant_id == self.tenant_id,
            )
        )
        run = result.scalar_one_or_none()
        if not run:
            raise NotFoundError("Run", str(run_id))
        return run

    async def list_runs(
        self,
        experiment_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
        status: RunStatus | None = None,
    ) -> tuple[Sequence[Run], int]:
        """List runs with pagination and filtering."""
        base_conditions = [Run.tenant_id == self.tenant_id]

        if experiment_id:
            base_conditions.append(Run.experiment_id == experiment_id)

        if status:
            base_conditions.append(Run.status == status)

        # Get total count
        count_query = select(func.count(Run.id)).where(and_(*base_conditions))
        total = (await self.session.execute(count_query)).scalar() or 0

        # Get runs
        query = (
            select(Run)
            .where(and_(*base_conditions))
            .order_by(Run.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        runs = result.scalars().all()

        return runs, total

    async def update_run(
        self,
        run_id: UUID,
        data: RunUpdate,
    ) -> Run:
        """Update a run."""
        run = await self.get_run(run_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(run, field, value)

        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run_status(
        self,
        run_id: UUID,
        data: RunStatusUpdate,
    ) -> Run:
        """Update run status with appropriate timestamps."""
        run = await self.get_run(run_id)

        # Set start time if transitioning to RUNNING
        if data.status == RunStatus.RUNNING and run.status == RunStatus.PENDING:
            run.start_time = datetime.now(timezone.utc)

        # Set end time if transitioning to terminal state
        if data.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            run.end_time = data.end_time or datetime.now(timezone.utc)

        run.status = data.status
        await self.session.flush()
        await self.session.refresh(run)
        return run

    # ========================================================================
    # Metrics Operations
    # ========================================================================

    async def log_metrics(
        self,
        run_id: UUID,
        data: MetricLogRequest,
    ) -> Run:
        """Log metrics for a run."""
        run = await self.get_run(run_id)

        for metric in data.metrics:
            # Update latest metric value in run.metrics
            run.metrics[metric.key] = metric.value

            # Add to metric history
            history = MetricHistory(
                tenant_id=self.tenant_id,
                run_id=run_id,
                key=metric.key,
                value=metric.value,
                step=metric.step,
                timestamp=metric.timestamp or datetime.now(timezone.utc),
            )
            self.session.add(history)

        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_metric_history(
        self,
        run_id: UUID,
        key: str | None = None,
    ) -> Sequence[MetricHistory]:
        """Get metric history for a run."""
        # Verify run exists
        await self.get_run(run_id)

        query = (
            select(MetricHistory)
            .where(
                MetricHistory.run_id == run_id,
                MetricHistory.tenant_id == self.tenant_id,
            )
            .order_by(MetricHistory.step.asc())
        )

        if key:
            query = query.where(MetricHistory.key == key)

        result = await self.session.execute(query)
        return result.scalars().all()

    # ========================================================================
    # Parameters Operations
    # ========================================================================

    async def log_parameters(
        self,
        run_id: UUID,
        data: ParamLogRequest,
    ) -> Run:
        """Log parameters for a run."""
        run = await self.get_run(run_id)

        for param in data.parameters:
            run.parameters[param.key] = param.value

        await self.session.flush()
        await self.session.refresh(run)
        return run

    # ========================================================================
    # Artifact Operations
    # ========================================================================

    async def upload_artifact(
        self,
        run_id: UUID,
        data: ArtifactUploadRequest,
        content: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> Artifact:
        """Upload an artifact for a run."""
        if not self.storage:
            raise ValidationError("Storage not configured")

        run = await self.get_run(run_id)

        # Build storage path
        file_path = f"experiments/{run.experiment_id}/runs/{run_id}/artifacts/{data.name}"

        # Upload to S3
        upload_result = await self.storage.upload_file(
            tenant_id=str(self.tenant_id),
            file_path=file_path,
            content=content,
            content_type=content_type,
            metadata={"artifact_type": data.artifact_type},
        )

        # Create artifact record
        artifact = Artifact(
            tenant_id=self.tenant_id,
            run_id=run_id,
            name=data.name,
            artifact_type=data.artifact_type,
            path=upload_result["path"],
            size_bytes=upload_result["size_bytes"],
            checksum=upload_result["checksum"],
            metadata=data.metadata,
        )
        self.session.add(artifact)
        await self.session.flush()
        await self.session.refresh(artifact)
        return artifact

    async def get_artifact(self, artifact_id: UUID) -> Artifact:
        """Get artifact by ID."""
        result = await self.session.execute(
            select(Artifact).where(
                Artifact.id == artifact_id,
                Artifact.tenant_id == self.tenant_id,
            )
        )
        artifact = result.scalar_one_or_none()
        if not artifact:
            raise NotFoundError("Artifact", str(artifact_id))
        return artifact

    async def list_artifacts(
        self,
        run_id: UUID,
    ) -> Sequence[Artifact]:
        """List artifacts for a run."""
        await self.get_run(run_id)

        query = (
            select(Artifact)
            .where(
                Artifact.run_id == run_id,
                Artifact.tenant_id == self.tenant_id,
            )
            .order_by(Artifact.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def download_artifact(self, artifact_id: UUID) -> bytes:
        """Download artifact content."""
        if not self.storage:
            raise ValidationError("Storage not configured")

        artifact = await self.get_artifact(artifact_id)

        # Extract file path from S3 URL
        # Format: s3://bucket/tenants/{tenant_id}/{path}
        path_parts = artifact.path.split(f"tenants/{self.tenant_id}/", 1)
        if len(path_parts) != 2:
            raise ValidationError("Invalid artifact path")

        return await self.storage.download_file(
            tenant_id=str(self.tenant_id),
            file_path=path_parts[1],
        )

    # ========================================================================
    # Run Comparison
    # ========================================================================

    async def compare_runs(
        self,
        data: RunCompareRequest,
    ) -> RunCompareResponse:
        """Compare multiple runs."""
        runs = []
        all_metric_keys: set[str] = set()
        all_param_keys: set[str] = set()

        for run_id in data.run_ids:
            run = await self.get_run(run_id)
            runs.append(run)
            all_metric_keys.update(run.metrics.keys())
            all_param_keys.update(run.parameters.keys())

        # Filter keys if specified
        metric_keys = (
            list(set(data.metric_keys) & all_metric_keys)
            if data.metric_keys
            else list(all_metric_keys)
        )
        param_keys = (
            list(set(data.param_keys) & all_param_keys)
            if data.param_keys
            else list(all_param_keys)
        )

        comparisons = []
        for run in runs:
            comparison = RunMetricComparison(
                run_id=run.id,
                run_name=run.name,
                metrics={k: run.metrics.get(k, 0.0) for k in metric_keys},
                parameters={k: run.parameters.get(k) for k in param_keys},
            )
            comparisons.append(comparison)

        return RunCompareResponse(
            runs=comparisons,
            metric_keys=metric_keys,
            param_keys=param_keys,
        )
