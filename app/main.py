
from datetime import datetime, timezone
import json

import requests
from fastapi import FastAPI, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler

# from httpx import request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
# from starlette.middleware.cors import CORSMiddleware

from app import models
from app import db as database
from app.db import remove_expired_transactions, run_migrations
from app.config import settings

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=unused-argument, redefined-outer-name
    print("Starting up...")
    # Alembic
    run_migrations()
    # 
    scheduler = BackgroundScheduler()
    scheduler.add_job(remove_expired_transactions, 'cron', hour=0, minute=0)
    scheduler.start()
    yield  # This is when the application code will run
    print("Shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# ----- TRANSACTIONS CRUD -----


@app.post("/webhook")
def receive_kofi_transaction(
    data: str = Form(...), db: Session = Depends(database.get_db)
):
    # Parse the data
    try:
        transaction = json.loads(data)
    except json.JSONDecodeError as e:
        return HTTPException(status_code=400, detail=f"Invalid JSON format, error: {e}" + str(e))

    # Validate the data
    try:
        transaction = models.KofiTransactionSchema(**transaction)
    except ValueError as e:
        return HTTPException(status_code=400, detail=str(e))

    # To SqlAlchemy
    transaction = models.KofiTransaction(**transaction.model_dump())
    try:
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig)) from e

    user = db.query(models.KofiUser).filter(
        models.KofiUser.verification_token == transaction.verification_token
    ).first()
    if not user:
        create_user(transaction.verification_token, db=db)

    return HTMLResponse(status_code=200)


@app.get("/transactions/{verification_token}")
def get_transactions(verification_token: str, db: Session = Depends(database.get_db)):
    transactions = db.query(models.KofiTransaction).filter(
        models.KofiTransaction.verification_token == verification_token
    ).all()
    return transactions


@app.get("/transactions/{verification_token}/{transaction_id}", response_model=models.KofiTransactionSchema)
def get_transaction(verification_token: str, transaction_id: str, db: Session = Depends(database.get_db)):
    transaction = db.query(models.KofiTransaction).filter(
        models.KofiTransaction.verification_token == verification_token,
        models.KofiTransaction.message_id == transaction_id
    ).first()
    return transaction


@app.get("/ammout/{method}/{verification_token}", response_model=float)
def get_transactions_total(
    method: str,
    verification_token: str,
    since: str | None = None,
    currency: str | None = None,
    db: Session = Depends(database.get_db)
):
    try:
        method = method.lower()
        assert method in [
            'total', 'recent', 'latest'], "Invalid 'method' parameter. Expected 'total', 'recent', or 'latest'."
    except AssertionError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid 'method' parameter ({method}). Expected 'total', 'recent', or 'latest'."
        ) from e

    user = db.query(models.KofiUser).filter(
        models.KofiUser.verification_token == verification_token
    ).first()

    if not user:
        raise HTTPException(
            status_code=404, detail="Invalid verification token")

    data = {}
    match method:
        case 'total':
            data = db.query(models.KofiTransaction).filter(
                models.KofiTransaction.verification_token == verification_token
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
            data = db.query(models.KofiTransaction).filter(
                models.KofiTransaction.verification_token == verification_token,
                models.KofiTransaction.timestamp >= since
            ).all()
            try:
                user.latest_request_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                db.commit()
                db.refresh(user)
            except IntegrityError as e:
                db.rollback()
                raise HTTPException(status_code=400, detail=str(e.orig)) from e

        case 'latest':
            data = db.query(models.KofiTransaction).filter(
                models.KofiTransaction.verification_token == verification_token
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
            total += currency_converter(amount, saved_currency, currency.upper())
    return total

# ----- USER CRUD -----


@app.post("/users/{verification_token}")
def create_user(
    verification_token: str,
    data_retention_days: int | None = None,
    db: Session = Depends(database.get_db)

):
    user = models.KofiUser(
        verification_token=verification_token,
        data_retention_days=data_retention_days or settings.DATA_RETENTION_DAYS,
        latest_request_at=datetime.now(
            timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig)) from e
    return user


@app.get("/users/{verification_token}")
def get_user(verification_token: str, db: Session = Depends(database.get_db)):
    user = db.query(models.KofiUser).filter(
        models.KofiUser.verification_token == verification_token
    ).first()
    if not user:
        raise HTTPException(
            status_code=404, detail="Invalid verification token")
    return user


@app.patch("/users/{verification_token}")
def update_expiration(
    verification_token: str,
    days: int,
    db: Session = Depends(database.get_db),
):
    user = db.query(models.KofiUser).filter(
        models.KofiUser.verification_token == verification_token
    ).first()
    if not user:
        raise HTTPException(
            status_code=404, detail="Invalid verification token")
    try:
        user.data_retention_days = days
        db.commit()
        db.refresh(user)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig)) from e
    return user


@app.delete("/users/{verification_token}")
def delete_user(verification_token: str, inculde_transactions: bool = True, db: Session = Depends(database.get_db)):
    user = db.query(models.KofiUser).filter(
        models.KofiUser.verification_token == verification_token
    ).first()
    if not user:
        raise HTTPException(
            status_code=404, detail="Invalid verification token")
    user.delete()
    db.commit()
    if inculde_transactions:
        transactions = db.query(models.KofiTransaction).filter(
            models.KofiTransaction.verification_token == verification_token
        )
        transactions.delete()
        db.commit()
    return {"message": "User deleted successfully"}


# ----- DEBUG -----
@app.get("/ping")
def ping():
    return "pong"


@app.get("/db/transactions", response_model=list[models.KofiTransactionSchema])
def read_transaction_db(db: Session = Depends(database.get_db)):
    return db.query(models.KofiTransaction).all()


@app.get("/db/users", response_model=list[models.KofiUsreSchema])
def read_user_db(db: Session = Depends(database.get_db)):
    return db.query(models.KofiUser).all()

# ----- UTILITY -----


def currency_converter(amount: float, from_currency: str, to_currency: str) -> float:
    # API endpoint to get exchange rates
    endpoint = f"https://open.er-api.com/v6/latest/{from_currency}"
    backup_endpoint = f"https://api.exchangerate-api.com/v4/latest/{
        from_currency}"

    # Send a GET request to the API and check if the request was successful
    response = requests.get(endpoint)
    if not response.status_code == 200:
        response = requests.get(backup_endpoint)
        if not response.status_code == 200:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve exchange rate")

    # Parse the response
    data = response.json()
    # Get the exchange rate for the target currency
    exchange_rate = data['rates'][to_currency]

    # Calculate the converted amount
    converted_amount = amount * exchange_rate
    return converted_amount
