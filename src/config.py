from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Deployment
    environment: Literal["local", "staging", "production"] = "local"

    # Database
    postgres_user: str = "twp"
    postgres_password: str = "twp_secret"
    postgres_db: str = "thewalkingpet"
    postgres_host: str = "localhost"
    postgres_port: int = 9876

    # JWT
    jwt_secret_key: str = "change_me_to_a_random_secret_key_at_least_32_chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Auth policy
    password_min_length: int = 10
    password_max_length: int = 128

    # Rate limiting. Empty storage URI keeps counters per-process (fine for a
    # single worker); point it at Redis to share them across workers.
    rate_limit_enabled: bool = True
    rate_limit_storage_uri: str = ""
    rate_limit_login: str = "10/minute"
    rate_limit_register: str = "5/hour"
    rate_limit_refresh: str = "30/minute"
    rate_limit_write: str = "60/minute"

    # Storage
    storage_path: str = "./storage/images"
    max_upload_mb: float = 12.0

    # ML
    yolo_model: str = "yolov8m-seg.pt"
    embedding_dim: int = 1024
    model_type: str = "dinov2"

    # Matching. The candidate bounding box is built at this radius, so a
    # declaration may never search wider than this.
    max_search_radius_km: float = 10.0

    # Google OAuth + Firebase
    google_client_id: str = ""
    firebase_credentials_path: str = ""

    # HTTP
    cors_origins: str = ""

    # Background jobs. Exactly one process in the deployment should set this;
    # every extra one double-expands search radii.
    run_scheduler: bool = True

    # Logging
    log_level: str = "INFO"
    log_json: bool = False

    # App
    debug: bool = False

    @field_validator("cors_origins")
    @classmethod
    def _strip_origins(cls, v: str) -> str:
        return v.strip()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
