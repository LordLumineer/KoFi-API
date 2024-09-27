"""
Utility functions for the Ko-fi donation API.

@file: ./app/core/utils.py
@date: 2024-09-22
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
import os
import httpx
from fastapi import HTTPException


def currency_converter(amount: float, from_currency: str, to_currency: str) -> float:
    """
    Convert a given amount from one currency to another.

    Args:
        amount (float): The amount to convert.
        from_currency (str): The currency to convert from.
        to_currency (str): The currency to convert to.

    Returns:
        float: The converted amount.

    Raises:
        HTTPException: If the API endpoint timed out or failed to retrieve the
            exchange rate.
    """
    # API endpoint to get exchange rates
    endpoint = f"https://open.er-api.com/v6/latest/{from_currency}"
    backup_endpoint = f"https://api.exchangerate-api.com/v4/latest/{
        from_currency}"

    # Send a GET request to the API and check if the request was successful
    try:
        response = httpx.get(endpoint, timeout=1)
        if not response.status_code == 200:
            response = httpx.get(backup_endpoint, timeout=5)
            if not response.status_code == 200:
                raise HTTPException(
                    status_code=500, detail="Failed to retrieve exchange rate")
    except httpx.TimeoutException as e:
        raise HTTPException(
            status_code=500, detail=f"API endpoint timed out. Please try again. \n Error: {e}") from e

    # Parse the response
    data = response.json()
    # Get the exchange rate for the target currency
    exchange_rate = data['rates'][to_currency]

    # Calculate the converted amount
    converted_amount = amount * exchange_rate
    return converted_amount


def remove_file(file_path: str):
    """Background task to delete the file after sending it."""
    if os.path.exists(file_path):
        os.remove(file_path)
