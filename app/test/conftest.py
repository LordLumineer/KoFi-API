"""
Test fixtures and utilities for the Ko-fi donation API.

@file: ./app/test/conftest.py
@date: 2024-09-27
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest

from app.core.models import KofiTransaction, KofiUser
from app.main import app
# from app.core.db import get_db
# from app.core import models


# Mock settings
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
def client():
    """
    Fixture to create a TestClient for the FastAPI app.

    Returns:
        TestClient: A TestClient for the FastAPI app.
    """
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """
    Fixture to mock the database session dependency.

    Yields a mock Session object from sqlalchemy.orm, which is returned by get_db().
    The mock is configured to be used as a context manager, so when the test needs
    to access the database, the mock session is returned as an iterator.
    """
    with patch("app.core.db.SessionLocal") as mock:
        mock.return_value = MagicMock()
        yield mock.return_value
