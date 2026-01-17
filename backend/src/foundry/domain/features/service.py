"""Feature service - business logic for feature store management."""

from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from foundry.core.exceptions import NotFoundError, ConflictError
from foundry.infrastructure.database.models import FeatureView
from foundry.infrastructure.cache.redis import RedisCache
from foundry.domain.features.schemas import (
    FeatureViewCreate,
    FeatureViewUpdate,
    FeatureValueRequest,
    FeatureValueResponse,
    FeatureValue,
    EntityKey,
)


class FeatureService:
    """Service for feature store management."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        cache: RedisCache | None = None,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.cache = cache

    # ========================================================================
    # Feature View Operations
    # ========================================================================

    async def create_feature_view(
        self,
        data: FeatureViewCreate,
        owner_id: UUID | None = None,
    ) -> FeatureView:
        """Create a new feature view."""
        # Check for duplicate name
        existing = await self.session.execute(
            select(FeatureView).where(
                FeatureView.tenant_id == self.tenant_id,
                FeatureView.name == data.name,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                "FeatureView",
                f"Feature view with name '{data.name}' already exists",
            )

        # Convert features to dict format
        features_dict = {
            f.name: {
                "dtype": f.dtype,
                "description": f.description,
                "default_value": f.default_value,
            }
            for f in data.features
        }

        feature_view = FeatureView(
            tenant_id=self.tenant_id,
            name=data.name,
            description=data.description,
            entities=data.entities,
            features=features_dict,
            source_config=data.source_config.model_dump(),
            ttl_seconds=data.ttl_seconds,
            online_enabled=data.online_enabled,
            offline_enabled=data.offline_enabled,
            owner_id=owner_id,
        )
        self.session.add(feature_view)
        await self.session.flush()
        await self.session.refresh(feature_view)
        return feature_view

    async def get_feature_view(self, feature_view_id: UUID) -> FeatureView:
        """Get feature view by ID."""
        result = await self.session.execute(
            select(FeatureView).where(
                FeatureView.id == feature_view_id,
                FeatureView.tenant_id == self.tenant_id,
            )
        )
        fv = result.scalar_one_or_none()
        if not fv:
            raise NotFoundError("FeatureView", str(feature_view_id))
        return fv

    async def get_feature_view_by_name(self, name: str) -> FeatureView:
        """Get feature view by name."""
        result = await self.session.execute(
            select(FeatureView).where(
                FeatureView.tenant_id == self.tenant_id,
                FeatureView.name == name,
            )
        )
        fv = result.scalar_one_or_none()
        if not fv:
            raise NotFoundError("FeatureView", name)
        return fv

    async def list_feature_views(
        self,
        offset: int = 0,
        limit: int = 100,
        online_only: bool = False,
    ) -> tuple[Sequence[FeatureView], int]:
        """List feature views with pagination."""
        base_conditions = [FeatureView.tenant_id == self.tenant_id]

        if online_only:
            base_conditions.append(FeatureView.online_enabled == True)

        count_query = select(func.count(FeatureView.id)).where(and_(*base_conditions))
        total = (await self.session.execute(count_query)).scalar() or 0

        query = (
            select(FeatureView)
            .where(and_(*base_conditions))
            .order_by(FeatureView.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        feature_views = result.scalars().all()

        return feature_views, total

    async def update_feature_view(
        self,
        feature_view_id: UUID,
        data: FeatureViewUpdate,
    ) -> FeatureView:
        """Update a feature view."""
        fv = await self.get_feature_view(feature_view_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(fv, field, value)

        await self.session.flush()
        await self.session.refresh(fv)
        return fv

    async def delete_feature_view(self, feature_view_id: UUID) -> None:
        """Delete a feature view."""
        fv = await self.get_feature_view(feature_view_id)
        await self.session.delete(fv)
        await self.session.flush()

    # ========================================================================
    # Online Feature Serving
    # ========================================================================

    async def get_online_features(
        self,
        data: FeatureValueRequest,
    ) -> FeatureValueResponse:
        """
        Get online feature values from Redis cache.

        This is the hot path for real-time feature serving.
        """
        fv = await self.get_feature_view_by_name(data.feature_view)

        if not fv.online_enabled:
            raise NotFoundError(
                "FeatureView",
                f"Feature view '{data.feature_view}' is not enabled for online serving",
            )

        # Determine which features to fetch
        feature_names = data.features or list(fv.features.keys())

        results = []
        for entity in data.entities:
            entity_key = f"{entity.entity_type}:{entity.entity_id}"

            if self.cache:
                # Try to get from cache
                cache_key = f"fv:{self.tenant_id}:{data.feature_view}:{entity_key}"
                cached_values = await self.cache.hmget(cache_key, feature_names)

                if cached_values:
                    results.append(FeatureValue(
                        entity_key=entity,
                        values=cached_values,
                        timestamp=datetime.now(timezone.utc),
                    ))
                else:
                    # Return default values if not in cache
                    default_values = self._get_default_values(fv, feature_names)
                    results.append(FeatureValue(
                        entity_key=entity,
                        values=default_values,
                        timestamp=None,
                    ))
            else:
                # No cache configured, return defaults
                default_values = self._get_default_values(fv, feature_names)
                results.append(FeatureValue(
                    entity_key=entity,
                    values=default_values,
                    timestamp=None,
                ))

        return FeatureValueResponse(
            feature_view=data.feature_view,
            results=results,
            metadata={"source": "online" if self.cache else "default"},
        )

    async def push_online_features(
        self,
        feature_view: str,
        entity: EntityKey,
        values: dict[str, Any],
    ) -> None:
        """
        Push feature values to online store (Redis).

        Used by materialization jobs and streaming ingestion.
        """
        if not self.cache:
            return

        fv = await self.get_feature_view_by_name(feature_view)

        if not fv.online_enabled:
            return

        entity_key = f"{entity.entity_type}:{entity.entity_id}"
        cache_key = f"fv:{self.tenant_id}:{feature_view}:{entity_key}"

        # Add timestamp
        values["_updated_at"] = datetime.now(timezone.utc).isoformat()

        await self.cache.hmset(cache_key, values, ttl=fv.ttl_seconds)

    async def delete_online_features(
        self,
        feature_view: str,
        entity: EntityKey,
    ) -> None:
        """Delete feature values from online store."""
        if not self.cache:
            return

        entity_key = f"{entity.entity_type}:{entity.entity_id}"
        cache_key = f"fv:{self.tenant_id}:{feature_view}:{entity_key}"
        await self.cache.delete(cache_key)

    def _get_default_values(
        self,
        fv: FeatureView,
        feature_names: list[str],
    ) -> dict[str, Any]:
        """Get default values for features."""
        defaults = {}
        for name in feature_names:
            if name in fv.features:
                feature_def = fv.features[name]
                defaults[name] = feature_def.get("default_value")
            else:
                defaults[name] = None
        return defaults

    # ========================================================================
    # Feature Freshness & Metadata
    # ========================================================================

    async def get_freshness(self, feature_view: str) -> dict[str, Any]:
        """Get freshness metadata for a feature view."""
        fv = await self.get_feature_view_by_name(feature_view)

        if self.cache:
            meta_key = f"fv_meta:{self.tenant_id}:{feature_view}:freshness"
            meta = await self.cache.hgetall(meta_key)
            return {
                "feature_view": feature_view,
                "last_updated": meta.get("last_updated"),
                "record_count": meta.get("record_count"),
                "ttl_seconds": fv.ttl_seconds,
            }

        return {
            "feature_view": feature_view,
            "last_updated": None,
            "record_count": None,
            "ttl_seconds": fv.ttl_seconds,
        }

    async def update_freshness(
        self,
        feature_view: str,
        record_count: int,
    ) -> None:
        """Update freshness metadata after materialization."""
        if not self.cache:
            return

        meta_key = f"fv_meta:{self.tenant_id}:{feature_view}:freshness"
        await self.cache.hmset(meta_key, {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "record_count": str(record_count),
        })
