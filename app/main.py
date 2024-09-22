
from datetime import datetime, timezone
import json

import requests
from fastapi import FastAPI, Depends, File, Form, UploadFile
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
    """Lifespan context for the application.

    This is an async context manager that will be called when the application is
    starting up or shutting down. It is used to perform tasks that should happen
    once, such as setting up the database or scheduling periodic tasks.

    The `yield` statement is where the application code will be run. The code
    above the `yield` is run when the application is starting up, and the code
    below the `yield` is run when the application is shutting down.

    """
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
    """
    Handles incoming webhook request from Ko-fi and stores the transaction in the database.

    The request body should contain a JSON object with the following keys:
        - `verification_token`: The verification token for the user.
        - `message_id`: The ID of the message.
        - `timestamp`: The timestamp of the message.
        - `type`: The type of the message (e.g. "Donation", "Subscription", etc.).
        - `is_public`: Whether the message is public or not.
        - `from_name`: The name of the user who sent the message.
        - `message`: The message itself.
        - `amount`: The amount of the message.
        - `url`: The URL of the message.
        - `email`: The email of the user who sent the message.
        - `currency`: The currency of the message.
        - `is_subscription_payment`: Whether the message is a subscription payment or not.
        - `is_first_subscription_payment`: Whether the message is the first subscription payment or not.
        - `kofi_transaction_id`: The ID of the transaction in Ko-fi.
        - `shop_items`: A list of items purchased in the message.
        - `tier_name`: The name of the tier purchased in the message.
        - `shipping`: A dictionary containing the shipping information for the message.

    If the request body is invalid, it returns a 400 error with a JSON object containing the following key:
        - `detail`: A string describing the error.

    If the request is successful, it returns a 200 response with a JSON object containing the following key:
        - `message`: A string describing the result of the request.
    """
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
    """
    Returns a list of KofiTransaction objects associated with the given verification token.

    Args:
        verification_token (str): The verification token to filter transactions by.

    Returns:
        A list of KofiTransaction objects.
    """
    transactions = db.query(models.KofiTransaction).filter(
        models.KofiTransaction.verification_token == verification_token
    ).all()
    return transactions


@app.get("/transactions/{verification_token}/{transaction_id}", response_model=models.KofiTransactionSchema)
def get_transaction(verification_token: str, transaction_id: str, db: Session = Depends(database.get_db)):
    """
    Returns a KofiTransaction object associated with the given verification token and transaction ID.

    Args:
        verification_token (str): The verification token to filter transactions by.
        transaction_id (str): The transaction ID to filter transactions by.

    Returns:
        A KofiTransaction object.
    """
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
    """
    Returns the total amount of transactions filtered by the given method and verification token.

    Args:
        method (str): The method to filter transactions by. Expected 'total', 'recent', or 'latest'.
        verification_token (str): The verification token to filter transactions by.
        since (str | None): The timestamp to filter transactions by. Optional if using 'latest' method.
        currency (str | None): The currency to filter transactions by. Optional if using 'latest' method.

    Returns:
        The total amount of transactions filtered by the given method and verification token as a float.
    """
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
                user.latest_request_at = datetime.now(
                    timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
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
            total += currency_converter(amount,
                                        saved_currency, currency.upper())
    return total

# ----- USER CRUD -----


@app.post("/users/{verification_token}")
def create_user(
    verification_token: str,
    data_retention_days: int | None = None,
    db: Session = Depends(database.get_db)

):
    """
    Creates a new user in the database.

    Args:
        verification_token (str): The verification token for the user.
        data_retention_days (int | None, optional): The number of days to retain transaction data for. Defaults to DATA_RETENTION_DAYS in the settings if not provided.

    Returns:
        A KofiUser object with the newly created user.

    Raises:
        HTTPException: 400 if the verification token already exists in the database.
    """
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
    """
    Retrieves a user from the database by verification token.

    Args:
        verification_token (str): The verification token to filter users by.

    Returns:
        A KofiUser object.

    Raises:
        HTTPException: 404 if the verification token is invalid.
    """
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
    """
    Updates the number of days to retain transaction data for the given user.

    Args:
        verification_token (str): The verification token for the user.
        days (int): The number of days to retain transaction data for.

    Returns:
        A KofiUser object with the updated user.

    Raises:
        HTTPException: 400 if the number of days is invalid.
        HTTPException: 404 if the verification token is invalid.
    """
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
    """
    Deletes a user from the database.

    Args:
        verification_token (str): The verification token for the user.
        inculde_transactions (bool, optional): Whether to include transactions in the deletion. Defaults to True.

    Returns:
        A JSON object with a single key "message" containing a string describing the result of the deletion.

    Raises:
        HTTPException: 404 if the verification token is invalid.
    """
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
    """
    Simple health check endpoint.

    Returns:
        A string "pong".
    """
    return "pong"


@app.get("/db/transactions", response_model=list[models.KofiTransactionSchema])
def read_transaction_db(ADMIN_SECRET_KEY, db: Session = Depends(database.get_db)):
    """
    Returns a list of all transactions in the database.

    Args:
        ADMIN_SECRET_KEY (str): The admin secret key.

    Returns:
        A list of KofiTransactionSchema objects.

    Raises:
        HTTPException: 401 if the admin secret key is invalid.
    """
    if ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")
    return db.query(models.KofiTransaction).all()


@app.get("/db/users", response_model=list[models.KofiUsreSchema])
def read_user_db(ADMIN_SECRET_KEY, db: Session = Depends(database.get_db)):
    """
    Returns a list of all users in the database.

    Args:
        ADMIN_SECRET_KEY (str): The admin secret key.

    Returns:
        A list of KofiUsreSchema objects.

    Raises:
        HTTPException: 401 if the admin secret key is invalid.
    """
    if ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")
    return db.query(models.KofiUser).all()

# ----- DB -----


@app.get("/db/export")
def export_db(ADMIN_SECRET_KEY, db: Session = Depends(database.get_db)):
    """
    Exports the entire database as a JSON file.

    Args:
        ADMIN_SECRET_KEY (str): The admin secret key.

    Returns:
        A JSON file containing all data in the database.

    Raises:
        HTTPException: 401 if the admin secret key is invalid.
        HTTPException: 500 if the export is not implemented.
    """
    if ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")

    return HTTPException(status_code=500, detail="Not implemented")


@app.get("/db/recover")
async def recover_db(ADMIN_SECRET_KEY, file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    if ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")

    return HTTPException(status_code=500, detail="Not implemented")


@app.get("/db/import")
def import_db(ADMIN_SECRET_KEY, db: Session = Depends(database.get_db)):
    if ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")

    return HTTPException(status_code=500, detail="Not implemented")


# ----- UTILITY -----

def currency_converter(amount: float, from_currency: str, to_currency: str) -> float:
    # API endpoint to get exchange rates
    """
    Converts an amount of money from one currency to another.

    Args:
        amount (float): The amount of money to be converted.
        from_currency (str): The currency to convert from.
        to_currency (str): The currency to convert to.

    Returns:
        float: The converted amount of money.

    Raises:
        HTTPException: 500 if the exchange rate could not be retrieved.
    """
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
