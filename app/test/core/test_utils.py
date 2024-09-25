"""./app/test/core/test_utils.py"""
import httpx
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.core.utils import currency_converter


# Test for a successful API call to the primary endpoint
@patch("httpx.get")
def test_currency_converter_success(mock_get):
    """Test currency conversion with a valid API response."""

    # Mock the response from the primary API
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "rates": {"USD": 1.2}  # Example conversion rate from source to USD
    }
    mock_get.return_value = mock_response

    # Call the function with the mocked response
    amount = currency_converter(100, "EUR", "USD")

    # Check that the conversion is correct
    assert amount == 120.0
    mock_get.assert_called_once_with(
        "https://open.er-api.com/v6/latest/EUR", timeout=1)


# Test when the primary API fails and the backup API is used
@patch("httpx.get")
def test_currency_converter_backup_api(mock_get):
    """Test currency conversion using the backup API when the primary API fails."""

    # Mock the primary API to fail and the backup API to succeed
    mock_failed_response = MagicMock()
    mock_failed_response.status_code = 500

    mock_successful_response = MagicMock()
    mock_successful_response.status_code = 200
    mock_successful_response.json.return_value = {
        "rates": {"USD": 1.5}
    }

    # First call fails, second call succeeds
    mock_get.side_effect = [mock_failed_response, mock_successful_response]

    # Call the function and check the conversion
    amount = currency_converter(100, "EUR", "USD")
    assert amount == 150.0

    # Check that the primary and backup API were called
    assert mock_get.call_count == 2
    mock_get.assert_any_call(
        "https://open.er-api.com/v6/latest/EUR", timeout=1)
    mock_get.assert_any_call(
        "https://api.exchangerate-api.com/v4/latest/EUR", timeout=5)


# Test when both primary and backup APIs fail
@patch("httpx.get")
def test_currency_converter_api_failure(mock_get):
    """Test currency conversion when both primary and backup APIs fail."""

    # Mock both APIs to fail
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response

    # Call the function and check that it raises HTTPException
    with pytest.raises(HTTPException) as exc_info:
        currency_converter(100, "EUR", "USD")

    assert exc_info.value.status_code == 500
    assert "Failed to retrieve exchange rate" in str(exc_info.value.detail)

    # Check that both APIs were called
    assert mock_get.call_count == 2
    mock_get.assert_any_call(
        "https://open.er-api.com/v6/latest/EUR", timeout=1)
    mock_get.assert_any_call(
        "https://api.exchangerate-api.com/v4/latest/EUR", timeout=5)


# Test when the API call times out
@patch("httpx.get")
def test_currency_converter_timeout(mock_get):
    """Test currency conversion handling a timeout."""

    # Mock a timeout exception
    mock_get.side_effect = httpx.TimeoutException("Request timed out")

    # Call the function and check that it raises HTTPException
    with pytest.raises(HTTPException) as exc_info:
        currency_converter(100, "EUR", "USD")

    assert exc_info.value.status_code == 500
    assert "API endpoint timed out" in str(exc_info.value.detail)

    # Check that the primary API was called and the timeout was handled
    mock_get.assert_called_once_with(
        "https://open.er-api.com/v6/latest/EUR", timeout=1)
