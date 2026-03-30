from __future__ import annotations

import io
import shutil
from datetime import timedelta
from pathlib import Path

from minio import Minio
from minio.commonconfig import CopySource

from app.core.config import Settings


class StorageClient:
    def healthcheck(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def ensure_bucket(self, bucket_name: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def put_bytes(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        *,
        content_type: str,
    ) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def read_bytes(self, bucket_name: str, object_name: str) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError

    def copy_object(
        self,
        source_bucket_name: str,
        source_object_name: str,
        target_bucket_name: str,
        target_object_name: str,
    ) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def delete_object(self, bucket_name: str, object_name: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def presigned_get_url(
        self,
        bucket_name: str,
        object_name: str,
        ttl_seconds: int = 300,
    ) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def presigned_put_url(
        self,
        bucket_name: str,
        object_name: str,
        ttl_seconds: int = 300,
    ) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class MinioStorageClient(StorageClient):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            region=settings.minio_region,
        )
        # Separate client for presigned URLs so the signature is computed
        # against the browser-reachable host rather than the Docker-internal one.
        public_ep = settings.minio_public_endpoint or settings.minio_endpoint
        self._public_client = Minio(
            endpoint=public_ep,
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

    def put_bytes(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        *,
        content_type: str,
    ) -> None:
        self.ensure_bucket(bucket_name)
        self.client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def read_bytes(self, bucket_name: str, object_name: str) -> bytes:
        response = self.client.get_object(bucket_name, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def copy_object(
        self,
        source_bucket_name: str,
        source_object_name: str,
        target_bucket_name: str,
        target_object_name: str,
    ) -> None:
        self.ensure_bucket(target_bucket_name)
        self.client.copy_object(
            bucket_name=target_bucket_name,
            object_name=target_object_name,
            source=CopySource(source_bucket_name, source_object_name),
        )

    def delete_object(self, bucket_name: str, object_name: str) -> None:
        self.client.remove_object(bucket_name, object_name)

    def presigned_get_url(self, bucket_name: str, object_name: str, ttl_seconds: int = 300) -> str:
        return self._public_client.presigned_get_object(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(seconds=ttl_seconds),
        )

    def presigned_put_url(self, bucket_name: str, object_name: str, ttl_seconds: int = 300) -> str:
        self.ensure_bucket(bucket_name)
        return self._public_client.presigned_put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(seconds=ttl_seconds),
        )


class LocalStorageClient(StorageClient):
    def __init__(self, settings: Settings) -> None:
        self.root = Path(settings.local_storage_root).resolve()

    def _path_for(self, bucket_name: str, object_name: str) -> Path:
        safe_object = Path(object_name.replace("\\", "/"))
        return self.root / bucket_name / safe_object

    def healthcheck(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def ensure_bucket(self, bucket_name: str) -> None:
        (self.root / bucket_name).mkdir(parents=True, exist_ok=True)

    def put_bytes(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        *,
        content_type: str,
    ) -> None:
        del content_type
        destination = self._path_for(bucket_name, object_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    def read_bytes(self, bucket_name: str, object_name: str) -> bytes:
        return self._path_for(bucket_name, object_name).read_bytes()

    def copy_object(
        self,
        source_bucket_name: str,
        source_object_name: str,
        target_bucket_name: str,
        target_object_name: str,
    ) -> None:
        source = self._path_for(source_bucket_name, source_object_name)
        destination = self._path_for(target_bucket_name, target_object_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    def delete_object(self, bucket_name: str, object_name: str) -> None:
        path = self._path_for(bucket_name, object_name)
        if path.exists():
            path.unlink()

    def presigned_get_url(self, bucket_name: str, object_name: str, ttl_seconds: int = 300) -> str:
        del ttl_seconds
        return str(self._path_for(bucket_name, object_name))

    def presigned_put_url(self, bucket_name: str, object_name: str, ttl_seconds: int = 300) -> str:
        del ttl_seconds
        destination = self._path_for(bucket_name, object_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        return str(destination)


def build_storage_client(settings: Settings) -> StorageClient:
    if settings.environment == "test":
        return LocalStorageClient(settings)
    return MinioStorageClient(settings)
