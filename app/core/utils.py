import requests
from fastapi import HTTPException


def currency_converter(amount: float, from_currency: str, to_currency: str) -> float:
    # API endpoint to get exchange rates
    endpoint = f"https://open.er-api.com/v6/latest/{from_currency}"
    backup_endpoint = f"https://api.exchangerate-api.com/v4/latest/{
        from_currency}"

    # Send a GET request to the API and check if the request was successful
    try:
        response = requests.get(endpoint, timeout=10)
        if not response.status_code == 200:
            response = requests.get(backup_endpoint, timeout=10)
            if not response.status_code == 200:
                raise HTTPException(
                    status_code=500, detail="Failed to retrieve exchange rate")
    except requests.Timeout as e:
        raise HTTPException(
            status_code=500, detail=f"API endpoint timed out. Please try again. \n Error: {e}") from e

    # Parse the response
    data = response.json()
    # Get the exchange rate for the target currency
    exchange_rate = data['rates'][to_currency]

    # Calculate the converted amount
    converted_amount = amount * exchange_rate
    return converted_amount
