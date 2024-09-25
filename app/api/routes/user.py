"""
API endpoints for Ko-fi users.

@file: ./app/api/routes/user.py
@date: 2024-09-22
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.db import get_db
from app.core.models import KofiTransaction, KofiUser
from app.core.config import settings


router = APIRouter()


@router.post("/{verification_token}")
def create_user(
    verification_token: str,
    data_retention_days: int | None = None,
    db: Session = Depends(get_db)

):
    """
    Create a new Ko-fi user in the database.

    Args:
        verification_token: The user's verification token.
        data_retention_days: The number of days to retain the user's donation data.
            Defaults to the value of `DATA_RETENTION_DAYS` in the configuration.
        db: The database session, provided by the dependency injection system.

    Returns:
        The new user object, represented as a KofiUser instance.

    Raises:
        HTTPException: If the provided verification token is invalid, or if the user
            already exists in the database.
    """
    user = KofiUser(
        verification_token=verification_token,
        data_retention_days=data_retention_days if data_retention_days else settings.DATA_RETENTION_DAYS,
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


@router.get("/{verification_token}")
def get_user(verification_token: str, db: Session = Depends(get_db)):
    """
    Get a Ko-fi user by their verification token.

    Args:
        verification_token: The verification token of the user to retrieve.
        db: The database session, provided by the dependency injection system.

    Returns:
        The user object, represented as a KofiUser instance, or 404 if not found.
    """
    user = db.query(KofiUser).filter(
        KofiUser.verification_token == verification_token
    ).first()
    if not user:
        raise HTTPException(
            status_code=404, detail="Invalid verification token")
    return user


@router.patch("/{verification_token}")
def update_user(
    verification_token: str,
    days: int | None = None,
    latest_request_at = None,
    db: Session = Depends(get_db),
):
    user = db.query(KofiUser).filter(
        KofiUser.verification_token == verification_token
    ).first()
    if not user:
        raise HTTPException(
            status_code=404, detail="Invalid verification token")
    try:
        if days:
            user.data_retention_days = days
        if latest_request_at:
            user.latest_request_at = latest_request_at
        if days or latest_request_at:
            db.commit()
            db.refresh(user)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig)) from e
    return user


@router.delete("/{verification_token}")
def delete_user(
    verification_token: str,
    inculde_transactions: bool = True,
    db: Session = Depends(get_db)
):
    """
    Delete a Ko-fi user by their verification token.

    Args:
        verification_token: The verification token of the user to delete.
        inculde_transactions: If True, delete all transactions associated with the user.
            Defaults to True.
        db: The database session, provided by the dependency injection system.

    Returns:
        A dictionary with a message indicating that the user was deleted successfully.

    Raises:
        HTTPException: If the provided verification token is invalid.
    """
    user = db.query(KofiUser).filter(
        KofiUser.verification_token == verification_token
    ).first()
    if not user:
        raise HTTPException(
            status_code=404, detail="Invalid verification token")
    db.delete(user)
    db.commit()
    if inculde_transactions:
        transactions = db.query(KofiTransaction).filter(
            KofiTransaction.verification_token == verification_token
        ).all()
        for transaction in transactions:
            db.delete(transaction)
        db.commit()
    return {"message": "User deleted successfully"}
