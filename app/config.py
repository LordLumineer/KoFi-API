import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True, extra="ignore"
    )
    PROJECT_NAME: str = "Ko-fi API"
    DATA_RETENTION_DAYS: int = 10
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./KoFi.db")


settings = Settings()  # type: ignore
