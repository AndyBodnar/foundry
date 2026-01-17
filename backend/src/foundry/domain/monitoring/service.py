"""Monitoring service - business logic for drift detection and alerting."""

from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from foundry.core.exceptions import NotFoundError, ValidationError
from foundry.infrastructure.database.models import (
    AlertRule,
    Alert,
    Deployment,
    AlertSeverity,
    AlertCondition,
)
from foundry.domain.monitoring.schemas import (
    AlertRuleCreate,
    AlertRuleUpdate,
    DriftReportResponse,
    FeatureDriftScore,
    PerformanceReportResponse,
)


class MonitoringService:
    """Service for monitoring, drift detection, and alerting."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id

    # ========================================================================
    # Alert Rule Operations
    # ========================================================================

    async def create_alert_rule(
        self,
        data: AlertRuleCreate,
    ) -> AlertRule:
        """Create a new alert rule."""
        # Verify deployment exists if specified
        if data.deployment_id:
            await self._get_deployment(data.deployment_id)

        alert_rule = AlertRule(
            tenant_id=self.tenant_id,
            deployment_id=data.deployment_id,
            name=data.name,
            description=data.description,
            metric=data.metric,
            condition=data.condition,
            threshold=data.threshold,
            severity=data.severity,
            notification_channels=data.notification_channels,
            cooldown_minutes=data.cooldown_minutes,
            enabled=data.enabled,
        )
        self.session.add(alert_rule)
        await self.session.flush()
        await self.session.refresh(alert_rule)
        return alert_rule

    async def get_alert_rule(self, rule_id: UUID) -> AlertRule:
        """Get alert rule by ID."""
        result = await self.session.execute(
            select(AlertRule).where(
                AlertRule.id == rule_id,
                AlertRule.tenant_id == self.tenant_id,
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise NotFoundError("AlertRule", str(rule_id))
        return rule

    async def list_alert_rules(
        self,
        deployment_id: UUID | None = None,
        enabled_only: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[AlertRule], int]:
        """List alert rules with filtering."""
        base_conditions = [AlertRule.tenant_id == self.tenant_id]

        if deployment_id:
            base_conditions.append(AlertRule.deployment_id == deployment_id)

        if enabled_only:
            base_conditions.append(AlertRule.enabled == True)

        count_query = select(func.count(AlertRule.id)).where(and_(*base_conditions))
        total = (await self.session.execute(count_query)).scalar() or 0

        query = (
            select(AlertRule)
            .where(and_(*base_conditions))
            .order_by(AlertRule.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        rules = result.scalars().all()

        return rules, total

    async def update_alert_rule(
        self,
        rule_id: UUID,
        data: AlertRuleUpdate,
    ) -> AlertRule:
        """Update an alert rule."""
        rule = await self.get_alert_rule(rule_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(rule, field, value)

        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def delete_alert_rule(self, rule_id: UUID) -> None:
        """Delete an alert rule."""
        rule = await self.get_alert_rule(rule_id)
        await self.session.delete(rule)
        await self.session.flush()

    # ========================================================================
    # Alert Operations
    # ========================================================================

    async def create_alert(
        self,
        rule_id: UUID,
        metric_value: float,
        message: str,
    ) -> Alert:
        """Create a new alert (triggered by monitoring system)."""
        rule = await self.get_alert_rule(rule_id)

        alert = Alert(
            tenant_id=self.tenant_id,
            rule_id=rule_id,
            deployment_id=rule.deployment_id,
            severity=rule.severity,
            metric_value=metric_value,
            threshold_value=rule.threshold,
            message=message,
        )
        self.session.add(alert)

        # Update rule's last triggered timestamp
        rule.last_triggered_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def get_alert(self, alert_id: UUID) -> Alert:
        """Get alert by ID."""
        result = await self.session.execute(
            select(Alert).where(
                Alert.id == alert_id,
                Alert.tenant_id == self.tenant_id,
            )
        )
        alert = result.scalar_one_or_none()
        if not alert:
            raise NotFoundError("Alert", str(alert_id))
        return alert

    async def list_alerts(
        self,
        deployment_id: UUID | None = None,
        severity: AlertSeverity | None = None,
        acknowledged: bool | None = None,
        resolved: bool | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Alert], int]:
        """List alerts with filtering."""
        base_conditions = [Alert.tenant_id == self.tenant_id]

        if deployment_id:
            base_conditions.append(Alert.deployment_id == deployment_id)

        if severity:
            base_conditions.append(Alert.severity == severity)

        if acknowledged is not None:
            base_conditions.append(Alert.acknowledged == acknowledged)

        if resolved is not None:
            if resolved:
                base_conditions.append(Alert.resolved_at.isnot(None))
            else:
                base_conditions.append(Alert.resolved_at.is_(None))

        count_query = select(func.count(Alert.id)).where(and_(*base_conditions))
        total = (await self.session.execute(count_query)).scalar() or 0

        query = (
            select(Alert)
            .where(and_(*base_conditions))
            .order_by(Alert.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        alerts = result.scalars().all()

        return alerts, total

    async def acknowledge_alert(
        self,
        alert_id: UUID,
        user_id: UUID,
    ) -> Alert:
        """Acknowledge an alert."""
        alert = await self.get_alert(alert_id)

        if alert.acknowledged:
            raise ValidationError("Alert already acknowledged")

        alert.acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = user_id

        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def resolve_alert(self, alert_id: UUID) -> Alert:
        """Resolve an alert."""
        alert = await self.get_alert(alert_id)

        if alert.resolved_at:
            raise ValidationError("Alert already resolved")

        alert.resolved_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    # ========================================================================
    # Drift Detection Operations
    # ========================================================================

    async def get_drift_report(
        self,
        deployment_id: UUID,
    ) -> DriftReportResponse:
        """
        Get current drift report for a deployment.

        In a real implementation, this would:
        1. Fetch recent predictions from TimescaleDB
        2. Compare against baseline distributions
        3. Calculate drift scores using statistical tests

        For now, returns mock data.
        """
        await self._get_deployment(deployment_id)

        # Mock drift data
        feature_drifts = [
            FeatureDriftScore(
                feature_name="feature_1",
                drift_score=0.15,
                drift_method="ks_test",
                status="none",
                baseline_stats={"mean": 0.5, "std": 0.1},
                current_stats={"mean": 0.52, "std": 0.11},
            ),
            FeatureDriftScore(
                feature_name="feature_2",
                drift_score=0.35,
                drift_method="ks_test",
                status="warning",
                baseline_stats={"mean": 10.0, "std": 2.0},
                current_stats={"mean": 11.5, "std": 2.5},
            ),
        ]

        return DriftReportResponse(
            deployment_id=deployment_id,
            report_time=datetime.now(timezone.utc),
            overall_drift_score=0.25,
            overall_status="warning",
            feature_drifts=feature_drifts,
            prediction_drift=FeatureDriftScore(
                feature_name="prediction",
                drift_score=0.12,
                drift_method="psi",
                status="none",
                baseline_stats={"positive_rate": 0.3},
                current_stats={"positive_rate": 0.28},
            ),
            sample_count=10000,
            baseline_sample_count=50000,
        )

    async def check_drift_alerts(
        self,
        deployment_id: UUID,
        drift_report: DriftReportResponse,
    ) -> list[Alert]:
        """Check drift against alert rules and create alerts if needed."""
        # Get drift-related alert rules for this deployment
        result = await self.session.execute(
            select(AlertRule).where(
                AlertRule.tenant_id == self.tenant_id,
                AlertRule.deployment_id == deployment_id,
                AlertRule.enabled == True,
                AlertRule.metric.like("drift%"),
            )
        )
        rules = result.scalars().all()

        alerts_created = []

        for rule in rules:
            # Check if cooldown has passed
            if rule.last_triggered_at:
                cooldown_end = rule.last_triggered_at.replace(
                    minute=rule.last_triggered_at.minute + rule.cooldown_minutes
                )
                if datetime.now(timezone.utc) < cooldown_end:
                    continue

            # Check condition
            metric_value = drift_report.overall_drift_score
            triggered = self._check_condition(
                metric_value,
                rule.condition,
                rule.threshold,
            )

            if triggered:
                alert = await self.create_alert(
                    rule_id=rule.id,
                    metric_value=metric_value,
                    message=f"Drift alert: {rule.name} - score {metric_value:.3f} {rule.condition.value} {rule.threshold}",
                )
                alerts_created.append(alert)

        return alerts_created

    # ========================================================================
    # Performance Metrics Operations
    # ========================================================================

    async def get_performance_report(
        self,
        deployment_id: UUID,
    ) -> PerformanceReportResponse:
        """
        Get current performance report for a deployment.

        In a real implementation, this would calculate metrics from
        predictions with ground truth labels.
        """
        await self._get_deployment(deployment_id)

        # Mock performance data
        return PerformanceReportResponse(
            deployment_id=deployment_id,
            report_time=datetime.now(timezone.utc),
            metrics={
                "accuracy": 0.92,
                "precision": 0.89,
                "recall": 0.87,
                "f1_score": 0.88,
                "auc_roc": 0.95,
            },
            confusion_matrix=[[850, 50], [80, 420]],
            sample_count=1400,
        )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _get_deployment(self, deployment_id: UUID) -> Deployment:
        """Get and verify deployment exists."""
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

    def _check_condition(
        self,
        value: float,
        condition: AlertCondition,
        threshold: float,
    ) -> bool:
        """Check if a value meets an alert condition."""
        if condition == AlertCondition.GREATER_THAN:
            return value > threshold
        elif condition == AlertCondition.LESS_THAN:
            return value < threshold
        elif condition == AlertCondition.GREATER_THAN_OR_EQUAL:
            return value >= threshold
        elif condition == AlertCondition.LESS_THAN_OR_EQUAL:
            return value <= threshold
        elif condition == AlertCondition.EQUAL:
            return value == threshold
        elif condition == AlertCondition.NOT_EQUAL:
            return value != threshold
        return False
