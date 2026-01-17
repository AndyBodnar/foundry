"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from foundry.config import settings
from foundry.core.events import lifespan, health_check, readiness_check
from foundry.api.v1 import api_router
from foundry.api.middleware import (
    error_handler_middleware,
    LoggingMiddleware,
    CorrelationIdMiddleware,
)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Foundry MLOps Platform - Complete ML lifecycle management",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else "/api/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # Register error handlers
    error_handler_middleware(app)

    # Mount Prometheus metrics endpoint
    if settings.enable_metrics:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    # Include API router
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # Health check endpoints
    @app.get("/health", tags=["Health"])
    async def health():
        """Health check endpoint for load balancers."""
        return await health_check()

    @app.get("/ready", tags=["Health"])
    async def ready():
        """Readiness check endpoint for Kubernetes."""
        return await readiness_check()

    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "docs": "/docs" if settings.debug else None,
            "api": settings.api_v1_prefix,
        }

    return app


# Create application instance
app = create_application()


def run() -> None:
    """Run the application using uvicorn."""
    import uvicorn

    uvicorn.run(
        "foundry.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
