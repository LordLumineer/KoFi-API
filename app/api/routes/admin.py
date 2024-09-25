"""
API endpoints for Ko-fi donation API admin operations.

@file: ./app/api/routes/admin.py
@date: 2024-09-22
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.models import KofiTransaction, KofiTransactionSchema, KofiUser, KofiUserSchema
from app.core.config import settings


router = APIRouter()


@router.get("/db/transactions", response_model=list[KofiTransactionSchema])
def read_transaction_db(admin_secret_key, db: Session = Depends(get_db)):
    """
    Get all Ko-fi transactions in the database.

    Args:
        admin_secret_key: The admin secret key set in the environment variable `admin_secret_key`.
        db: The database session, provided by the dependency injection system.

    Returns:
        A list of all Ko-fi transactions in the database, represented as KofiTransactionSchema.

    Raises:
        HTTPException: If the provided admin secret key is invalid.
    """
    if admin_secret_key != settings.admin_secret_key:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")
    return db.query(KofiTransaction).all()


@router.get("/db/users", response_model=list[KofiUserSchema])
def read_user_db(admin_secret_key, db: Session = Depends(get_db)):
    """
    Get all Ko-fi users in the database.

    Args:
        admin_secret_key: The admin secret key set in the environment variable `admin_secret_key`.
        db: The database session, provided by the dependency injection system.

    Returns:
        A list of all Ko-fi users in the database, represented as KofiUserSchema.

    Raises:
        HTTPException: If the provided admin secret key is invalid.
    """
    if admin_secret_key != settings.admin_secret_key:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")
    return db.query(KofiUser).all()
