"""Model Registry service - business logic for model versioning."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from foundry.core.exceptions import (
    NotFoundError,
    ConflictError,
    ModelStageTransitionError,
)
from foundry.infrastructure.database.models import (
    RegisteredModel,
    ModelVersion,
    StageTransition,
    ModelStage,
    Run,
    Experiment,
    Artifact,
)
from foundry.domain.registry.schemas import (
    ModelCreate,
    ModelUpdate,
    ModelVersionCreate,
    StageTransitionRequest,
    ModelLineageResponse,
    RunSummary,
)


# Valid stage transitions
VALID_TRANSITIONS: dict[ModelStage, set[ModelStage]] = {
    ModelStage.NONE: {ModelStage.STAGING, ModelStage.ARCHIVED},
    ModelStage.STAGING: {ModelStage.PRODUCTION, ModelStage.ARCHIVED, ModelStage.NONE},
    ModelStage.PRODUCTION: {ModelStage.STAGING, ModelStage.ARCHIVED},
    ModelStage.ARCHIVED: {ModelStage.NONE, ModelStage.STAGING},
}


class RegistryService:
    """Service for model registry management."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id

    # ========================================================================
    # Model Operations
    # ========================================================================

    async def create_model(
        self,
        data: ModelCreate,
        owner_id: UUID | None = None,
    ) -> RegisteredModel:
        """Create a new registered model."""
        # Check for duplicate name
        existing = await self.session.execute(
            select(RegisteredModel).where(
                RegisteredModel.tenant_id == self.tenant_id,
                RegisteredModel.name == data.name,
                RegisteredModel.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                "Model",
                f"Model with name '{data.name}' already exists",
            )

        model = RegisteredModel(
            tenant_id=self.tenant_id,
            name=data.name,
            description=data.description,
            tags=data.tags,
            owner_id=owner_id,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def get_model(self, model_id: UUID) -> RegisteredModel:
        """Get model by ID."""
        result = await self.session.execute(
            select(RegisteredModel).where(
                RegisteredModel.id == model_id,
                RegisteredModel.tenant_id == self.tenant_id,
                RegisteredModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            raise NotFoundError("Model", str(model_id))
        return model

    async def get_model_by_name(self, name: str) -> RegisteredModel:
        """Get model by name."""
        result = await self.session.execute(
            select(RegisteredModel).where(
                RegisteredModel.tenant_id == self.tenant_id,
                RegisteredModel.name == name,
                RegisteredModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            raise NotFoundError("Model", name)
        return model

    async def list_models(
        self,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        tags: list[str] | None = None,
    ) -> tuple[Sequence[RegisteredModel], int]:
        """List models with pagination and filtering."""
        base_conditions = [
            RegisteredModel.tenant_id == self.tenant_id,
            RegisteredModel.deleted_at.is_(None),
        ]

        if search:
            base_conditions.append(RegisteredModel.name.ilike(f"%{search}%"))

        if tags:
            base_conditions.append(RegisteredModel.tags.contains(tags))

        # Get total count
        count_query = select(func.count(RegisteredModel.id)).where(
            and_(*base_conditions)
        )
        total = (await self.session.execute(count_query)).scalar() or 0

        # Get models
        query = (
            select(RegisteredModel)
            .where(and_(*base_conditions))
            .order_by(RegisteredModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        models = result.scalars().all()

        return models, total

    async def update_model(
        self,
        name: str,
        data: ModelUpdate,
    ) -> RegisteredModel:
        """Update a model."""
        model = await self.get_model_by_name(name)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(model, field, value)

        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete_model(self, name: str) -> None:
        """Soft delete a model."""
        model = await self.get_model_by_name(name)
        model.soft_delete()
        await self.session.flush()

    async def get_model_version_count(self, model_id: UUID) -> int:
        """Get the number of versions for a model."""
        result = await self.session.execute(
            select(func.count(ModelVersion.id)).where(
                ModelVersion.model_id == model_id,
                ModelVersion.tenant_id == self.tenant_id,
            )
        )
        return result.scalar() or 0

    async def get_latest_version(self, model_id: UUID) -> ModelVersion | None:
        """Get the latest version of a model."""
        result = await self.session.execute(
            select(ModelVersion)
            .where(
                ModelVersion.model_id == model_id,
                ModelVersion.tenant_id == self.tenant_id,
            )
            .order_by(ModelVersion.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_production_version(self, model_id: UUID) -> ModelVersion | None:
        """Get the production version of a model."""
        result = await self.session.execute(
            select(ModelVersion).where(
                ModelVersion.model_id == model_id,
                ModelVersion.tenant_id == self.tenant_id,
                ModelVersion.stage == ModelStage.PRODUCTION,
            )
        )
        return result.scalar_one_or_none()

    # ========================================================================
    # Model Version Operations
    # ========================================================================

    async def create_version(
        self,
        model_name: str,
        data: ModelVersionCreate,
    ) -> ModelVersion:
        """Create a new model version."""
        model = await self.get_model_by_name(model_name)

        # Check for duplicate version
        existing = await self.session.execute(
            select(ModelVersion).where(
                ModelVersion.model_id == model.id,
                ModelVersion.version == data.version,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                "ModelVersion",
                f"Version '{data.version}' already exists for model '{model_name}'",
            )

        version = ModelVersion(
            tenant_id=self.tenant_id,
            model_id=model.id,
            version=data.version,
            stage=ModelStage.NONE,
            artifact_path=data.artifact_path,
            run_id=data.run_id,
            metrics=data.metrics,
            signature=data.signature.model_dump() if data.signature else None,
            description=data.description,
        )
        self.session.add(version)
        await self.session.flush()
        await self.session.refresh(version)
        return version

    async def get_version(
        self,
        model_name: str,
        version: str,
    ) -> ModelVersion:
        """Get a specific model version."""
        model = await self.get_model_by_name(model_name)

        result = await self.session.execute(
            select(ModelVersion).where(
                ModelVersion.model_id == model.id,
                ModelVersion.version == version,
                ModelVersion.tenant_id == self.tenant_id,
            )
        )
        model_version = result.scalar_one_or_none()
        if not model_version:
            raise NotFoundError("ModelVersion", f"{model_name}:{version}")
        return model_version

    async def get_version_by_id(self, version_id: UUID) -> ModelVersion:
        """Get model version by ID."""
        result = await self.session.execute(
            select(ModelVersion).where(
                ModelVersion.id == version_id,
                ModelVersion.tenant_id == self.tenant_id,
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            raise NotFoundError("ModelVersion", str(version_id))
        return version

    async def list_versions(
        self,
        model_name: str,
        offset: int = 0,
        limit: int = 100,
        stage: ModelStage | None = None,
    ) -> tuple[Sequence[ModelVersion], int]:
        """List versions for a model."""
        model = await self.get_model_by_name(model_name)

        base_conditions = [
            ModelVersion.model_id == model.id,
            ModelVersion.tenant_id == self.tenant_id,
        ]

        if stage:
            base_conditions.append(ModelVersion.stage == stage)

        # Get total count
        count_query = select(func.count(ModelVersion.id)).where(
            and_(*base_conditions)
        )
        total = (await self.session.execute(count_query)).scalar() or 0

        # Get versions
        query = (
            select(ModelVersion)
            .where(and_(*base_conditions))
            .order_by(ModelVersion.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        versions = result.scalars().all()

        return versions, total

    # ========================================================================
    # Stage Transition Operations
    # ========================================================================

    async def transition_stage(
        self,
        model_name: str,
        version: str,
        data: StageTransitionRequest,
        user_id: UUID | None = None,
    ) -> ModelVersion:
        """Transition a model version to a new stage."""
        model_version = await self.get_version(model_name, version)

        # Validate transition
        if data.stage not in VALID_TRANSITIONS.get(model_version.stage, set()):
            raise ModelStageTransitionError(
                current_stage=model_version.stage.value,
                target_stage=data.stage.value,
            )

        # Archive existing versions in target stage if requested
        if data.archive_existing_versions and data.stage in (
            ModelStage.STAGING,
            ModelStage.PRODUCTION,
        ):
            await self._archive_versions_in_stage(model_version.model_id, data.stage)

        # Record transition
        transition = StageTransition(
            tenant_id=self.tenant_id,
            model_version_id=model_version.id,
            from_stage=model_version.stage,
            to_stage=data.stage,
            user_id=user_id,
            comment=data.comment,
        )
        self.session.add(transition)

        # Update version stage
        model_version.stage = data.stage

        await self.session.flush()
        await self.session.refresh(model_version)
        return model_version

    async def _archive_versions_in_stage(
        self,
        model_id: UUID,
        stage: ModelStage,
    ) -> None:
        """Archive all versions currently in a stage."""
        result = await self.session.execute(
            select(ModelVersion).where(
                ModelVersion.model_id == model_id,
                ModelVersion.stage == stage,
                ModelVersion.tenant_id == self.tenant_id,
            )
        )
        versions = result.scalars().all()

        for version in versions:
            version.stage = ModelStage.ARCHIVED

    async def get_stage_history(
        self,
        model_name: str,
        version: str,
    ) -> Sequence[StageTransition]:
        """Get stage transition history for a version."""
        model_version = await self.get_version(model_name, version)

        result = await self.session.execute(
            select(StageTransition)
            .where(
                StageTransition.model_version_id == model_version.id,
                StageTransition.tenant_id == self.tenant_id,
            )
            .order_by(StageTransition.created_at.desc())
        )
        return result.scalars().all()

    # ========================================================================
    # Lineage Operations
    # ========================================================================

    async def get_lineage(
        self,
        model_name: str,
        version: str,
    ) -> ModelLineageResponse:
        """Get lineage information for a model version."""
        model = await self.get_model_by_name(model_name)
        model_version = await self.get_version(model_name, version)

        run_summary = None
        artifacts: list[dict] = []

        if model_version.run_id:
            # Get run details
            run_result = await self.session.execute(
                select(Run)
                .options(selectinload(Run.experiment))
                .where(
                    Run.id == model_version.run_id,
                    Run.tenant_id == self.tenant_id,
                )
            )
            run = run_result.scalar_one_or_none()

            if run:
                # Get experiment name
                exp_result = await self.session.execute(
                    select(Experiment).where(Experiment.id == run.experiment_id)
                )
                experiment = exp_result.scalar_one_or_none()

                run_summary = RunSummary(
                    id=run.id,
                    experiment_id=run.experiment_id,
                    experiment_name=experiment.name if experiment else "Unknown",
                    parameters=run.parameters,
                    metrics=run.metrics,
                )

                # Get artifacts from the run
                artifact_result = await self.session.execute(
                    select(Artifact).where(
                        Artifact.run_id == run.id,
                        Artifact.tenant_id == self.tenant_id,
                    )
                )
                for artifact in artifact_result.scalars().all():
                    artifacts.append({
                        "id": str(artifact.id),
                        "name": artifact.name,
                        "type": artifact.artifact_type,
                        "path": artifact.path,
                    })

        return ModelLineageResponse(
            model_version_id=model_version.id,
            model_name=model.name,
            version=model_version.version,
            run=run_summary,
            artifacts=artifacts,
            parent_versions=[],  # Could be extended to track model derivation
        )
