"""
The base class for all SQLAlchemy models.

@file: ./app/core/base.py
@date: 2024-09-22
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
from sqlalchemy.orm import DeclarativeBase

# pylint: disable=R0903


class Base(DeclarativeBase):
    """
    The base class for all SQLAlchemy models.
    """
