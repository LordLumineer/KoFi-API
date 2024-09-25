"""
Configuration for Ko-fi donation API.

@file: ./app/core/config.py
@date: 2024-09-22
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
import logging
import warnings
from typing import Literal, Self
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration for Ko-fi donation API.

    Attributes:
        PROJECT_NAME: str
            The name of the project.
        DATA_RETENTION_DAYS: int
            The number of days to retain data.
        DATABASE_URL: str
            The URL of the database.
        ADMIN_SECRET_KEY: str
            The secret key to authorize admin operations.
        ENVIRONMENT: Literal["local", "staging", "production"]
            The environment to run in.

    Methods:
        _check_default_secret(var_name, value)
            Check if the value of a secret variable is the default and warn/error accordingly.
        _enforce_non_default_secrets()
            Enforce that the default secrets are not used in non-local environments.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True, extra="ignore"
    )
    PROJECT_NAME: str = "Ko-fi API"
    DATA_RETENTION_DAYS: int = 10
    DATABASE_URL: str = "sqlite:///./KoFi.db"
    ADMIN_SECRET_KEY: str = "changethis"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        """
        Check if the value of a secret variable is the default and warn/error accordingly.

        Args:
            var_name (str): The name of the secret variable.
            value (str | None): The value of the secret variable.

        Raises:
            ValueError: 
                If the value of the secret variable is the default and the environment is not local.
        """
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
        """
        Enforce that the default secrets are not used in non-local environments.

        This model validator function will check if the default secrets are used and
        warn/error accordingly. This is to ensure that the API is not deployed with
        the default secrets.
        """
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
