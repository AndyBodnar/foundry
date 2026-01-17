"""Deployment service - business logic for model deployment and A/B testing."""

from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from foundry.core.exceptions import (
    NotFoundError,
    ConflictError,
    ValidationError,
    DeploymentError,
)
from foundry.infrastructure.database.models import (
    Deployment,
    ABTest,
    ModelVersion,
    DeploymentStatus,
    ABTestStatus,
)
from foundry.domain.deployments.schemas import (
    DeploymentCreate,
    DeploymentUpdate,
    TrafficConfigUpdate,
    ABTestCreate,
    ABTestCompleteRequest,
    RollbackRequest,
    DeploymentHealthResponse,
)


class DeploymentService:
    """Service for deployment management."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id

    # ========================================================================
    # Deployment Operations
    # ========================================================================

    async def create_deployment(
        self,
        data: DeploymentCreate,
        owner_id: UUID | None = None,
    ) -> Deployment:
        """Create a new deployment."""
        # Check for duplicate name
        existing = await self.session.execute(
            select(Deployment).where(
                Deployment.tenant_id == self.tenant_id,
                Deployment.name == data.name,
                Deployment.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                "Deployment",
                f"Deployment with name '{data.name}' already exists",
            )

        # Verify model version exists
        await self._get_model_version(data.model_version_id)

        # Build traffic config
        traffic_config = {
            "versions": [
                {"version_id": str(data.model_version_id), "weight": 100}
            ]
        }

        deployment = Deployment(
            tenant_id=self.tenant_id,
            name=data.name,
            description=data.description,
            status=DeploymentStatus.PENDING,
            config=data.config.model_dump(),
            traffic_config=traffic_config,
            model_version_id=data.model_version_id,
            replicas=data.replicas,
            min_replicas=data.min_replicas,
            max_replicas=data.max_replicas,
            owner_id=owner_id,
        )
        self.session.add(deployment)
        await self.session.flush()
        await self.session.refresh(deployment)
        return deployment

    async def get_deployment(self, deployment_id: UUID) -> Deployment:
        """Get deployment by ID."""
        result = await self.session.execute(
            select(Deployment).where(
                Deployment.id == deployment_id,
                Deployment.tenant_id == self.tenant_id,
                Deployment.deleted_at.is_(None),
            )
        )
        deployment = result.scalar_one_or_none()
        if not deployment:
            raise NotFoundError("Deployment", str(deployment_id))
        return deployment

    async def get_deployment_by_name(self, name: str) -> Deployment:
        """Get deployment by name."""
        result = await self.session.execute(
            select(Deployment).where(
                Deployment.tenant_id == self.tenant_id,
                Deployment.name == name,
                Deployment.deleted_at.is_(None),
            )
        )
        deployment = result.scalar_one_or_none()
        if not deployment:
            raise NotFoundError("Deployment", name)
        return deployment

    async def list_deployments(
        self,
        offset: int = 0,
        limit: int = 100,
        status: DeploymentStatus | None = None,
    ) -> tuple[Sequence[Deployment], int]:
        """List deployments with pagination and filtering."""
        base_conditions = [
            Deployment.tenant_id == self.tenant_id,
            Deployment.deleted_at.is_(None),
        ]

        if status:
            base_conditions.append(Deployment.status == status)

        # Get total count
        count_query = select(func.count(Deployment.id)).where(
            and_(*base_conditions)
        )
        total = (await self.session.execute(count_query)).scalar() or 0

        # Get deployments
        query = (
            select(Deployment)
            .where(and_(*base_conditions))
            .order_by(Deployment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        deployments = result.scalars().all()

        return deployments, total

    async def update_deployment(
        self,
        deployment_id: UUID,
        data: DeploymentUpdate,
    ) -> Deployment:
        """Update a deployment."""
        deployment = await self.get_deployment(deployment_id)

        # Don't allow updates if deployment is being modified
        if deployment.status in (DeploymentStatus.DEPLOYING, DeploymentStatus.ROLLING_BACK):
            raise DeploymentError(
                "Cannot update deployment while it is being modified",
                deployment_id=str(deployment_id),
            )

        update_data = data.model_dump(exclude_unset=True)

        # Handle config update
        if "config" in update_data and update_data["config"]:
            deployment.config = update_data.pop("config").model_dump()

        for field, value in update_data.items():
            if value is not None:
                setattr(deployment, field, value)

        await self.session.flush()
        await self.session.refresh(deployment)
        return deployment

    async def delete_deployment(self, deployment_id: UUID) -> None:
        """Soft delete a deployment."""
        deployment = await self.get_deployment(deployment_id)

        # Stop deployment first
        if deployment.status == DeploymentStatus.ACTIVE:
            deployment.status = DeploymentStatus.STOPPED

        deployment.soft_delete()
        await self.session.flush()

    async def update_traffic(
        self,
        deployment_id: UUID,
        data: TrafficConfigUpdate,
    ) -> Deployment:
        """Update traffic configuration."""
        deployment = await self.get_deployment(deployment_id)

        # Verify all model versions exist
        for traffic in data.traffic:
            await self._get_model_version(traffic.model_version_id)

        # Build traffic config
        traffic_config = {
            "versions": [
                {"version_id": str(t.model_version_id), "weight": t.weight}
                for t in data.traffic
            ]
        }

        deployment.traffic_config = traffic_config
        await self.session.flush()
        await self.session.refresh(deployment)
        return deployment

    async def rollback(
        self,
        deployment_id: UUID,
        data: RollbackRequest,
    ) -> Deployment:
        """Rollback a deployment to a previous version."""
        deployment = await self.get_deployment(deployment_id)

        if deployment.status == DeploymentStatus.ROLLING_BACK:
            raise DeploymentError(
                "Deployment is already rolling back",
                deployment_id=str(deployment_id),
            )

        if data.target_version_id:
            # Verify target version exists
            await self._get_model_version(data.target_version_id)
            target_version_id = data.target_version_id
        else:
            # Get previous version from traffic config
            # This is a simplified implementation
            raise ValidationError("Automatic rollback not implemented. Please specify target_version_id.")

        deployment.status = DeploymentStatus.ROLLING_BACK
        deployment.model_version_id = target_version_id
        deployment.traffic_config = {
            "versions": [{"version_id": str(target_version_id), "weight": 100}]
        }

        await self.session.flush()
        await self.session.refresh(deployment)
        return deployment

    async def get_health(self, deployment_id: UUID) -> DeploymentHealthResponse:
        """Get deployment health status."""
        deployment = await self.get_deployment(deployment_id)

        # In a real implementation, this would query Kubernetes
        # For now, return mock health data
        return DeploymentHealthResponse(
            deployment_id=deployment.id,
            status=deployment.status,
            healthy=deployment.status == DeploymentStatus.ACTIVE,
            replicas_ready=deployment.replicas if deployment.status == DeploymentStatus.ACTIVE else 0,
            replicas_desired=deployment.replicas,
            last_check=datetime.now(timezone.utc),
            metrics={
                "requests_per_second": 0,
                "avg_latency_ms": 0,
                "error_rate": 0,
            },
        )

    async def update_status(
        self,
        deployment_id: UUID,
        status: DeploymentStatus,
        endpoint_url: str | None = None,
    ) -> Deployment:
        """Update deployment status (called by deployment controller)."""
        deployment = await self.get_deployment(deployment_id)
        deployment.status = status
        if endpoint_url:
            deployment.endpoint_url = endpoint_url
        await self.session.flush()
        await self.session.refresh(deployment)
        return deployment

    # ========================================================================
    # A/B Test Operations
    # ========================================================================

    async def create_ab_test(
        self,
        deployment_id: UUID,
        data: ABTestCreate,
    ) -> ABTest:
        """Create a new A/B test."""
        deployment = await self.get_deployment(deployment_id)

        if deployment.status != DeploymentStatus.ACTIVE:
            raise DeploymentError(
                "Cannot create A/B test on inactive deployment",
                deployment_id=str(deployment_id),
            )

        # Verify model versions
        await self._get_model_version(data.control_version_id)
        await self._get_model_version(data.treatment_version_id)

        if data.control_version_id == data.treatment_version_id:
            raise ValidationError("Control and treatment versions must be different")

        treatment_traffic = 100 - data.control_traffic_percent

        ab_test = ABTest(
            tenant_id=self.tenant_id,
            deployment_id=deployment_id,
            name=data.name,
            status=ABTestStatus.RUNNING,
            control_version_id=data.control_version_id,
            treatment_version_id=data.treatment_version_id,
            control_traffic_percent=data.control_traffic_percent,
            treatment_traffic_percent=treatment_traffic,
            start_time=datetime.now(timezone.utc),
            metrics={},
        )
        self.session.add(ab_test)

        # Update deployment traffic config
        deployment.traffic_config = {
            "versions": [
                {"version_id": str(data.control_version_id), "weight": data.control_traffic_percent},
                {"version_id": str(data.treatment_version_id), "weight": treatment_traffic},
            ]
        }

        await self.session.flush()
        await self.session.refresh(ab_test)
        return ab_test

    async def get_ab_test(self, test_id: UUID) -> ABTest:
        """Get A/B test by ID."""
        result = await self.session.execute(
            select(ABTest).where(
                ABTest.id == test_id,
                ABTest.tenant_id == self.tenant_id,
            )
        )
        ab_test = result.scalar_one_or_none()
        if not ab_test:
            raise NotFoundError("ABTest", str(test_id))
        return ab_test

    async def list_ab_tests(
        self,
        deployment_id: UUID,
        status: ABTestStatus | None = None,
    ) -> tuple[Sequence[ABTest], int]:
        """List A/B tests for a deployment."""
        base_conditions = [
            ABTest.deployment_id == deployment_id,
            ABTest.tenant_id == self.tenant_id,
        ]

        if status:
            base_conditions.append(ABTest.status == status)

        count_query = select(func.count(ABTest.id)).where(and_(*base_conditions))
        total = (await self.session.execute(count_query)).scalar() or 0

        query = (
            select(ABTest)
            .where(and_(*base_conditions))
            .order_by(ABTest.created_at.desc())
        )
        result = await self.session.execute(query)
        tests = result.scalars().all()

        return tests, total

    async def complete_ab_test(
        self,
        test_id: UUID,
        data: ABTestCompleteRequest,
    ) -> ABTest:
        """Complete an A/B test and optionally apply winner."""
        ab_test = await self.get_ab_test(test_id)

        if ab_test.status != ABTestStatus.RUNNING:
            raise ValidationError("A/B test is not running")

        # Verify winner is one of the test versions
        if data.winner_version_id not in (ab_test.control_version_id, ab_test.treatment_version_id):
            raise ValidationError("Winner must be either control or treatment version")

        ab_test.status = ABTestStatus.COMPLETED
        ab_test.end_time = datetime.now(timezone.utc)
        ab_test.winner_version_id = data.winner_version_id

        if data.apply_winner:
            # Update deployment to use winner
            deployment = await self.get_deployment(ab_test.deployment_id)
            deployment.model_version_id = data.winner_version_id
            deployment.traffic_config = {
                "versions": [{"version_id": str(data.winner_version_id), "weight": 100}]
            }

        await self.session.flush()
        await self.session.refresh(ab_test)
        return ab_test

    async def cancel_ab_test(self, test_id: UUID) -> ABTest:
        """Cancel an A/B test."""
        ab_test = await self.get_ab_test(test_id)

        if ab_test.status != ABTestStatus.RUNNING:
            raise ValidationError("A/B test is not running")

        ab_test.status = ABTestStatus.CANCELLED
        ab_test.end_time = datetime.now(timezone.utc)

        # Revert deployment to control version
        deployment = await self.get_deployment(ab_test.deployment_id)
        deployment.model_version_id = ab_test.control_version_id
        deployment.traffic_config = {
            "versions": [{"version_id": str(ab_test.control_version_id), "weight": 100}]
        }

        await self.session.flush()
        await self.session.refresh(ab_test)
        return ab_test

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _get_model_version(self, version_id: UUID) -> ModelVersion:
        """Get and verify model version exists."""
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
