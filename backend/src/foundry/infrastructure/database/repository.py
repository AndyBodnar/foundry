"""Base repository pattern for database operations."""

from typing import Any, Generic, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from foundry.infrastructure.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Base repository with common CRUD operations.

    Provides tenant-aware operations when applicable.
    """

    def __init__(self, session: AsyncSession, model: Type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def create(self, **kwargs: Any) -> ModelT:
        """Create a new entity."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(
        self,
        id: UUID,
        tenant_id: UUID | None = None,
    ) -> ModelT | None:
        """Get entity by ID, optionally filtered by tenant."""
        query = select(self.model).where(self.model.id == id)

        if tenant_id and hasattr(self.model, "tenant_id"):
            query = query.where(self.model.tenant_id == tenant_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_desc: bool = True,
    ) -> Sequence[ModelT]:
        """Get all entities with pagination."""
        query = self._build_base_query(tenant_id)
        query = self._apply_ordering(query, order_by, order_desc)
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, tenant_id: UUID | None = None) -> int:
        """Count total entities."""
        query = select(func.count(self.model.id))

        if tenant_id and hasattr(self.model, "tenant_id"):
            query = query.where(self.model.tenant_id == tenant_id)

        if hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def update_by_id(
        self,
        id: UUID,
        tenant_id: UUID | None = None,
        **kwargs: Any,
    ) -> ModelT | None:
        """Update entity by ID."""
        instance = await self.get_by_id(id, tenant_id)
        if instance is None:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete_by_id(
        self,
        id: UUID,
        tenant_id: UUID | None = None,
        soft_delete: bool = True,
    ) -> bool:
        """Delete entity by ID."""
        instance = await self.get_by_id(id, tenant_id)
        if instance is None:
            return False

        if soft_delete and hasattr(instance, "soft_delete"):
            instance.soft_delete()
        else:
            await self.session.delete(instance)

        await self.session.flush()
        return True

    async def exists(
        self,
        id: UUID,
        tenant_id: UUID | None = None,
    ) -> bool:
        """Check if entity exists."""
        query = select(func.count(self.model.id)).where(self.model.id == id)

        if tenant_id and hasattr(self.model, "tenant_id"):
            query = query.where(self.model.tenant_id == tenant_id)

        result = await self.session.execute(query)
        return (result.scalar() or 0) > 0

    def _build_base_query(self, tenant_id: UUID | None = None) -> Select:
        """Build base query with tenant filter and soft delete exclusion."""
        query = select(self.model)

        if tenant_id and hasattr(self.model, "tenant_id"):
            query = query.where(self.model.tenant_id == tenant_id)

        if hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))

        return query

    def _apply_ordering(
        self,
        query: Select,
        order_by: str | None,
        order_desc: bool,
    ) -> Select:
        """Apply ordering to query."""
        if order_by and hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            query = query.order_by(column.desc() if order_desc else column.asc())
        elif hasattr(self.model, "created_at"):
            column = self.model.created_at
            query = query.order_by(column.desc() if order_desc else column.asc())

        return query


class TenantAwareRepository(BaseRepository[ModelT]):
    """Repository that requires tenant context for all operations."""

    def __init__(
        self,
        session: AsyncSession,
        model: Type[ModelT],
        tenant_id: UUID,
    ) -> None:
        super().__init__(session, model)
        self.tenant_id = tenant_id

    async def create(self, **kwargs: Any) -> ModelT:
        """Create entity with tenant_id automatically set."""
        kwargs["tenant_id"] = self.tenant_id
        return await super().create(**kwargs)

    async def get_by_id(self, id: UUID, tenant_id: UUID | None = None) -> ModelT | None:
        """Get entity by ID with tenant enforcement."""
        return await super().get_by_id(id, self.tenant_id)

    async def get_all(
        self,
        tenant_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_desc: bool = True,
    ) -> Sequence[ModelT]:
        """Get all entities for the tenant."""
        return await super().get_all(
            tenant_id=self.tenant_id,
            offset=offset,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc,
        )

    async def count(self, tenant_id: UUID | None = None) -> int:
        """Count entities for the tenant."""
        return await super().count(self.tenant_id)

    async def update_by_id(
        self,
        id: UUID,
        tenant_id: UUID | None = None,
        **kwargs: Any,
    ) -> ModelT | None:
        """Update entity with tenant enforcement."""
        return await super().update_by_id(id, self.tenant_id, **kwargs)

    async def delete_by_id(
        self,
        id: UUID,
        tenant_id: UUID | None = None,
        soft_delete: bool = True,
    ) -> bool:
        """Delete entity with tenant enforcement."""
        return await super().delete_by_id(id, self.tenant_id, soft_delete)

    async def exists(self, id: UUID, tenant_id: UUID | None = None) -> bool:
        """Check if entity exists within tenant."""
        return await super().exists(id, self.tenant_id)
