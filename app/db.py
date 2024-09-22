from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import MetaData, create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.orm import Session

from app import models
from app.config import settings

DATABASE_URL = "sqlite:///./KoFi.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """
    The base class for all SQLAlchemy models.
    """


def get_db():
    """
    Returns a context manager that provides a database session.

    This function creates a new database session using the `SessionLocal` object, 
    which is a session factory created by the `sessionmaker` function. 
    The session is yielded in the context manager, allowing the caller to use it to interact with the database.

    The session is automatically closed in the `finally` block of the context manager, 
    ensuring that it is always properly closed, even if an exception occurs.

    Returns:
        A context manager that provides a database session.

    Example:
        with get_db() as db:
            # Use the db session to interact with the database
            # ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def remove_expired_transactions():
    """
    Removes expired transactions from the database.

    Args:
        db (Session): The database session.
        retention_months (int): The number of months to retain transactions for.

    Returns:
        None
    """
    db_generator = get_db()
    db = next(db_generator)
    try:
        users = db.query(models.KofiUser).all()
        for user in users:
            latest_day = datetime.now() - timedelta(days=user.data_retention_days)
            db.get(models.KofiTransaction).filter(
                models.KofiTransaction.timestamp < latest_day,
            ).delete()
    finally:
        db.close()
