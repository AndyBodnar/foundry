"""Authentication API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from foundry.api.v1.deps import DbSession, CurrentUserDep, TenantId
from foundry.domain.tenants.service import TenantService
from foundry.domain.tenants.schemas import (
    LoginRequest,
    TokenResponse,
    TokenRefreshRequest,
    UserCreate,
    UserResponse,
    PasswordChangeRequest,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreatedResponse,
)
from foundry.core.security import verify_token
from foundry.core.exceptions import AuthenticationError

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: DbSession,
):
    """
    Authenticate user and return access/refresh tokens.

    The response includes:
    - access_token: Short-lived JWT for API access
    - refresh_token: Long-lived token for getting new access tokens
    - expires_in: Access token expiration in seconds
    """
    service = TenantService(db)

    try:
        user = await service.authenticate(data.email, data.password)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )

    # Get user's tenants to include first tenant in token
    memberships = await service.get_user_tenants(user.id)
    tenant_id = memberships[0].tenant_id if memberships else None
    role = memberships[0].role.value if memberships else None

    tokens = await service.create_tokens(user, tenant_id, role)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: TokenRefreshRequest,
    db: DbSession,
):
    """
    Refresh access token using refresh token.

    Use this endpoint to get a new access token when the current one expires.
    """
    try:
        payload = verify_token(data.refresh_token, token_type="refresh")
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )

    service = TenantService(db)
    user = await service.get_user(UUID(payload["sub"]))

    # Get user's tenants
    memberships = await service.get_user_tenants(user.id)
    tenant_id = memberships[0].tenant_id if memberships else None
    role = memberships[0].role.value if memberships else None

    tokens = await service.create_tokens(user, tenant_id, role)
    return tokens


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    db: DbSession,
):
    """
    Register a new user account.

    Note: In production, this endpoint would typically be disabled or
    protected, with user creation handled through admin interfaces or SSO.
    """
    service = TenantService(db)

    try:
        user = await service.create_user(data)
        return UserResponse.model_validate(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUserDep,
    db: DbSession,
):
    """Get current authenticated user information."""
    service = TenantService(db)
    user = await service.get_user(current_user.id)
    return UserResponse.model_validate(user)


@router.post("/change-password")
async def change_password(
    data: PasswordChangeRequest,
    current_user: CurrentUserDep,
    db: DbSession,
):
    """Change current user's password."""
    service = TenantService(db)

    try:
        await service.change_password(
            current_user.id,
            data.current_password,
            data.new_password,
        )
        return {"message": "Password changed successfully"}
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


# ============================================================================
# API Key Management
# ============================================================================


@router.post("/api-keys", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: APIKeyCreate,
    current_user: CurrentUserDep,
    tenant_id: TenantId,
    db: DbSession,
):
    """
    Create a new API key.

    The API key is only returned once in this response.
    Store it securely as it cannot be retrieved again.
    """
    service = TenantService(db)
    api_key, raw_key = await service.create_api_key(
        current_user.id,
        tenant_id,
        data,
    )

    response = APIKeyCreatedResponse.model_validate(api_key)
    response.key = raw_key
    return response


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: CurrentUserDep,
    tenant_id: TenantId,
    db: DbSession,
):
    """List all API keys for the current user."""
    service = TenantService(db)
    api_keys = await service.list_api_keys(current_user.id, tenant_id)
    return [APIKeyResponse.model_validate(key) for key in api_keys]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
):
    """Revoke an API key."""
    service = TenantService(db)
    await service.revoke_api_key(key_id, current_user.id)
    return {"message": "API key revoked"}
