"""
Test cases for the base class for all SQLAlchemy models.

@file: ./app/test/core/test_base.py
@date: 2024-09-27
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
from sqlalchemy import Column, Integer, String, create_engine, inspect
from sqlalchemy.orm import Session
from app.core.base import Base

# Define a mock model that inherits from Base


class MockModel(Base): # pylint: disable=R0903
    """Define a mock model that inherits from Base."""
    __tablename__ = "mock_model"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

# --------------- Test that the Base class works as expected ---------------


def test_base_class():
    """Test that the Base class can be inherited and works with SQLAlchemy."""

    # Create an in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")

    # Create the table associated with MockModel
    Base.metadata.create_all(bind=engine)

    # Verify that the table is created
    inspector = inspect(engine)
    assert "mock_model" in inspector.get_table_names()

    # Create a session to interact with the database
    session = Session(bind=engine)

    # Create and insert a new MockModel instance
    new_entry = MockModel(name="Test Entry")
    session.add(new_entry)
    session.commit()

    # Verify that the entry was added to the database
    result = session.query(MockModel).filter_by(name="Test Entry").first()
    assert result is not None
    assert result.name == "Test Entry"

    # Update the entry
    result.name = "Updated Entry"
    session.commit()

    # Verify the update
    updated_result = session.query(MockModel).filter_by(name="Updated Entry").first()
    assert updated_result is not None
    assert updated_result.name == "Updated Entry"

    # Delete the entry
    session.delete(updated_result)
    session.commit()

    # Verify the deletion
    deleted_result = session.query(MockModel).filter_by(name="Updated Entry").first()
    assert deleted_result is None

    session.close()
