"""./app/test/conftest.py"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
# from app.core.db import get_db
# from app.core import models


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    with patch("app.core.db.SessionLocal") as mock:
        mock.return_value = MagicMock()
        yield mock.return_value
