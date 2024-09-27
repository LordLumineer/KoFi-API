"""
Models for Ko-fi transaction data and user data.

@file: ./app/core/models.py
@date: 2024-09-22
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from sqlalchemy import PickleType
from sqlalchemy.ext.mutable import MutableList, MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base
from app.core.config import settings

# pylint: disable=R0903


class KofiTransactionSchema(BaseModel):
    """
    Schemas for Ko-fi transaction data, based on the format described at:
    https://ko-fi.com/manage/webhooks (as of 2024-21-09).
    """
    verification_token: str
    message_id: str
    timestamp: str
    type: str
    is_public: bool
    from_name: str
    message: None | str = Field(default=None, nullable=True)
    amount: str
    url: str
    email: str
    currency: str
    is_subscription_payment: bool
    is_first_subscription_payment: bool
    kofi_transaction_id: str
    shop_items: None | list = Field(default=None, nullable=True)
    tier_name: None | str = Field(default=None, nullable=True)
    shipping: None | dict = Field(default=None, nullable=True)

    class Config:
        """ORM model configuration"""
        from_attributes = True


class KofiTransaction(Base):
    """Ko-fi transaction model."""
    __tablename__ = "kofi_transactions"

    verification_token: Mapped[str] = mapped_column(index=True)
    message_id: Mapped[str] = mapped_column(primary_key=True, index=True)
    timestamp: Mapped[str]
    type: Mapped[str]
    is_public: Mapped[bool]
    from_name: Mapped[str]
    message: Mapped[str | None]
    amount: Mapped[str]
    url: Mapped[str]
    email: Mapped[str]
    currency: Mapped[str]
    is_subscription_payment: Mapped[bool]
    is_first_subscription_payment: Mapped[bool]
    kofi_transaction_id: Mapped[str]
    shop_items: Mapped[PickleType | None] = mapped_column(
        MutableList.as_mutable(PickleType))
    tier_name: Mapped[str | None]
    shipping: Mapped[PickleType | None] = mapped_column(
        MutableDict.as_mutable(PickleType))


class KofiUserSchema(BaseModel):
    """
    Schemas for User data.
    """
    verification_token: str
    data_retention_days: int = Field(default=settings.DATA_RETENTION_DAYS)
    latest_request_at: str = Field(default=datetime.now(
        timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    prefered_currency: str = Field(default="USD")

    class Config:
        """ORM model configuration"""
        from_attributes = True


class KofiUser(Base):
    """Ko-fi users model."""
    __tablename__ = "kofi_users"

    verification_token: Mapped[str] = mapped_column(
        primary_key=True, index=True)
    data_retention_days: Mapped[int] = mapped_column(
        default=settings.DATA_RETENTION_DAYS)
    latest_request_at: Mapped[str]
    prefered_currency: Mapped[str] = mapped_column(default="USD")
