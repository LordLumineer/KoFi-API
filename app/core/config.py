import logging
import warnings
from typing import Literal, Self
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True, extra="ignore"
    )
    PROJECT_NAME: str = "Ko-fi API"
    DATA_RETENTION_DAYS: int = 10
    DATABASE_URL: str = "sqlite:///./KoFi.db"
    ADMIN_SECRET_KEY: str = "changethis"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("ADMIN_SECRET_KEY", self.ADMIN_SECRET_KEY)
        
        return self


settings = Settings()  # type: ignore

logger = logging.getLogger("uvicorn")
if not logger:
    logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s:     %(message)s",
            handlers=[logging.StreamHandler()]  # Output to stdout
        )
    logger = logging.getLogger(__name__)
