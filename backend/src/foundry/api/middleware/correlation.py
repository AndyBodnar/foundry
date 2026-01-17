"""Correlation ID middleware for request tracing."""

import uuid
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for correlation ID
from contextvars import ContextVar

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle correlation IDs for distributed tracing.

    - Extracts or generates X-Correlation-ID header
    - Generates unique X-Request-ID for each request
    - Makes IDs available in context variables for logging
    - Adds IDs to response headers
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and manage correlation IDs."""
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Always generate new request ID
        request_id = str(uuid.uuid4())

        # Set context variables
        correlation_id_ctx.set(correlation_id)
        request_id_ctx.set(request_id)

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_id=request_id,
        )

        # Store in request state for easy access
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add IDs to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-ID"] = request_id

        return response


def get_correlation_id() -> str:
    """Get current correlation ID from context."""
    return correlation_id_ctx.get()


def get_request_id() -> str:
    """Get current request ID from context."""
    return request_id_ctx.get()
