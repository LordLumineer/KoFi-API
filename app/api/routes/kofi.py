import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.routes.user import create_user
from app.core.db import get_db
from app.core.models import KofiTransactionSchema, KofiTransaction, KofiUser
from app.core.utils import currency_converter


router = APIRouter()


@router.post("/webhook")
def receive_kofi_transaction(
    data: str = Form(...), db: Session = Depends(get_db)
):
    # Parse the data
    try:
        transaction = json.loads(data)
    except json.JSONDecodeError as e:
        return HTTPException(status_code=400, detail=f"Invalid JSON format, error: {e}" + str(e))

    # Validate the data
    try:
        transaction = KofiTransactionSchema(**transaction)
    except ValueError as e:
        return HTTPException(status_code=400, detail=str(e))

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
    transactions = db.query(KofiTransaction).filter(
        KofiTransaction.verification_token == verification_token
    ).all()
    return transactions


@router.get("/transactions/{verification_token}/{transaction_id}", response_model=KofiTransactionSchema)
def get_transaction(verification_token: str, transaction_id: str, db: Session = Depends(get_db)):
    transaction = db.query(KofiTransaction).filter(
        KofiTransaction.verification_token == verification_token,
        KofiTransaction.message_id == transaction_id
    ).first()
    return transaction


@router.get("/ammout/{method}/{verification_token}", response_model=float)
def get_transactions_total(
    method: str,
    verification_token: str,
    since: str | None = None,
    currency: str | None = None,
    db: Session = Depends(get_db)
):
    try:
        method = method.lower()
        assert method in [
            'total', 'recent', 'latest'], "Invalid 'method' parameter. Expected 'total', 'recent', or 'latest'."
    except AssertionError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid 'method' parameter ({method}). Expected 'total', 'recent', or 'latest'.") from e

    user = db.query(KofiUser).filter(
        KofiUser.verification_token == verification_token
    ).first()

    if not user:
        raise HTTPException(
            status_code=404, detail="Invalid verification token")

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
            try:
                user.latest_request_at = datetime.now(
                    timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                db.commit()
                db.refresh(user)
            except IntegrityError as e:
                db.rollback()
                raise HTTPException(status_code=400, detail=str(e.orig)) from e

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
