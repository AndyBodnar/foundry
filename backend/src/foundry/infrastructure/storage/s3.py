"""S3/MinIO object storage implementation."""

import hashlib
import io
from datetime import datetime, timedelta
from typing import Any, BinaryIO
from urllib.parse import urljoin

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from foundry.config import settings
from foundry.core.exceptions import ExternalServiceError


class S3Storage:
    """S3/MinIO storage client for artifact management."""

    def __init__(
        self,
        bucket_name: str | None = None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region: str | None = None,
    ) -> None:
        self.bucket_name = bucket_name or settings.s3_bucket_name
        self.endpoint_url = endpoint_url or settings.s3_endpoint_url
        self.region = region or settings.s3_region

        config = Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "adaptive"},
        )

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key_id or settings.s3_access_key_id,
            aws_secret_access_key=secret_access_key or settings.s3_secret_access_key,
            region_name=self.region,
            config=config,
        )

    def _build_key(self, tenant_id: str, *parts: str) -> str:
        """Build a storage key with tenant prefix."""
        return f"tenants/{tenant_id}/{'/'.join(parts)}"

    async def upload_file(
        self,
        tenant_id: str,
        file_path: str,
        content: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Upload a file to S3.

        Args:
            tenant_id: Tenant identifier for isolation
            file_path: Path within the tenant's storage
            content: File content as bytes or file-like object
            content_type: MIME type of the file
            metadata: Optional metadata to attach

        Returns:
            Dictionary with upload details including path and checksum.
        """
        key = self._build_key(tenant_id, file_path)

        # Calculate checksum
        if isinstance(content, bytes):
            checksum = hashlib.sha256(content).hexdigest()
            content_length = len(content)
            body = io.BytesIO(content)
        else:
            # Read file content for checksum
            content_bytes = content.read()
            checksum = hashlib.sha256(content_bytes).hexdigest()
            content_length = len(content_bytes)
            body = io.BytesIO(content_bytes)

        try:
            extra_args: dict[str, Any] = {
                "ContentType": content_type,
            }
            if metadata:
                extra_args["Metadata"] = metadata

            self.client.upload_fileobj(
                body,
                self.bucket_name,
                key,
                ExtraArgs=extra_args,
            )

            return {
                "bucket": self.bucket_name,
                "key": key,
                "path": f"s3://{self.bucket_name}/{key}",
                "size_bytes": content_length,
                "checksum": checksum,
                "content_type": content_type,
            }

        except ClientError as e:
            raise ExternalServiceError(
                service="S3",
                message=f"Failed to upload file: {str(e)}",
                details={"key": key, "error": str(e)},
            )

    async def download_file(
        self,
        tenant_id: str,
        file_path: str,
    ) -> bytes:
        """
        Download a file from S3.

        Args:
            tenant_id: Tenant identifier
            file_path: Path within the tenant's storage

        Returns:
            File content as bytes.
        """
        key = self._build_key(tenant_id, file_path)

        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise ExternalServiceError(
                    service="S3",
                    message=f"File not found: {file_path}",
                    details={"key": key},
                )
            raise ExternalServiceError(
                service="S3",
                message=f"Failed to download file: {str(e)}",
                details={"key": key, "error": str(e)},
            )

    async def delete_file(
        self,
        tenant_id: str,
        file_path: str,
    ) -> bool:
        """
        Delete a file from S3.

        Args:
            tenant_id: Tenant identifier
            file_path: Path within the tenant's storage

        Returns:
            True if deleted successfully.
        """
        key = self._build_key(tenant_id, file_path)

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True

        except ClientError as e:
            raise ExternalServiceError(
                service="S3",
                message=f"Failed to delete file: {str(e)}",
                details={"key": key, "error": str(e)},
            )

    async def file_exists(
        self,
        tenant_id: str,
        file_path: str,
    ) -> bool:
        """Check if a file exists in S3."""
        key = self._build_key(tenant_id, file_path)

        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    async def get_file_info(
        self,
        tenant_id: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Get metadata about a file."""
        key = self._build_key(tenant_id, file_path)

        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=key)
            return {
                "key": key,
                "size_bytes": response["ContentLength"],
                "content_type": response.get("ContentType"),
                "last_modified": response["LastModified"],
                "etag": response.get("ETag", "").strip('"'),
                "metadata": response.get("Metadata", {}),
            }

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise ExternalServiceError(
                    service="S3",
                    message=f"File not found: {file_path}",
                    details={"key": key},
                )
            raise ExternalServiceError(
                service="S3",
                message=f"Failed to get file info: {str(e)}",
                details={"key": key, "error": str(e)},
            )

    async def generate_presigned_url(
        self,
        tenant_id: str,
        file_path: str,
        expiration: int = 3600,
        method: str = "get_object",
    ) -> str:
        """
        Generate a presigned URL for direct access.

        Args:
            tenant_id: Tenant identifier
            file_path: Path within the tenant's storage
            expiration: URL expiration time in seconds
            method: S3 method (get_object, put_object)

        Returns:
            Presigned URL string.
        """
        key = self._build_key(tenant_id, file_path)

        try:
            url = self.client.generate_presigned_url(
                method,
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
            return url

        except ClientError as e:
            raise ExternalServiceError(
                service="S3",
                message=f"Failed to generate presigned URL: {str(e)}",
                details={"key": key, "error": str(e)},
            )

    async def list_files(
        self,
        tenant_id: str,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        List files in a directory.

        Args:
            tenant_id: Tenant identifier
            prefix: Directory prefix to list
            max_keys: Maximum number of keys to return

        Returns:
            List of file info dictionaries.
        """
        key_prefix = self._build_key(tenant_id, prefix) if prefix else self._build_key(tenant_id, "")

        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=key_prefix,
                MaxKeys=max_keys,
            )

            files = []
            for obj in response.get("Contents", []):
                files.append({
                    "key": obj["Key"],
                    "size_bytes": obj["Size"],
                    "last_modified": obj["LastModified"],
                    "etag": obj.get("ETag", "").strip('"'),
                })

            return files

        except ClientError as e:
            raise ExternalServiceError(
                service="S3",
                message=f"Failed to list files: {str(e)}",
                details={"prefix": key_prefix, "error": str(e)},
            )

    async def copy_file(
        self,
        tenant_id: str,
        source_path: str,
        dest_path: str,
    ) -> dict[str, Any]:
        """Copy a file within the same bucket."""
        source_key = self._build_key(tenant_id, source_path)
        dest_key = self._build_key(tenant_id, dest_path)

        try:
            self.client.copy_object(
                Bucket=self.bucket_name,
                CopySource={"Bucket": self.bucket_name, "Key": source_key},
                Key=dest_key,
            )

            return {
                "source_key": source_key,
                "dest_key": dest_key,
                "path": f"s3://{self.bucket_name}/{dest_key}",
            }

        except ClientError as e:
            raise ExternalServiceError(
                service="S3",
                message=f"Failed to copy file: {str(e)}",
                details={"source": source_key, "dest": dest_key, "error": str(e)},
            )


# Singleton storage instance
_storage: S3Storage | None = None


def get_storage() -> S3Storage:
    """Get the S3 storage singleton instance."""
    global _storage
    if _storage is None:
        _storage = S3Storage()
    return _storage
