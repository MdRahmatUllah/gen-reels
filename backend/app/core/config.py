from __future__ import annotations

from functools import lru_cache
from typing import Literal

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


@lru_cache(maxsize=1)
def _generate_dev_rsa_pair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    environment: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "Reels Generation Backend"
    api_v1_prefix: str = "/api/v1"
    app_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:5173"
    database_url: str = "sqlite:///./reels.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_always_eager: bool = False
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_region: str = "us-east-1"
    minio_bucket_assets: str = "reels-assets"
    minio_bucket_quarantine: str = "reels-quarantine"
    minio_bucket_temp: str = "reels-temp"
    minio_bucket_models: str = "reels-models"
    local_storage_root: str = ".local-storage"
    jwt_private_key: str | None = None
    jwt_public_key: str | None = None
    jwt_access_token_ttl_minutes: int = 15
    jwt_refresh_token_ttl_days: int = 30
    access_cookie_name: str = "rg_access_token"
    refresh_cookie_name: str = "rg_refresh_token"
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str | None = None
    azure_content_safety_endpoint: str | None = None
    azure_content_safety_api_key: str | None = None
    azure_content_safety_api_version: str = "2024-09-15-preview"
    azure_content_safety_block_threshold: int = 4
    mail_from: str = "noreply@reels.local"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    password_reset_ttl_minutes: int = 60
    idempotency_retention_hours: int = 24
    planning_job_timeout_minutes: int = 30
    render_job_timeout_minutes: int = 120
    allow_export_without_music: bool = True
    use_stub_providers: bool = False

    @computed_field
    @property
    def jwt_private_key_resolved(self) -> str:
        if self.jwt_private_key:
            return self.jwt_private_key
        if self.environment in {"development", "test"}:
            return _generate_dev_rsa_pair()[0]
        raise ValueError("JWT_PRIVATE_KEY is required outside development and test.")

    @computed_field
    @property
    def jwt_public_key_resolved(self) -> str:
        if self.jwt_public_key:
            return self.jwt_public_key
        if self.environment in {"development", "test"}:
            return _generate_dev_rsa_pair()[1]
        raise ValueError("JWT_PUBLIC_KEY is required outside development and test.")

    @computed_field
    @property
    def cookie_secure(self) -> bool:
        return self.environment not in {"development", "test"}

    @computed_field
    @property
    def cookie_samesite(self) -> str:
        return "strict" if self.cookie_secure else "lax"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
