"""Tenant service - business logic for tenant management."""

from datetime import datetime, timedelta, timezone
from typing import Sequence
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from foundry.core.exceptions import (
    NotFoundError,
    ConflictError,
    AuthenticationError,
    AuthorizationError,
)
from foundry.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_api_key,
)
from foundry.infrastructure.database.models import (
    Tenant,
    User,
    TenantMembership,
    APIKey,
    TenantStatus,
    UserRole,
)
from foundry.domain.tenants.schemas import (
    TenantCreate,
    TenantUpdate,
    UserCreate,
    UserUpdate,
    MembershipCreate,
    APIKeyCreate,
    TokenResponse,
)
from foundry.config import settings


class TenantService:
    """Service for tenant and user management."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ========================================================================
    # Tenant Operations
    # ========================================================================

    async def create_tenant(self, data: TenantCreate) -> Tenant:
        """Create a new tenant."""
        # Check for duplicate slug
        existing = await self.session.execute(
            select(Tenant).where(Tenant.slug == data.slug)
        )
        if existing.scalar_one_or_none():
            raise ConflictError("Tenant", f"Tenant with slug '{data.slug}' already exists")

        tenant = Tenant(
            name=data.name,
            slug=data.slug,
            settings=data.settings,
            quotas=data.quotas,
        )
        self.session.add(tenant)
        await self.session.flush()
        await self.session.refresh(tenant)
        return tenant

    async def get_tenant(self, tenant_id: UUID) -> Tenant:
        """Get tenant by ID."""
        result = await self.session.execute(
            select(Tenant).where(
                Tenant.id == tenant_id,
                Tenant.status != TenantStatus.DELETED,
            )
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise NotFoundError("Tenant", str(tenant_id))
        return tenant

    async def get_tenant_by_slug(self, slug: str) -> Tenant:
        """Get tenant by slug."""
        result = await self.session.execute(
            select(Tenant).where(
                Tenant.slug == slug,
                Tenant.status != TenantStatus.DELETED,
            )
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise NotFoundError("Tenant", slug)
        return tenant

    async def list_tenants(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Tenant], int]:
        """List all tenants with pagination."""
        # Get total count
        count_query = select(func.count(Tenant.id)).where(
            Tenant.status != TenantStatus.DELETED
        )
        total = (await self.session.execute(count_query)).scalar() or 0

        # Get tenants
        query = (
            select(Tenant)
            .where(Tenant.status != TenantStatus.DELETED)
            .order_by(Tenant.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        tenants = result.scalars().all()

        return tenants, total

    async def update_tenant(
        self,
        tenant_id: UUID,
        data: TenantUpdate,
    ) -> Tenant:
        """Update a tenant."""
        tenant = await self.get_tenant(tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)

        await self.session.flush()
        await self.session.refresh(tenant)
        return tenant

    async def delete_tenant(self, tenant_id: UUID) -> None:
        """Soft delete a tenant."""
        tenant = await self.get_tenant(tenant_id)
        tenant.status = TenantStatus.DELETED
        await self.session.flush()

    # ========================================================================
    # User Operations
    # ========================================================================

    async def create_user(self, data: UserCreate) -> User:
        """Create a new user."""
        # Check for duplicate email
        existing = await self.session.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise ConflictError("User", f"User with email '{data.email}' already exists")

        user = User(
            email=data.email,
            name=data.name,
            hashed_password=hash_password(data.password),
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_user(self, user_id: UUID) -> User:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User", str(user_id))
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def list_users(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[User], int]:
        """List all users with pagination."""
        count_query = select(func.count(User.id))
        total = (await self.session.execute(count_query)).scalar() or 0

        query = (
            select(User)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        users = result.scalars().all()

        return users, total

    async def update_user(
        self,
        user_id: UUID,
        data: UserUpdate,
    ) -> User:
        """Update a user."""
        user = await self.get_user(user_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def delete_user(self, user_id: UUID) -> None:
        """Delete a user."""
        user = await self.get_user(user_id)
        user.is_active = False
        await self.session.flush()

    # ========================================================================
    # Membership Operations
    # ========================================================================

    async def add_member(
        self,
        tenant_id: UUID,
        data: MembershipCreate,
    ) -> TenantMembership:
        """Add a user to a tenant."""
        # Verify tenant and user exist
        await self.get_tenant(tenant_id)
        await self.get_user(data.user_id)

        # Check for existing membership
        existing = await self.session.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == data.user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                "Membership",
                f"User is already a member of this tenant",
            )

        membership = TenantMembership(
            tenant_id=tenant_id,
            user_id=data.user_id,
            role=data.role,
        )
        self.session.add(membership)
        await self.session.flush()
        await self.session.refresh(membership)
        return membership

    async def get_membership(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> TenantMembership:
        """Get a specific membership."""
        result = await self.session.execute(
            select(TenantMembership)
            .options(selectinload(TenantMembership.user))
            .where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == user_id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise NotFoundError("Membership")
        return membership

    async def list_members(
        self,
        tenant_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[TenantMembership], int]:
        """List all members of a tenant."""
        count_query = select(func.count(TenantMembership.id)).where(
            TenantMembership.tenant_id == tenant_id
        )
        total = (await self.session.execute(count_query)).scalar() or 0

        query = (
            select(TenantMembership)
            .options(selectinload(TenantMembership.user))
            .where(TenantMembership.tenant_id == tenant_id)
            .order_by(TenantMembership.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        members = result.scalars().all()

        return members, total

    async def update_member_role(
        self,
        tenant_id: UUID,
        user_id: UUID,
        role: UserRole,
    ) -> TenantMembership:
        """Update a member's role."""
        membership = await self.get_membership(tenant_id, user_id)
        membership.role = role
        await self.session.flush()
        await self.session.refresh(membership)
        return membership

    async def remove_member(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> None:
        """Remove a user from a tenant."""
        membership = await self.get_membership(tenant_id, user_id)
        await self.session.delete(membership)
        await self.session.flush()

    async def get_user_tenants(
        self,
        user_id: UUID,
    ) -> Sequence[TenantMembership]:
        """Get all tenants a user belongs to."""
        query = (
            select(TenantMembership)
            .options(selectinload(TenantMembership.tenant))
            .where(TenantMembership.user_id == user_id)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    # ========================================================================
    # Authentication Operations
    # ========================================================================

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> User:
        """Authenticate a user with email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        if not user.hashed_password:
            raise AuthenticationError("Password authentication not available")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        return user

    async def create_tokens(
        self,
        user: User,
        tenant_id: UUID | None = None,
        role: str | None = None,
    ) -> TokenResponse:
        """Create access and refresh tokens for a user."""
        access_token = create_access_token(
            subject=str(user.id),
            tenant_id=str(tenant_id) if tenant_id else None,
            role=role,
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change a user's password."""
        user = await self.get_user(user_id)

        if not user.hashed_password:
            raise AuthenticationError("Password not set")

        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")

        user.hashed_password = hash_password(new_password)
        await self.session.flush()

    # ========================================================================
    # API Key Operations
    # ========================================================================

    async def create_api_key(
        self,
        user_id: UUID,
        tenant_id: UUID,
        data: APIKeyCreate,
    ) -> tuple[APIKey, str]:
        """
        Create a new API key.

        Returns:
            Tuple of (APIKey model, raw key string).
            The raw key is only returned once at creation.
        """
        raw_key, hashed_key = generate_api_key()
        prefix = raw_key[:12]  # Store prefix for identification

        expires_at = None
        if data.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

        api_key = APIKey(
            user_id=user_id,
            tenant_id=tenant_id,
            name=data.name,
            hashed_key=hashed_key,
            prefix=prefix,
            scopes=data.scopes,
            expires_at=expires_at,
        )
        self.session.add(api_key)
        await self.session.flush()
        await self.session.refresh(api_key)

        return api_key, raw_key

    async def get_api_key_by_hash(self, hashed_key: str) -> APIKey | None:
        """Get API key by its hash."""
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.hashed_key == hashed_key,
                APIKey.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def list_api_keys(
        self,
        user_id: UUID,
        tenant_id: UUID | None = None,
    ) -> Sequence[APIKey]:
        """List API keys for a user."""
        query = select(APIKey).where(
            APIKey.user_id == user_id,
            APIKey.is_active == True,
        )
        if tenant_id:
            query = query.where(APIKey.tenant_id == tenant_id)

        query = query.order_by(APIKey.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def revoke_api_key(
        self,
        key_id: UUID,
        user_id: UUID,
    ) -> None:
        """Revoke an API key."""
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.id == key_id,
                APIKey.user_id == user_id,
            )
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise NotFoundError("API Key", str(key_id))

        api_key.is_active = False
        await self.session.flush()

    async def update_api_key_usage(self, key_id: UUID) -> None:
        """Update last used timestamp for an API key."""
        result = await self.session.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        api_key = result.scalar_one_or_none()
        if api_key:
            api_key.last_used_at = datetime.now(timezone.utc)
            await self.session.flush()
