"""Application lifecycle events and hooks."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI

from foundry.config import settings
from foundry.infrastructure.database.session import init_db, close_db
from foundry.infrastructure.cache.redis import init_redis, close_redis

logger = structlog.get_logger(__name__)


def configure_logging() -> None:
    """Configure structured logging."""
    # Set log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
    )


def setup_telemetry() -> None:
    """Setup OpenTelemetry tracing and metrics."""
    if not settings.enable_tracing or not settings.otlp_endpoint:
        logger.info("Tracing disabled or no OTLP endpoint configured")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME

        resource = Resource(attributes={
            SERVICE_NAME: settings.otlp_service_name,
        })

        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        logger.info("OpenTelemetry tracing configured", endpoint=settings.otlp_endpoint)

    except ImportError:
        logger.warning("OpenTelemetry packages not installed, tracing disabled")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info(
        "Starting Foundry API",
        environment=settings.environment,
        version=settings.app_version,
    )

    # Configure logging
    configure_logging()

    # Setup telemetry
    setup_telemetry()

    # Initialize database connection pool
    try:
        await init_db()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

    # Initialize Redis connection pool
    try:
        await init_redis()
        logger.info("Redis connection pool initialized")
    except Exception as e:
        logger.warning("Failed to initialize Redis", error=str(e))
        # Redis is not critical, continue without it

    logger.info("Foundry API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Foundry API")

    # Close database connections
    await close_db()
    logger.info("Database connections closed")

    # Close Redis connections
    await close_redis()
    logger.info("Redis connections closed")

    logger.info("Foundry API shutdown complete")


async def health_check() -> dict:
    """
    Perform health check on all services.

    Returns:
        Dictionary with health status of each service.
    """
    from foundry.infrastructure.database.session import get_db_health
    from foundry.infrastructure.cache.redis import get_redis_health

    health = {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "checks": {},
    }

    # Check database
    db_health = await get_db_health()
    health["checks"]["database"] = db_health

    # Check Redis
    redis_health = await get_redis_health()
    health["checks"]["redis"] = redis_health

    # Determine overall status
    if not db_health.get("healthy", False):
        health["status"] = "unhealthy"
    elif not redis_health.get("healthy", False):
        health["status"] = "degraded"

    return health


async def readiness_check() -> dict:
    """
    Check if the application is ready to serve requests.

    Returns:
        Dictionary with readiness status.
    """
    from foundry.infrastructure.database.session import get_db_health

    # Database is required for readiness
    db_health = await get_db_health()

    return {
        "ready": db_health.get("healthy", False),
        "checks": {
            "database": db_health,
        },
    }
