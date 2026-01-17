"""API middleware - authentication, logging, error handling."""

from foundry.api.middleware.error_handler import error_handler_middleware
from foundry.api.middleware.logging import LoggingMiddleware
from foundry.api.middleware.correlation import CorrelationIdMiddleware

__all__ = [
    "error_handler_middleware",
    "LoggingMiddleware",
    "CorrelationIdMiddleware",
]
