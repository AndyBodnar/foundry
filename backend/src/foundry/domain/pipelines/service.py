"""Pipeline service - business logic for DAG management and orchestration."""

from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from foundry.core.exceptions import NotFoundError, ConflictError, ValidationError
from foundry.infrastructure.database.models import (
    Pipeline,
    PipelineRun,
    PipelineTask,
    PipelineStatus,
)
from foundry.domain.pipelines.schemas import (
    PipelineCreate,
    PipelineUpdate,
    TriggerPipelineRequest,
)


class PipelineService:
    """Service for pipeline management."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id

    # ========================================================================
    # Pipeline Operations
    # ========================================================================

    async def create_pipeline(
        self,
        data: PipelineCreate,
        owner_id: UUID | None = None,
    ) -> Pipeline:
        """Create a new pipeline."""
        # Check for duplicate name
        existing = await self.session.execute(
            select(Pipeline).where(
                Pipeline.tenant_id == self.tenant_id,
                Pipeline.name == data.name,
                Pipeline.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                "Pipeline",
                f"Pipeline with name '{data.name}' already exists",
            )

        # Validate DAG definition
        self._validate_dag(data.dag_definition.model_dump())

        pipeline = Pipeline(
            tenant_id=self.tenant_id,
            name=data.name,
            description=data.description,
            dag_definition=data.dag_definition.model_dump(),
            schedule=data.schedule,
            enabled=data.enabled,
            owner_id=owner_id,
        )
        self.session.add(pipeline)
        await self.session.flush()
        await self.session.refresh(pipeline)
        return pipeline

    async def get_pipeline(self, pipeline_id: UUID) -> Pipeline:
        """Get pipeline by ID."""
        result = await self.session.execute(
            select(Pipeline).where(
                Pipeline.id == pipeline_id,
                Pipeline.tenant_id == self.tenant_id,
                Pipeline.deleted_at.is_(None),
            )
        )
        pipeline = result.scalar_one_or_none()
        if not pipeline:
            raise NotFoundError("Pipeline", str(pipeline_id))
        return pipeline

    async def get_pipeline_by_name(self, name: str) -> Pipeline:
        """Get pipeline by name."""
        result = await self.session.execute(
            select(Pipeline).where(
                Pipeline.tenant_id == self.tenant_id,
                Pipeline.name == name,
                Pipeline.deleted_at.is_(None),
            )
        )
        pipeline = result.scalar_one_or_none()
        if not pipeline:
            raise NotFoundError("Pipeline", name)
        return pipeline

    async def list_pipelines(
        self,
        offset: int = 0,
        limit: int = 100,
        enabled_only: bool = False,
    ) -> tuple[Sequence[Pipeline], int]:
        """List pipelines with pagination."""
        base_conditions = [
            Pipeline.tenant_id == self.tenant_id,
            Pipeline.deleted_at.is_(None),
        ]

        if enabled_only:
            base_conditions.append(Pipeline.enabled == True)

        count_query = select(func.count(Pipeline.id)).where(and_(*base_conditions))
        total = (await self.session.execute(count_query)).scalar() or 0

        query = (
            select(Pipeline)
            .where(and_(*base_conditions))
            .order_by(Pipeline.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        pipelines = result.scalars().all()

        return pipelines, total

    async def update_pipeline(
        self,
        pipeline_id: UUID,
        data: PipelineUpdate,
    ) -> Pipeline:
        """Update a pipeline."""
        pipeline = await self.get_pipeline(pipeline_id)

        update_data = data.model_dump(exclude_unset=True)

        # Validate DAG if being updated
        if "dag_definition" in update_data and update_data["dag_definition"]:
            self._validate_dag(update_data["dag_definition"].model_dump())
            update_data["dag_definition"] = update_data["dag_definition"].model_dump()

        for field, value in update_data.items():
            if value is not None:
                setattr(pipeline, field, value)

        await self.session.flush()
        await self.session.refresh(pipeline)
        return pipeline

    async def delete_pipeline(self, pipeline_id: UUID) -> None:
        """Soft delete a pipeline."""
        pipeline = await self.get_pipeline(pipeline_id)
        pipeline.soft_delete()
        await self.session.flush()

    def _validate_dag(self, dag_definition: dict[str, Any]) -> None:
        """Validate DAG definition."""
        tasks = dag_definition.get("tasks", [])
        if not tasks:
            raise ValidationError("DAG must have at least one task")

        task_ids = set()
        for task in tasks:
            task_id = task.get("task_id")
            if not task_id:
                raise ValidationError("Each task must have a task_id")
            if task_id in task_ids:
                raise ValidationError(f"Duplicate task_id: {task_id}")
            task_ids.add(task_id)

        # Validate dependencies exist
        for task in tasks:
            for dep in task.get("dependencies", []):
                if dep not in task_ids:
                    raise ValidationError(
                        f"Task '{task['task_id']}' depends on unknown task '{dep}'"
                    )

        # Check for cycles
        self._check_dag_cycles(tasks)

    def _check_dag_cycles(self, tasks: list[dict[str, Any]]) -> None:
        """Check for cycles in DAG using DFS."""
        # Build adjacency list
        graph: dict[str, list[str]] = {}
        for task in tasks:
            task_id = task["task_id"]
            graph[task_id] = task.get("dependencies", [])

        # DFS for cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {task_id: WHITE for task_id in graph}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in graph.get(node, []):
                if color[neighbor] == GRAY:
                    return True  # Cycle found
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        for task_id in graph:
            if color[task_id] == WHITE:
                if dfs(task_id):
                    raise ValidationError("DAG contains a cycle")

    # ========================================================================
    # Pipeline Run Operations
    # ========================================================================

    async def trigger_pipeline(
        self,
        pipeline_id: UUID,
        data: TriggerPipelineRequest,
        user_id: UUID | None = None,
    ) -> PipelineRun:
        """Trigger a pipeline run."""
        pipeline = await self.get_pipeline(pipeline_id)

        if not pipeline.enabled:
            raise ValidationError("Pipeline is disabled")

        # Create pipeline run
        pipeline_run = PipelineRun(
            tenant_id=self.tenant_id,
            pipeline_id=pipeline_id,
            status=PipelineStatus.PENDING,
            trigger_type=data.trigger_type,
            parameters=data.parameters,
            triggered_by=user_id,
        )
        self.session.add(pipeline_run)
        await self.session.flush()

        # Create task records
        dag = pipeline.dag_definition
        for task_def in dag.get("tasks", []):
            task = PipelineTask(
                tenant_id=self.tenant_id,
                pipeline_run_id=pipeline_run.id,
                task_id=task_def["task_id"],
                status=PipelineStatus.PENDING,
            )
            self.session.add(task)

        await self.session.flush()
        await self.session.refresh(pipeline_run)
        return pipeline_run

    async def get_pipeline_run(self, run_id: UUID) -> PipelineRun:
        """Get pipeline run by ID."""
        result = await self.session.execute(
            select(PipelineRun)
            .options(selectinload(PipelineRun.tasks))
            .where(
                PipelineRun.id == run_id,
                PipelineRun.tenant_id == self.tenant_id,
            )
        )
        run = result.scalar_one_or_none()
        if not run:
            raise NotFoundError("PipelineRun", str(run_id))
        return run

    async def list_pipeline_runs(
        self,
        pipeline_id: UUID | None = None,
        status: PipelineStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[PipelineRun], int]:
        """List pipeline runs with filtering."""
        base_conditions = [PipelineRun.tenant_id == self.tenant_id]

        if pipeline_id:
            base_conditions.append(PipelineRun.pipeline_id == pipeline_id)

        if status:
            base_conditions.append(PipelineRun.status == status)

        count_query = select(func.count(PipelineRun.id)).where(and_(*base_conditions))
        total = (await self.session.execute(count_query)).scalar() or 0

        query = (
            select(PipelineRun)
            .where(and_(*base_conditions))
            .order_by(PipelineRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        runs = result.scalars().all()

        return runs, total

    async def update_run_status(
        self,
        run_id: UUID,
        status: PipelineStatus,
        error_message: str | None = None,
    ) -> PipelineRun:
        """Update pipeline run status."""
        run = await self.get_pipeline_run(run_id)

        if status == PipelineStatus.RUNNING and run.status == PipelineStatus.PENDING:
            run.start_time = datetime.now(timezone.utc)

        if status in (PipelineStatus.SUCCESS, PipelineStatus.FAILED, PipelineStatus.CANCELLED):
            run.end_time = datetime.now(timezone.utc)
            if error_message:
                run.error_message = error_message

        run.status = status
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def cancel_pipeline_run(self, run_id: UUID) -> PipelineRun:
        """Cancel a pipeline run."""
        run = await self.get_pipeline_run(run_id)

        if run.status not in (PipelineStatus.PENDING, PipelineStatus.RUNNING):
            raise ValidationError("Cannot cancel a completed pipeline run")

        return await self.update_run_status(run_id, PipelineStatus.CANCELLED)

    # ========================================================================
    # Pipeline Task Operations
    # ========================================================================

    async def get_pipeline_tasks(self, run_id: UUID) -> Sequence[PipelineTask]:
        """Get all tasks for a pipeline run."""
        await self.get_pipeline_run(run_id)

        result = await self.session.execute(
            select(PipelineTask)
            .where(
                PipelineTask.pipeline_run_id == run_id,
                PipelineTask.tenant_id == self.tenant_id,
            )
            .order_by(PipelineTask.created_at.asc())
        )
        return result.scalars().all()

    async def update_task_status(
        self,
        task_id: UUID,
        status: PipelineStatus,
        error_message: str | None = None,
        logs: str | None = None,
    ) -> PipelineTask:
        """Update pipeline task status."""
        result = await self.session.execute(
            select(PipelineTask).where(
                PipelineTask.id == task_id,
                PipelineTask.tenant_id == self.tenant_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError("PipelineTask", str(task_id))

        if status == PipelineStatus.RUNNING and task.status == PipelineStatus.PENDING:
            task.start_time = datetime.now(timezone.utc)

        if status in (PipelineStatus.SUCCESS, PipelineStatus.FAILED, PipelineStatus.CANCELLED):
            task.end_time = datetime.now(timezone.utc)

        task.status = status
        if error_message:
            task.error_message = error_message
        if logs:
            task.logs = logs

        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def get_last_run(self, pipeline_id: UUID) -> PipelineRun | None:
        """Get the most recent run for a pipeline."""
        result = await self.session.execute(
            select(PipelineRun)
            .where(
                PipelineRun.pipeline_id == pipeline_id,
                PipelineRun.tenant_id == self.tenant_id,
            )
            .order_by(PipelineRun.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
