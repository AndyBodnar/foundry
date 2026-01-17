"""Security utilities for authentication and authorization."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from foundry.config import settings
from foundry.core.exceptions import AuthenticationError


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    subject: str | UUID,
    tenant_id: str | UUID | None = None,
    role: str | None = None,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "iat": now,
        "exp": expire,
    }

    if tenant_id:
        to_encode["tenant_id"] = str(tenant_id)
    if role:
        to_encode["role"] = role
    if additional_claims:
        to_encode.update(additional_claims)

    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: str | UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token."""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.jwt_refresh_token_expire_days)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    to_encode = {
        "sub": str(subject),
        "type": "refresh",
        "iat": now,
        "exp": expire,
        "jti": secrets.token_urlsafe(32),  # Unique token ID for revocation
    }

    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str, token_type: str = "access") -> dict[str, Any]:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        # Verify token type
        if payload.get("type") != token_type:
            raise AuthenticationError(
                message=f"Invalid token type. Expected {token_type}.",
                details={"expected_type": token_type},
            )

        return payload

    except JWTError as e:
        raise AuthenticationError(
            message="Invalid or expired token",
            details={"error": str(e)},
        )


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (raw_key, hashed_key)
        The raw_key is returned to the user once, the hashed_key is stored.
    """
    # Generate a secure random key
    random_bytes = secrets.token_bytes(32)
    raw_key = f"{settings.api_key_prefix}{secrets.token_urlsafe(32)}"
    hashed_key = hash_api_key(raw_key)

    return raw_key, hashed_key


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return secrets.compare_digest(hash_api_key(api_key), hashed_key)


class TokenPayload:
    """Parsed token payload with typed attributes."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.subject: str = payload["sub"]
        self.token_type: str = payload["type"]
        self.tenant_id: str | None = payload.get("tenant_id")
        self.role: str | None = payload.get("role")
        self.issued_at: datetime = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        self.expires_at: datetime = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        self.token_id: str | None = payload.get("jti")
        self._raw_payload = payload

    @property
    def user_id(self) -> str:
        """Alias for subject as user_id."""
        return self.subject

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def has_role(self, required_role: str) -> bool:
        """Check if token has required role."""
        if not self.role:
            return False
        # Role hierarchy: admin > ml_engineer > data_scientist > viewer
        # Use lowercase for comparison to handle case-insensitivity
        role_hierarchy = {
            "viewer": 1,
            "data_scientist": 2,
            "ml_engineer": 3,
            "admin": 4,
        }
        user_level = role_hierarchy.get(self.role.lower(), 0)
        required_level = role_hierarchy.get(required_role.lower(), 0)
        return user_level >= required_level

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self._raw_payload


def decode_token(token: str, token_type: str = "access") -> TokenPayload:
    """Decode and return a typed TokenPayload object."""
    payload = verify_token(token, token_type)
    return TokenPayload(payload)
