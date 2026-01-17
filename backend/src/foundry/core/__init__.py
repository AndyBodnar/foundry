"""Core module - security, exceptions, and lifecycle events."""

from foundry.core.exceptions import (
    FoundryException,
    NotFoundError,
    ConflictError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ExternalServiceError,
)
from foundry.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_password,
    verify_password,
    generate_api_key,
    hash_api_key,
)

__all__ = [
    # Exceptions
    "FoundryException",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    "ExternalServiceError",
    # Security
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "hash_password",
    "verify_password",
    "generate_api_key",
    "hash_api_key",
]
