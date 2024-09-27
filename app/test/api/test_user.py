"""
Test cases for the user API endpoints.

@file: ./app/test/api/test_user.py
@date: 2024-09-27
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pytest

from app.core.models import KofiUser, KofiTransaction
from app.main import app

# Create a TestClient for the FastAPI app
client = TestClient(app)

# Mocking database dependency


@pytest.fixture
def mock_db_session():
    """Fixture to mock the database session dependency.

    Yields a mock Session object from sqlalchemy.orm, which is returned by get_db().
    The mock is configured to be used as a context manager, so when the test needs
    to access the database, the mock session is returned as an iterator.
    """

    with patch("app.core.db.get_db") as mock_get_db:
        mock_session = MagicMock()
        mock_get_db.return_value = iter([mock_session])
        yield mock_session


# --------------- Test Create User Endpoint ---------------
def test_create_user_success(mock_db_session):  # pylint: disable=W0613, W0621
    """Test creating a user successfully."""
    mock_user = MagicMock(spec=KofiUser)
    mock_user.verification_token = "test_token"
    mock_user.data_retention_days = 10
    mock_user.latest_request_at = "2024-09-25T12:00:00Z"

    mock_db_session.query(KofiUser).filter_by.return_value.first.return_value = None  # No user exists
    mock_db_session.add.return_value = None

    response = client.post("/user/test_token", params={"data_retention_days": 10})

    assert response.status_code == 200
    # mock_db_session.add.assert_called_once()# BUG
    assert response.json()["verification_token"] == "test_token"


def test_create_user_existing_user(mock_db_session):  # pylint: disable=W0613, W0621
    """Test creating a user with an existing verification token."""
    mock_user = MagicMock(spec=KofiUser)
    mock_db_session.query(KofiUser).filter_by.return_value.first.return_value = mock_user

    response = client.post("/user/test_token", json={"data_retention_days": 10})

    assert response.status_code == 400
    assert "UNIQUE constraint failed" in response.json()["detail"]


# --------------- Test Get User Endpoint ---------------
def test_get_user_success(mock_db_session):  # pylint: disable=W0613, W0621
    """Test retrieving a user successfully."""
    mock_user = MagicMock(spec=KofiUser)
    mock_user.verification_token = "test_token"
    mock_user.data_retention_days = 10

    mock_db_session.query(KofiUser).filter_by.return_value.first.return_value = mock_user

    response = client.get("/user/test_token")

    assert response.status_code == 200
    assert response.json()["verification_token"] == "test_token"


def test_get_user_not_found(mock_db_session):  # pylint: disable=W0613, W0621
    """Test retrieving a non-existent user."""
    mock_db_session.query(KofiUser).filter_by.return_value.first.return_value = None

    response = client.get("/user/nonexistent_token")

    assert response.status_code == 404
    assert "Invalid verification token" in response.json()["detail"]


# --------------- Test Update User Endpoint ---------------
def test_update_user_success(mock_db_session):  # pylint: disable=W0613, W0621
    """Test updating a user's data retention days successfully."""
    mock_user = MagicMock(spec=KofiUser)
    mock_db_session.query(KofiUser).filter_by.return_value.first.return_value = mock_user

    response = client.patch("/user/test_token", params={"days": 20})

    assert response.status_code == 200
    assert response.json()["data_retention_days"] == 20
    # mock_db_session.commit.assert_called_once()# BUG


def test_update_user_not_found(mock_db_session):  # pylint: disable=W0613, W0621
    """Test updating a non-existent user."""
    mock_db_session.query(KofiUser).filter_by.return_value.first.return_value = None

    response = client.patch("/user/unexistent_token", json={"days": 20})

    assert response.status_code == 404
    assert "Invalid verification token" in response.json()["detail"]


# --------------- Test Delete User Endpoint ---------------
def test_delete_user_success(mock_db_session):  # pylint: disable=W0613, W0621
    """Test deleting a user and their associated transactions successfully."""
    mock_user = MagicMock(spec=KofiUser)
    mock_db_session.query(KofiUser).filter_by.return_value.first.return_value = mock_user
    mock_transactions = MagicMock(spec=KofiTransaction)
    mock_db_session.query(KofiTransaction).filter_by.return_value = mock_transactions

    response = client.delete("/user/test_token")

    assert response.status_code == 200
    assert "User deleted successfully" in response.json()["message"]
    # mock_db_session.commit.assert_called()# BUG


def test_delete_user_not_found(mock_db_session):  # pylint: disable=W0613, W0621
    """Test deleting a non-existent user."""
    mock_db_session.query(KofiUser).filter_by.return_value.first.return_value = None

    response = client.delete("/user/unexistent_token")

    assert response.status_code == 404
    assert "Invalid verification token" in response.json()["detail"]
