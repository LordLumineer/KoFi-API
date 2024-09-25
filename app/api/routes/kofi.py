"""
Ko-fi webhook API endpoints (https://ko-fi.com/manage/webhooks).
And data retrieval endpoints, Main API.

@file: ./app/api/routes/kofi.py
@date: 2024-09-22
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.routes.user import create_user, get_user, update_user
from app.core.db import get_db
from app.core.models import KofiTransactionSchema, KofiTransaction, KofiUser
from app.core.utils import currency_converter


router = APIRouter()


@router.post("/webhook")
def receive_kofi_transaction(
    data: str = Form(...), db: Session = Depends(get_db)
):
    """
    Receive a Ko-fi transaction from the Ko-fi webhook API, and store it in the database.

    Args:
        data: The transaction data, as a stringified JSON object.
        db: The database session, provided by the dependency injection system.

    Returns:
        A HTML response with a status code of 200, 
        indicating that the transaction was stored successfully.

    Raises:
        HTTPException: If the transaction data is invalid, 
            or if the transaction could not be stored in the database.
    """
    # Parse the data
    try:
        transaction = json.loads(data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format, error: {e}" + str(e)) from e

    # Validate the data
    try:
        transaction = KofiTransactionSchema(**transaction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # To SqlAlchemy
    transaction = KofiTransaction(**transaction.model_dump())
    try:
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig)) from e

    user = db.query(KofiUser).filter(
        KofiUser.verification_token == transaction.verification_token
    ).first()
    if not user:
        create_user(transaction.verification_token, db=db)

    return HTMLResponse(status_code=200)


@router.get("/transactions/{verification_token}")
def get_transactions(verification_token: str, db: Session = Depends(get_db)):
    """
    Get all transactions for a given user.

    Args:
        verification_token: The user's verification token.
        db: The database session, provided by the dependency injection system.

    Returns:
        A list of all transactions for the user, represented as KofiTransactionSchema.

    Raises:
        HTTPException: If the provided verification token is invalid.
    """
    transactions = db.query(KofiTransaction).filter(
        KofiTransaction.verification_token == verification_token
    ).all()
    if not transactions:
        raise HTTPException(status_code=404, detail="Invalid verification token")
    return transactions


@router.get(
    "/transactions/{verification_token}/{transaction_id}",
    response_model=KofiTransactionSchema
)
def get_transaction(verification_token: str, transaction_id: str, db: Session = Depends(get_db)):
    """
    Get a single transaction by its verification token and message ID.

    Args:
        verification_token: The verification token of the user that made the transaction.
        transaction_id: The message ID of the transaction.

    Returns:
        The transaction object, or 404 if not found.
    """
    transaction = db.query(KofiTransaction).filter(
        KofiTransaction.verification_token == verification_token,
        KofiTransaction.message_id == transaction_id
    ).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.get("/amount/{method}/{verification_token}", response_model=float)
def get_transactions_total(
    method: str,
    verification_token: str,
    since: str | None = None,
    currency: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Get the total amount of donations for a given user, depending on the 'method' parameter.

    'total' returns the total amount of all donations for the user.
    'recent' returns the total amount of donations since the 'since' parameter (ISO 8601 format).
    'latest' returns the total amount of the latest donation.

    If the 'currency' parameter is not provided, the user's preferred currency will be used.

    :param method: The method to use for calculating the total amount of donations.
    :param verification_token: The user's verification token.
    :param since: The date and time to start calculating the total amount from.
    :param currency: The currency to convert the amounts to.
    :returns: The total amount of donations.
    """
    try:
        method = method.lower()
        if method not in ['total', 'recent', 'latest']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid 'method' parameter ({method}). Expected 'total', 'recent', or 'latest'.")
    except AssertionError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid 'method' parameter ({method}). Expected 'total', 'recent', or 'latest'.") from e

    user = get_user(verification_token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid verification token")

    data = {}
    match method:
        case 'total':
            data = db.query(KofiTransaction).filter(
                KofiTransaction.verification_token == verification_token
            ).all()

        case 'recent':
            if since:
                try:
                    datetime.fromisoformat(since)
                except (ValueError, TypeError) as e:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid 'since' parameter. Expected ISO 8601 format."
                    ) from e
            else:
                since = user.latest_request_at
            data = db.query(KofiTransaction).filter(
                KofiTransaction.verification_token == verification_token,
                KofiTransaction.timestamp >= since
            ).all()
            update_user(
                verification_token,
                latest_request_at=datetime.now(
                    timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                db=db
            )

        case 'latest':
            data = db.query(KofiTransaction).filter(
                KofiTransaction.verification_token == verification_token
            ).all()
            latest = data[0]
            for d in data:
                if d.timestamp > latest.timestamp:
                    latest = d
            data = [latest]
        case _:
            return 0

    if not currency:
        currency = user.prefered_currency

    currencies = {}
    for transaction in data:
        # Conversion str to float
        amount = 0
        try:
            amount = float(transaction.amount)
        except ValueError:
            continue
        # register currency
        if transaction.currency not in currencies:
            currencies[f"{transaction.currency}"] = 0
        currencies[f"{transaction.currency}"] += amount

    # Convert currencies
    total = 0
    for saved_currency, amount in currencies.items():
        if saved_currency == currency:
            total += amount
        else:
            total += currency_converter(amount,
                                        saved_currency, currency.upper())
    return total
