"""Custom exceptions for the Foundry platform."""

from typing import Any


class FoundryException(Exception):
    """Base exception for all Foundry errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        }


class NotFoundError(FoundryException):
    """Resource not found error."""

    def __init__(
        self,
        resource: str,
        identifier: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details or {"resource": resource, "identifier": identifier},
        )


class ConflictError(FoundryException):
    """Resource conflict error (e.g., duplicate)."""

    def __init__(
        self,
        resource: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message or f"{resource} already exists",
            status_code=409,
            error_code="CONFLICT",
            details=details or {"resource": resource},
        )


class ValidationError(FoundryException):
    """Input validation error."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=error_details,
        )


class AuthenticationError(FoundryException):
    """Authentication failed error."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details or {},
        )


class AuthorizationError(FoundryException):
    """Authorization failed error (insufficient permissions)."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        resource: str | None = None,
        action: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = details or {}
        if resource:
            error_details["resource"] = resource
        if action:
            error_details["action"] = action
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=error_details,
        )


class RateLimitError(FoundryException):
    """Rate limit exceeded error."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = details or {}
        if retry_after:
            error_details["retry_after_seconds"] = retry_after
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=error_details,
        )


class ExternalServiceError(FoundryException):
    """External service error (database, cache, storage, etc.)."""

    def __init__(
        self,
        service: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message or f"External service '{service}' error",
            status_code=503,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details or {"service": service},
        )


class TenantIsolationError(FoundryException):
    """Tenant isolation violation error."""

    def __init__(
        self,
        message: str = "Tenant isolation violation",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=403,
            error_code="TENANT_ISOLATION_ERROR",
            details=details or {},
        )


class QuotaExceededError(FoundryException):
    """Quota exceeded error."""

    def __init__(
        self,
        quota_type: str,
        limit: int,
        current: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = details or {}
        error_details.update({
            "quota_type": quota_type,
            "limit": limit,
            "current": current,
        })
        super().__init__(
            message=f"Quota exceeded for {quota_type}: {current}/{limit}",
            status_code=429,
            error_code="QUOTA_EXCEEDED",
            details=error_details,
        )


class ModelStageTransitionError(FoundryException):
    """Invalid model stage transition error."""

    def __init__(
        self,
        current_stage: str,
        target_stage: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = details or {}
        error_details.update({
            "current_stage": current_stage,
            "target_stage": target_stage,
        })
        super().__init__(
            message=f"Invalid stage transition from '{current_stage}' to '{target_stage}'",
            status_code=400,
            error_code="INVALID_STAGE_TRANSITION",
            details=error_details,
        )


class DeploymentError(FoundryException):
    """Deployment operation error."""

    def __init__(
        self,
        message: str,
        deployment_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = details or {}
        if deployment_id:
            error_details["deployment_id"] = deployment_id
        super().__init__(
            message=message,
            status_code=500,
            error_code="DEPLOYMENT_ERROR",
            details=error_details,
        )
