from __future__ import annotations

from functools import lru_cache
from typing import Literal

from cryptography.fernet import Fernet
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
    frontend_url: str | None = None
    database_url: str = "sqlite:///./reels.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_always_eager: bool = False
    minio_endpoint: str = "localhost:9000"
    minio_public_endpoint: str | None = None
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
    app_encryption_key: str | None = None
    disable_browser_auth: bool | None = None
    jwt_access_token_ttl_minutes: int = 43200  # 30 days — no auto-logout
    jwt_refresh_token_ttl_days: int = 365
    access_cookie_name: str = "rg_access_token"
    refresh_cookie_name: str = "rg_refresh_token"
    dev_workspace_cookie_name: str = "rg_dev_workspace_id"
    dev_browser_auth_email: str = "admin@example.com"
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str | None = None
    # Chat completions (brief, script, scene plan, prompt pairs) — large JSON can exceed 90s.
    azure_openai_chat_timeout_seconds: float = 300.0
    azure_openai_image_deployment: str | None = None
    azure_openai_image_model: str = "gpt-image-1.5"
    azure_openai_image_api_version: str = "2024-02-01"
    azure_openai_speech_deployment: str | None = None
    azure_openai_speech_model: str = "tts-1-hd"
    azure_openai_speech_api_version: str = "2025-04-01-preview"
    azure_openai_speech_voice: str = "alloy"
    azure_openai_whisper_deployment: str | None = None
    azure_openai_whisper_api_version: str = "2024-06-01"
    azure_content_safety_endpoint: str | None = None
    azure_content_safety_api_key: str | None = None
    azure_content_safety_api_version: str = "2024-09-15-preview"
    azure_content_safety_block_threshold: int = 4
    vertex_ai_project_id: str | None = None
    vertex_ai_location: str = "us-central1"
    vertex_ai_model_id: str = "veo-3.1-generate-001"
    vertex_ai_access_token: str | None = None
    vertex_ai_output_storage_uri: str | None = None
    mail_from: str = "noreply@reels.local"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    password_reset_ttl_minutes: int = 60
    idempotency_retention_hours: int = 24
    planning_job_timeout_minutes: int = 30
    render_job_timeout_minutes: int = 120
    local_worker_heartbeat_timeout_seconds: int = 180
    render_event_stream_heartbeat_seconds: int = 15
    webhook_max_attempts: int = 5
    webhook_retry_base_seconds: int = 30
    export_moderation_sample_rate: float = 0.10
    export_moderation_lookback_days: int = 30
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    ffmpeg_docker_image: str = "jrottenberg/ffmpeg:6.1-alpine"
    model_cache_root: str = "/models"
    faster_whisper_cache_dir: str | None = None
    faster_whisper_device: Literal["auto", "cpu", "cuda"] = "auto"
    faster_whisper_cpu_compute_type: str = "int8"
    faster_whisper_cuda_compute_type: str = "float16"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    youtube_scopes: str = (
        "openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/userinfo.profile,"
        "https://www.googleapis.com/auth/youtube,"
        "https://www.googleapis.com/auth/youtube.upload"
    )
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
    def app_encryption_key_resolved(self) -> str:
        if self.app_encryption_key:
            return self.app_encryption_key
        if self.environment == "test":
            return Fernet.generate_key().decode("utf-8")
        raise ValueError("APP_ENCRYPTION_KEY is required outside test to avoid losing encrypted secrets.")

    @computed_field
    @property
    def disable_browser_auth_resolved(self) -> bool:
        if self.disable_browser_auth is not None:
            return self.disable_browser_auth
        return self.environment == "development"

    @computed_field
    @property
    def cookie_secure(self) -> bool:
        return self.environment not in {"development", "test"}

    @computed_field
    @property
    def cookie_samesite(self) -> str:
        return "strict" if self.cookie_secure else "lax"

    @computed_field
    @property
    def frontend_url_resolved(self) -> str:
        return (self.frontend_url or self.frontend_base_url).rstrip("/")

    @computed_field
    @property
    def faster_whisper_cache_dir_resolved(self) -> str:
        if self.faster_whisper_cache_dir:
            return self.faster_whisper_cache_dir.rstrip("/\\")
        return self.model_cache_root.rstrip("/\\") + "/faster-whisper"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
