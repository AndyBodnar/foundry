"""API v1 routes."""

from fastapi import APIRouter

from foundry.api.v1.experiments import router as experiments_router
from foundry.api.v1.models import router as models_router
from foundry.api.v1.features import router as features_router
from foundry.api.v1.deployments import router as deployments_router
from foundry.api.v1.monitoring import router as monitoring_router
from foundry.api.v1.pipelines import router as pipelines_router
from foundry.api.v1.auth import router as auth_router

api_router = APIRouter()

# Include all routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(experiments_router, prefix="/experiments", tags=["Experiments"])
api_router.include_router(models_router, prefix="/models", tags=["Model Registry"])
api_router.include_router(features_router, prefix="/features", tags=["Feature Store"])
api_router.include_router(deployments_router, prefix="/deployments", tags=["Deployments"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["Monitoring"])
api_router.include_router(pipelines_router, prefix="/pipelines", tags=["Pipelines"])

__all__ = ["api_router"]
