"""Celery application configuration."""

from celery import Celery

from foundry.config import settings

celery_app = Celery(
    "foundry",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "foundry.workers.tasks.experiments",
        "foundry.workers.tasks.deployments",
        "foundry.workers.tasks.monitoring",
        "foundry.workers.tasks.pipelines",
        "foundry.workers.tasks.features",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # Result settings
    result_expires=86400,  # 24 hours

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Beat schedule for periodic tasks
    beat_schedule={
        "check-drift-every-hour": {
            "task": "foundry.workers.tasks.monitoring.check_all_deployments_drift",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-old-runs-daily": {
            "task": "foundry.workers.tasks.experiments.cleanup_old_runs",
            "schedule": 86400.0,  # Daily
        },
        "refresh-features-hourly": {
            "task": "foundry.workers.tasks.features.refresh_all_feature_views",
            "schedule": 3600.0,  # Every hour
        },
    },

    # Task routing
    task_routes={
        "foundry.workers.tasks.deployments.*": {"queue": "deployments"},
        "foundry.workers.tasks.monitoring.*": {"queue": "monitoring"},
        "foundry.workers.tasks.pipelines.*": {"queue": "pipelines"},
        "foundry.workers.tasks.features.*": {"queue": "features"},
        "foundry.workers.tasks.experiments.*": {"queue": "default"},
    },
)
