"""Object storage abstraction (A-02 backend-mediated, S-06 presigned download).

Runtime uses boto3 against MinIO/S3. Tests inject an in-memory fake. The service layer
depends only on the StorageClient protocol so it never imports boto3 directly (§5 isolation).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.config import get_settings


@runtime_checkable
class StorageClient(Protocol):
    def put_object(self, *, bucket: str, key: str, data: bytes, content_type: str) -> None: ...

    def delete_object(self, *, bucket: str, key: str) -> None: ...

    def presigned_get_url(self, *, bucket: str, key: str, expires_in: int) -> str: ...


class S3StorageClient:
    """boto3-backed client for MinIO/S3. Buckets are created lazily on first use."""

    def __init__(self) -> None:
        import boto3
        from botocore.client import Config

        settings = get_settings()
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
        )

    def _ensure_bucket(self, bucket: str) -> None:
        from botocore.exceptions import ClientError

        try:
            self._client.head_bucket(Bucket=bucket)
        except ClientError:
            self._client.create_bucket(Bucket=bucket)

    def put_object(self, *, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self._ensure_bucket(bucket)
        self._client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)

    def delete_object(self, *, bucket: str, key: str) -> None:
        self._client.delete_object(Bucket=bucket, Key=key)

    def presigned_get_url(self, *, bucket: str, key: str, expires_in: int) -> str:
        # GET-only, key-bound, short TTL (S-06).
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
            HttpMethod="GET",
        )


class InMemoryStorageClient:
    """Test/dev double: stores objects in a dict and returns deterministic fake URLs."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, *, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self.objects[(bucket, key)] = data

    def delete_object(self, *, bucket: str, key: str) -> None:
        self.objects.pop((bucket, key), None)

    def presigned_get_url(self, *, bucket: str, key: str, expires_in: int) -> str:
        return f"https://storage.local/{bucket}/{key}?expires_in={expires_in}"


def get_storage() -> StorageClient:
    """FastAPI dependency returning the runtime storage client (overridden in tests)."""
    return S3StorageClient()
