from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.models import KofiTransaction, KofiTransactionSchema, KofiUser, KofiUserSchema
from app.core.config import settings


router = APIRouter()


@router.get("/db/transactions", response_model=list[KofiTransactionSchema])
def read_transaction_db(ADMIN_SECRET_KEY, db: Session = Depends(get_db)):
    if ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")
    return db.query(KofiTransaction).all()


@router.get("/db/users", response_model=list[KofiUserSchema])
def read_user_db(ADMIN_SECRET_KEY, db: Session = Depends(get_db)):
    if ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")
    return db.query(KofiUser).all()
