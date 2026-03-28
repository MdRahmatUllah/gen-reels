from __future__ import annotations

from datetime import timedelta

from minio import Minio

from app.core.config import Settings


class StorageClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            region=settings.minio_region,
        )

    def healthcheck(self) -> None:
        self.client.list_buckets()

    def ensure_bucket(self, bucket_name: str) -> None:
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

    def presigned_get_url(self, bucket_name: str, object_name: str, ttl_seconds: int = 300) -> str:
        return self.client.presigned_get_object(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(seconds=ttl_seconds),
        )


def build_storage_client(settings: Settings) -> StorageClient:
    return StorageClient(settings)
