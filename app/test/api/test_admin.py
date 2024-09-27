"""
These tests check the correctness of the admin endpoints.

@file: ./app/test/api/test_admin.py
@date: 2024-09-27
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.models import KofiTransaction, KofiUser
from app.test.conftest import basic_mock_transaction, basic_mock_user

client = TestClient(app)

# Mock settings
ADMIN_SECRET_KEY = "valid_admin_key"
INVALID_ADMIN_SECRET_KEY = "invalid_admin_key"

@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to mock settings with valid admin secret key."""
    monkeypatch.setattr("app.core.config.settings.ADMIN_SECRET_KEY", ADMIN_SECRET_KEY)


# --------------- Test Get All Transactions ---------------
def test_read_transaction_db_success(mock_settings, mock_db_session): #pylint: disable=W0613, W0621
    """Test successful retrieval of all transactions with a valid admin secret key."""
    mock_transaction = basic_mock_transaction
    mock_db_session.query(KofiTransaction).all.return_value = [mock_transaction]

    response = client.get(f"/admin/db/transactions?admin_secret_key={ADMIN_SECRET_KEY}")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    mock_db_session.query(KofiTransaction).all.assert_called_once()


def test_read_transaction_db_invalid_secret_key(mock_settings): #pylint: disable=W0613, W0621
    """Test retrieval failure with an invalid admin secret key."""
    response = client.get(f"/admin/db/transactions?admin_secret_key={INVALID_ADMIN_SECRET_KEY}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid admin secret key"


# --------------- Test Get All Users ---------------
def test_read_user_db_success(mock_settings, mock_db_session): #pylint: disable=W0613, W0621
    """Test successful retrieval of all users with a valid admin secret key."""
    mock_user = basic_mock_user
    mock_db_session.query(KofiUser).all.return_value = [mock_user]

    response = client.get(f"/admin/db/users?admin_secret_key={ADMIN_SECRET_KEY}")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    mock_db_session.query(KofiUser).all.assert_called_once()


def test_read_user_db_invalid_secret_key(mock_settings): #pylint: disable=W0613, W0621
    """Test retrieval failure with an invalid admin secret key."""
    response = client.get(f"/admin/db/users?admin_secret_key={INVALID_ADMIN_SECRET_KEY}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid admin secret key"
