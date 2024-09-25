"""./app/test/core/test_models.py"""
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
import pytest
from pydantic import ValidationError
from app.core.config import settings
from app.core.models import KofiTransactionSchema, KofiUserSchema, KofiTransaction, KofiUser


# --------------- Tests for Pydantic Schemas ----------------

def test_kofi_transaction_schema_success():
    """Test successful validation of KofiTransactionSchema."""
    transaction_data = {
        "verification_token": "test_token",
        "message_id": "12345",
        "timestamp": "2024-09-25T12:34:56",
        "type": "Donation",
        "is_public": True,
        "from_name": "John Doe",
        "message": "Keep up the good work!",
        "amount": "5.00",
        "url": "https://ko-fi.com/some-url",
        "email": "johndoe@example.com",
        "currency": "USD",
        "is_subscription_payment": False,
        "is_first_subscription_payment": False,
        "kofi_transaction_id": "txn_123",
        "shop_items": [],
        "tier_name": None,
        "shipping": {}
    }

    schema = KofiTransactionSchema(**transaction_data)
    assert schema.verification_token == "test_token"
    assert schema.message_id == "12345"
    assert schema.amount == "5.00"
    assert schema.is_public is True
    assert schema.model_dump()["shipping"] == {}


def test_kofi_transaction_schema_invalid_data():
    """Test KofiTransactionSchema with invalid data."""
    invalid_transaction_data = { # Missing required fields
        "verification_token": "test_token",
        "message_id": "12345"
    }

    with pytest.raises(ValidationError):
        KofiTransactionSchema(**invalid_transaction_data)


def test_kofi_user_schema_success():
    """Test successful validation of KofiUserSchema."""
    user_data = {
        "verification_token": "user_token",
        # "data_retention_days": 30,
        "latest_request_at": "2024-09-25T12:00:00",
        # "prefered_currency": "USD",
    }

    schema = KofiUserSchema(**user_data)
    assert schema.verification_token == "user_token"
    assert schema.data_retention_days == 30
    assert schema.latest_request_at == "2024-09-25T12:00:00"
    assert schema.prefered_currency == "USD"


def test_kofi_user_schema_invalid_data():
    """Test KofiUserSchema with invalid data."""
    invalid_user_data = {
        "verification_token": "user_token",
        "data_retention_days": "thirty",  # Invalid type
        "latest_request_at": "2024-09-25T12:00:00",
        "prefered_currency": "USD",
    }

    with pytest.raises(ValidationError):
        KofiUserSchema(**invalid_user_data)


# --------------- Tests for SQLAlchemy ORM Models (Mocked DB) ---------------


def test_kofi_transaction_model_defaults():
    """Test that KofiTransaction model has correct field types and defaults."""
    # Mocking a SQLAlchemy session
    mock_session = MagicMock(spec=Session)

    # Creating a KofiTransaction instance
    transaction = KofiTransaction(
        verification_token="test_token",
        message_id="12345",
        timestamp="2024-09-25T12:34:56",
        type="Donation",
        is_public=True,
        from_name="John Doe",
        message="Keep up the good work!",
        amount="5.00",
        url="https://ko-fi.com/some-url",
        email="johndoe@example.com",
        currency="USD",
        is_subscription_payment=False,
        is_first_subscription_payment=False,
        kofi_transaction_id="txn_123",
        shop_items=None,  # Pickled list
        tier_name=None,
        shipping=None  # Pickled dict
    )

    # Assert values are correctly mapped
    assert transaction.verification_token == "test_token"
    assert transaction.shop_items is None
    assert transaction.shipping is None


def test_kofi_user_model_defaults():
    """Test that KofiUser model has correct defaults for specific fields."""
    # Mocking a SQLAlchemy session
    mock_session = MagicMock(spec=Session)

    # Creating a KofiUser instance
    user = KofiUser(**KofiUserSchema(
        verification_token="user_token",
        latest_request_at="2024-09-25T12:00:00"
    ).model_dump())

    # Assert that default values are set correctly
    assert user.verification_token == "user_token"
    assert user.data_retention_days == 30  # From settings
    assert user.prefered_currency == "USD"  # Default value
