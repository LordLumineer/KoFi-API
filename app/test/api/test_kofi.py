"""
Test cases for the Ko-fi donation API endpoints.

@file: ./app/test/api/test_kofi.py
@date: 2024-09-27
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
import copy
import json
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.core.models import KofiTransaction, KofiUser
from app.main import app
from app.test.conftest import basic_mock_transaction, basic_mock_user

client = TestClient(app)

# --------------- Test Webhook Endpoint ---------------


def test_webhook_transaction_success(mock_db_session):  #pylint: disable=W0613, W0621
    """Test receiving a valid Ko-fi transaction through the webhook."""
    transaction_data = {
        "verification_token": "test_token",
        "message_id": "12345",
        "timestamp": "2024-09-25T12:34:56",
        "type": "Donation",
        "is_public": True,
        "from_name": "John Doe",
        "message": "Great work!",
        "amount": "5.00",
        "url": "https://ko-fi.com/some-url",
        "email": "john.doe@example.com",
        "currency": "USD",
        "is_subscription_payment": False,
        "is_first_subscription_payment": False,
        "kofi_transaction_id": "txn_123",
        "shop_items": None,
        "tier_name": None,
        "shipping": None
    }

    response = client.post(
        "/kofi/webhook", data={"data": json.dumps(transaction_data)})
    assert response.status_code == 200
    # mock_db_session.add.assert_called_once()  # BUG


def test_webhook_invalid_json():
    """Test handling invalid JSON in the webhook."""
    response = client.post("/kofi/webhook", data={"data": "invalid-json"})
    print(response.status_code)
    assert response.status_code == 400
    assert "Invalid JSON format" in response.json()["detail"]


def test_webhook_invalid_transaction_data(mock_db_session): #pylint: disable=W0613, W0621
    """Test validation errors for missing fields in the transaction data."""
    invalid_data = {
        "verification_token": "test_token",
        "message_id": "12345",
        # Missing required fields like timestamp, type, etc.
    }

    response = client.post(
        "/kofi/webhook", data={"data": json.dumps(invalid_data)})

    assert response.status_code == 400
    assert "validation errors" in response.json()["detail"]


# --------------- Test Get All Transactions for a User Endpoint ---------------
def test_get_transactions_success(mock_db_session):
    """Test successfully retrieving all transactions for a given user."""
    mock_transaction_1 = copy.copy(basic_mock_transaction)
    mock_transaction_1.verification_token = "basic_token"
    mock_transaction_2 = basic_mock_transaction
    mock_db_session.query(KofiTransaction).filter.return_value.all.return_value = [
        mock_transaction_1, mock_transaction_2]

    response = client.get("/kofi/transactions/test_token")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["verification_token"] == "basic_token"
    assert response.json()[1]["verification_token"] == "test_token"


def test_get_transactions_not_found(mock_db_session):
    """Test retrieving transactions for a user with an invalid verification token."""
    mock_db_session.query(
        KofiTransaction).filter.return_value.all.return_value = []

    response = client.get("/kofi/transactions/invalid_token")

    assert response.status_code == 404
    assert "Invalid verification token" in response.json()["detail"]


# --------------- Test Get Single Transaction Endpoint ---------------
def test_get_transaction_success(mock_db_session):
    """Test retrieving a single transaction by its ID."""
    mock_transaction = basic_mock_transaction
    mock_db_session.query(
        KofiTransaction).filter.return_value.first.return_value = mock_transaction

    response = client.get("/kofi/transactions/test_token/12345")

    assert response.status_code == 200
    assert response.json()["message_id"] == "12345"


def test_get_transaction_not_found(mock_db_session):
    """Test retrieving a single transaction with invalid ID or token."""
    mock_db_session.query(
        KofiTransaction).filter.return_value.first.return_value = None

    response = client.get("/kofi/transactions/invalid_token/txn_123")

    assert response.status_code == 404
    assert "Transaction not found" in response.json()["detail"]


# --------------- Test Get Total Amount of Transactions Endpoint ---------------
@patch("app.api.routes.kofi.currency_converter")
def test_get_total_amount_success(mock_currency_converter, mock_db_session):
    """Test successfully calculating the total amount of donations."""
    mock_transaction1 = copy.copy(basic_mock_transaction)
    mock_transaction1.amount = "10.00"
    mock_transaction1.currency = "USD"
    mock_transaction2 = copy.copy(basic_mock_transaction)
    mock_transaction2.amount = "20.00"
    mock_transaction2.currency = "EUR"

    mock_db_session.query(KofiTransaction).filter.return_value.all.return_value = [
        mock_transaction1, mock_transaction2]
    mock_db_session.query(
        KofiUser).filter.return_value.first.return_value = basic_mock_user
    mock_currency_converter.return_value = 25.0  # Mock conversion of EUR to USD

    response = client.get("/kofi/amount/total/test_token")
    print(response.json())
    assert response.status_code == 200
    assert response.json() == 35.0  # 10 USD + 25 USD (converted from EUR)


def test_get_total_amount_invalid_method():
    """Test handling invalid 'method' parameter for calculating total amount."""
    response = client.get("/kofi/amount/invalid_method/test_token")

    assert response.status_code == 400
    assert "Invalid 'method' parameter" in response.json()["detail"]


def test_get_total_amount_invalid_since_parameter(mock_db_session):
    """Test handling invalid 'since' parameter for calculating recent donations."""
    mock_db_session.query(
        KofiUser).filter.return_value.first.return_value = basic_mock_user
    response = client.get("/kofi/amount/recent/test_token?since=invalid_date")
    print(response.json())
    assert response.status_code == 400
    assert "Invalid 'since' parameter" in response.json()["detail"]
