"""./app/test/core/test_config.py"""
from unittest.mock import patch
import pytest
import warnings
from pydantic import ValidationError
from app.core.config import Settings


# --------------- Test default settings ---------------
def test_default_settings():
    """Test that default settings are correctly initialized."""
    settings = Settings()

    assert settings.PROJECT_NAME == "Ko-fi API"
    assert settings.DATA_RETENTION_DAYS == 30
    assert settings.DATABASE_URL == "sqlite:///./KoFi.db"
    assert settings.ADMIN_SECRET_KEY == "changethis"
    assert settings.ENVIRONMENT == "local"


# --------------- Test loading from environment variables ---------------
@patch.dict('os.environ', {
    "PROJECT_NAME": "Test Project",
    "DATA_RETENTION_DAYS": "20",
    "DATABASE_URL": "postgres://localhost/test",
    "ADMIN_SECRET_KEY": "newsecretkey",
    "ENVIRONMENT": "staging"
})
def test_load_from_env_vars():
    """Test that settings are correctly loaded from environment variables."""
    settings = Settings()

    assert settings.PROJECT_NAME == "Test Project"
    assert settings.DATA_RETENTION_DAYS == 20
    assert settings.DATABASE_URL == "postgres://localhost/test"
    assert settings.ADMIN_SECRET_KEY == "newsecretkey"
    assert settings.ENVIRONMENT == "staging"


# --------------- Test secret enforcement in 'local' environment ---------------
def test_secret_warning_local_env():
    """Test that a warning is raised in the 'local' environment when the secret key is not changed."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        settings = Settings(ENVIRONMENT="local", ADMIN_SECRET_KEY="changethis")
        
        # Ensure that a warning was raised
        assert len(w) == 1
        assert "The value of ADMIN_SECRET_KEY is \"changethis\"" in str(w[-1].message)


# --------------- Test secret enforcement in 'staging' or 'production' environment ---------------
def test_secret_error_non_local_env():
    """Test that a ValueError is raised in 'staging' or 'production' environment when the secret key is not changed."""
    with pytest.raises(ValueError, match="The value of ADMIN_SECRET_KEY is \"changethis\""):
        Settings(ENVIRONMENT="staging", ADMIN_SECRET_KEY="changethis")

    with pytest.raises(ValueError, match="The value of ADMIN_SECRET_KEY is \"changethis\""):
        Settings(ENVIRONMENT="production", ADMIN_SECRET_KEY="changethis")


# --------------- Test secret key enforcement success ---------------
def test_secret_success_non_local_env():
    """Test that no errors are raised in 'staging' or 'production' when the secret key is changed."""
    settings = Settings(ENVIRONMENT="staging", ADMIN_SECRET_KEY="supersecret")
    assert settings.ADMIN_SECRET_KEY == "supersecret"

    settings = Settings(ENVIRONMENT="production", ADMIN_SECRET_KEY="supersecret")
    assert settings.ADMIN_SECRET_KEY == "supersecret"
