"""Celery workers for background task processing."""

from foundry.workers.celery_app import celery_app

__all__ = ["celery_app"]
