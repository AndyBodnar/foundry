"""Pydantic schemas for tenant domain."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from foundry.infrastructure.database.models import TenantStatus, UserRole


# ============================================================================
# Tenant Schemas
# ============================================================================


class TenantBase(BaseModel):
    """Base tenant schema."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class TenantCreate(TenantBase):
    """Schema for creating a tenant."""

    settings: dict[str, Any] = Field(default_factory=dict)
    quotas: dict[str, Any] = Field(default_factory=dict)


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    name: str | None = Field(None, min_length=1, max_length=255)
    status: TenantStatus | None = None
    settings: dict[str, Any] | None = None
    quotas: dict[str, Any] | None = None


class TenantResponse(TenantBase):
    """Schema for tenant response."""

    id: UUID
    status: TenantStatus
    settings: dict[str, Any]
    quotas: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantListResponse(BaseModel):
    """Schema for paginated tenant list."""

    items: list[TenantResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# User Schemas
# ============================================================================


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None


class UserResponse(UserBase):
    """Schema for user response."""

    id: UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Schema for paginated user list."""

    items: list[UserResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# Membership Schemas
# ============================================================================


class MembershipCreate(BaseModel):
    """Schema for creating a tenant membership."""

    user_id: UUID
    role: UserRole = UserRole.VIEWER


class MembershipUpdate(BaseModel):
    """Schema for updating a membership."""

    role: UserRole


class MembershipResponse(BaseModel):
    """Schema for membership response."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    role: UserRole
    created_at: datetime
    user: UserResponse | None = None

    model_config = {"from_attributes": True}


# ============================================================================
# Auth Schemas
# ============================================================================


class TokenResponse(BaseModel):
    """Schema for authentication token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr
    password: str


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# ============================================================================
# API Key Schemas
# ============================================================================


class APIKeyCreate(BaseModel):
    """Schema for creating an API key."""

    name: str = Field(..., min_length=1, max_length=255)
    scopes: list[str] = Field(default_factory=list)
    expires_in_days: int | None = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    """Schema for API key response (without the actual key)."""

    id: UUID
    name: str
    prefix: str
    scopes: list[str]
    expires_at: datetime | None
    last_used_at: datetime | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyCreatedResponse(APIKeyResponse):
    """Schema for newly created API key (includes the actual key)."""

    key: str  # Only returned once at creation


class CurrentUser(BaseModel):
    """Schema for current authenticated user context."""

    id: UUID
    email: str
    name: str
    tenant_id: UUID | None
    role: UserRole | None
    is_superuser: bool

    model_config = {"from_attributes": True}
