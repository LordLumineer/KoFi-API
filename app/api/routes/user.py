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
    user = KofiUser(
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


@router.get("/{verification_token}")
def get_user(verification_token: str, db: Session = Depends(get_db)):
    user = db.query(KofiUser).filter(
        KofiUser.verification_token == verification_token
    ).first()
    if not user:
        raise HTTPException(
            status_code=404, detail="Invalid verification token")
    return user


@router.patch("/{verification_token}")
def update_expiration(
    verification_token: str,
    days: int,
    db: Session = Depends(get_db),
):
    user = db.query(KofiUser).filter(
        KofiUser.verification_token == verification_token
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


@router.delete("/{verification_token}")
def delete_user(
    verification_token: str,
    inculde_transactions: bool = True,
    db: Session = Depends(get_db)
):
    user = db.query(KofiUser).filter(
        KofiUser.verification_token == verification_token
    ).first()
    if not user:
        raise HTTPException(
            status_code=404, detail="Invalid verification token")
    user.delete()
    db.commit()
    if inculde_transactions:
        transactions = db.query(KofiTransaction).filter(
            KofiTransaction.verification_token == verification_token
        )
        transactions.delete()
        db.commit()
    return {"message": "User deleted successfully"}
