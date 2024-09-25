"""./app/test/api/test_admin.py"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.core.models import KofiTransaction, KofiUser

client = TestClient(app)

# Mock settings
admin_secret_key = "valid_admin_key"
invalid_admin_secret_key = "invalid_key"

basic_mock_transaction = KofiTransaction(
    verification_token="test_token",
    message_id="12345",
    timestamp="2024-09-25T12:34:56",
    type="Donation",
    is_public=True,
    from_name="John Doe",
    message="Great work!",
    amount="5.00",
    url="https://ko-fi.com/some-url",
    email="john.doe@example.com",
    currency="USD",
    is_subscription_payment=False,
    is_first_subscription_payment=False,
    kofi_transaction_id="txn_123",
    shop_items=None,
    tier_name=None,
    shipping=None
)

basic_mock_user = KofiUser(
    verification_token="test_token",
    data_retention_days=30,
    latest_request_at="2024-09-25T12:34:56",
    prefered_currency="USD"
)

@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to mock settings with valid admin secret key."""
    monkeypatch.setattr("app.core.config.settings.ADMIN_SECRET_KEY", admin_secret_key)


# --------------- Test Get All Transactions ---------------
def test_read_transaction_db_success(mock_settings, mock_db_session):
    """Test successful retrieval of all transactions with a valid admin secret key."""
    mock_transaction = basic_mock_transaction
    mock_db_session.query(KofiTransaction).all.return_value = [mock_transaction]

    response = client.get(f"/admin/db/transactions?admin_secret_key={admin_secret_key}")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    mock_db_session.query(KofiTransaction).all.assert_called_once()


def test_read_transaction_db_invalid_secret_key(mock_settings):
    """Test retrieval failure with an invalid admin secret key."""
    response = client.get(f"/admin/db/transactions?admin_secret_key={invalid_admin_secret_key}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid admin secret key"


# --------------- Test Get All Users ---------------
def test_read_user_db_success(mock_settings, mock_db_session):
    """Test successful retrieval of all users with a valid admin secret key."""
    mock_user = basic_mock_user
    mock_db_session.query(KofiUser).all.return_value = [mock_user]

    response = client.get(f"/admin/db/users?admin_secret_key={admin_secret_key}")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    mock_db_session.query(KofiUser).all.assert_called_once()


def test_read_user_db_invalid_secret_key(mock_settings):
    """Test retrieval failure with an invalid admin secret key."""
    response = client.get(f"/admin/db/users?admin_secret_key={invalid_admin_secret_key}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid admin secret key"
