from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    postgres_user: str = "twp"
    postgres_password: str = "twp_secret"
    postgres_db: str = "thewalkingpet"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # JWT
    jwt_secret_key: str = "change_me_to_a_random_secret_key_at_least_32_chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Storage
    storage_path: str = "./storage/images"

    # ML
    model_checkpoint_path: str = "./models/triplet_net.pt"
    yolo_model: str = "yolov8m-seg.pt"
    embedding_dim: int = 256

    # Google OAuth + Firebase
    google_client_id: str = ""
    firebase_credentials_path: str = ""

    # App
    debug: bool = False

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
