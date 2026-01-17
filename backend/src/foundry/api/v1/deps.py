"""API dependencies - authentication, database sessions, etc."""

from typing import Annotated, AsyncGenerator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from foundry.core.security import decode_token, hash_api_key, TokenPayload
from foundry.core.exceptions import AuthenticationError, AuthorizationError
from foundry.infrastructure.database.session import get_session
from foundry.infrastructure.database.models import UserRole
from foundry.infrastructure.cache.redis import get_redis, RedisCache
from foundry.infrastructure.storage.s3 import get_storage, S3Storage
from foundry.domain.tenants.service import TenantService
from foundry.domain.tenants.schemas import CurrentUser
from foundry.config import settings

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async for session in get_session():
        yield session


async def get_cache() -> RedisCache | None:
    """Dependency for Redis cache."""
    try:
        redis = await get_redis()
        return RedisCache(redis)
    except Exception:
        return None


async def get_storage_client() -> S3Storage:
    """Dependency for S3 storage."""
    return get_storage()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    Get current authenticated user from JWT token or API key.

    Supports two authentication methods:
    1. Bearer token (JWT) in Authorization header
    2. API key in X-API-Key header
    """
    if credentials:
        # JWT authentication
        try:
            token_payload = decode_token(credentials.credentials)
            return CurrentUser(
                id=UUID(token_payload.user_id),
                email="",  # Will be fetched if needed
                name="",
                tenant_id=UUID(token_payload.tenant_id) if token_payload.tenant_id else None,
                role=UserRole(token_payload.role) if token_payload.role else None,
                is_superuser=False,
            )
        except AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.message,
                headers={"WWW-Authenticate": "Bearer"},
            )

    elif x_api_key:
        # API key authentication
        if not x_api_key.startswith(settings.api_key_prefix):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key format",
            )

        hashed_key = hash_api_key(x_api_key)
        tenant_service = TenantService(db)
        api_key = await tenant_service.get_api_key_by_hash(hashed_key)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        if api_key.expires_at and api_key.expires_at.replace(tzinfo=None) < __import__("datetime").datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key expired",
            )

        # Update last used timestamp (fire and forget)
        await tenant_service.update_api_key_usage(api_key.id)

        # Get user role from membership
        membership = await tenant_service.get_membership(api_key.tenant_id, api_key.user_id)

        return CurrentUser(
            id=api_key.user_id,
            email="",
            name="",
            tenant_id=api_key.tenant_id,
            role=membership.role,
            is_superuser=False,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Ensure the current user is active."""
    # In a full implementation, we'd check user.is_active
    return current_user


def require_role(required_role: UserRole):
    """Dependency factory for role-based access control."""

    async def check_role(
        current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    ) -> CurrentUser:
        if current_user.is_superuser:
            return current_user

        if not current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No role assigned",
            )

        # Role hierarchy: admin > ml_engineer > data_scientist > viewer
        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.DATA_SCIENTIST: 2,
            UserRole.ML_ENGINEER: 3,
            UserRole.ADMIN: 4,
        }

        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )

        return current_user

    return check_role


def get_tenant_id(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
) -> UUID:
    """Get tenant ID from current user."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required",
        )
    return current_user.tenant_id


# Type aliases for dependencies
DbSession = Annotated[AsyncSession, Depends(get_db)]
Cache = Annotated[RedisCache | None, Depends(get_cache)]
Storage = Annotated[S3Storage, Depends(get_storage_client)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
TenantId = Annotated[UUID, Depends(get_tenant_id)]

# Role-specific dependencies
ViewerUser = Annotated[CurrentUser, Depends(require_role(UserRole.VIEWER))]
DataScientistUser = Annotated[CurrentUser, Depends(require_role(UserRole.DATA_SCIENTIST))]
MLEngineerUser = Annotated[CurrentUser, Depends(require_role(UserRole.ML_ENGINEER))]
AdminUser = Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))]
