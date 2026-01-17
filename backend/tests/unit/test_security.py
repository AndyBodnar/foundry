"""Tests for security utilities."""

import pytest
from datetime import timedelta
from uuid import uuid4

from foundry.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    verify_api_key,
)
from foundry.core.exceptions import AuthenticationError


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "SecurePassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "SecurePassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "SecurePassword123"
        hashed = hash_password(password)

        assert verify_password("WrongPassword", hashed) is False

    def test_hash_uniqueness(self):
        """Test that same password produces different hashes."""
        password = "SecurePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Bcrypt uses different salts, so hashes should differ
        assert hash1 != hash2
        # But both should verify
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTTokens:
    """Tests for JWT token functions."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = uuid4()
        token = create_access_token(subject=str(user_id))

        assert token is not None
        assert len(token) > 0

    def test_create_access_token_with_tenant(self):
        """Test access token creation with tenant."""
        user_id = uuid4()
        tenant_id = uuid4()
        token = create_access_token(
            subject=str(user_id),
            tenant_id=str(tenant_id),
            role="ADMIN",
        )

        payload = verify_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["tenant_id"] == str(tenant_id)
        assert payload["role"] == "ADMIN"

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = uuid4()
        token = create_refresh_token(subject=str(user_id))

        assert token is not None
        payload = verify_token(token, token_type="refresh")
        assert payload["type"] == "refresh"

    def test_verify_token_success(self):
        """Test token verification."""
        user_id = uuid4()
        token = create_access_token(subject=str(user_id))

        payload = verify_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_verify_token_wrong_type(self):
        """Test token verification with wrong type."""
        user_id = uuid4()
        access_token = create_access_token(subject=str(user_id))

        with pytest.raises(AuthenticationError):
            verify_token(access_token, token_type="refresh")

    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        with pytest.raises(AuthenticationError):
            verify_token("invalid.token.here")

    def test_decode_token(self):
        """Test token decoding to TokenPayload."""
        user_id = uuid4()
        tenant_id = uuid4()
        token = create_access_token(
            subject=str(user_id),
            tenant_id=str(tenant_id),
            role="DATA_SCIENTIST",
        )

        payload = decode_token(token)
        assert payload.user_id == str(user_id)
        assert payload.tenant_id == str(tenant_id)
        assert payload.role == "DATA_SCIENTIST"
        assert payload.token_type == "access"

    def test_token_payload_has_role(self):
        """Test TokenPayload role checking."""
        user_id = uuid4()
        token = create_access_token(
            subject=str(user_id),
            role="ML_ENGINEER",
        )

        payload = decode_token(token)

        assert payload.has_role("VIEWER")
        assert payload.has_role("DATA_SCIENTIST")
        assert payload.has_role("ML_ENGINEER")
        assert not payload.has_role("ADMIN")


class TestAPIKeys:
    """Tests for API key functions."""

    def test_generate_api_key(self):
        """Test API key generation."""
        raw_key, hashed_key = generate_api_key()

        assert raw_key.startswith("fnd_")
        assert len(raw_key) > 20
        assert len(hashed_key) == 64  # SHA256 hex

    def test_hash_api_key(self):
        """Test API key hashing."""
        key = "fnd_test_key_123"
        hashed = hash_api_key(key)

        assert hashed != key
        assert len(hashed) == 64

    def test_verify_api_key_correct(self):
        """Test API key verification with correct key."""
        raw_key, hashed_key = generate_api_key()

        assert verify_api_key(raw_key, hashed_key) is True

    def test_verify_api_key_incorrect(self):
        """Test API key verification with incorrect key."""
        _, hashed_key = generate_api_key()

        assert verify_api_key("fnd_wrong_key", hashed_key) is False
