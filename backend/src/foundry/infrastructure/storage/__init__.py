"""Object storage infrastructure (S3/MinIO)."""

from foundry.infrastructure.storage.s3 import S3Storage, get_storage

__all__ = [
    "S3Storage",
    "get_storage",
]
