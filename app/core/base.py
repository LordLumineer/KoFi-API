"""
The base class for all SQLAlchemy models.

@file: ./app/core/base.py
@date: 2024-09-22
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    The base class for all SQLAlchemy models.
    """
