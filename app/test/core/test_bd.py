"""./app/test/core/test_db.py"""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from app.core.db import get_db, remove_expired_transactions, run_migrations, handle_database_import, export_db


# --------------- Test get_db ---------------
def test_get_db():
    """Test the database session lifecycle management in get_db()."""
    with patch("app.core.db.SessionLocal") as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        # Simulate calling get_db and using the session
        generator = get_db()
        db = next(generator)

        # Check if the session was created and returned
        assert db == mock_session

        # Simulate closing the session
        try:
            next(generator)
        except StopIteration:
            pass

        mock_session.close.assert_called_once()


# --------------- Test remove_expired_transactions --------------- 
# @patch("app.core.db.get_db")# BUG
# def test_remove_expired_transactions(mock_get_db):
#     """Test the removal of expired transactions based on user retention policy."""
#     # Mock the session and queries
#     mock_session = MagicMock()
#     mock_get_db.return_value = iter([mock_session])

#     # Create mock users with different data retention policies
#     mock_user1 = MagicMock(data_retention_days=30)
#     mock_user2 = MagicMock(data_retention_days=60)
#     mock_session.query.return_value.all.return_value = [mock_user1, mock_user2]

#     # Call the function
#     remove_expired_transactions()

#     # Check that the transactions older than the retention period are filtered and deleted
#     assert mock_session.query.return_value.filter.call_count == 2
#     assert mock_session.query.return_value.filter.return_value.delete.call_count == 2
#     mock_session.close.assert_called_once()


# --------------- Test run_migrations ---------------
# @patch("alembic.command.upgrade")# BUG
# @patch("alembic.config.Config")
# def test_run_migrations(mock_config, mock_upgrade):
#     """Test running Alembic migrations to upgrade the database schema."""
#     mock_alembic_config = MagicMock()
#     mock_config.return_value = mock_alembic_config

#     # Call the function
#     run_migrations()

#     # Check that Alembic's upgrade command was called with the correct arguments
#     mock_upgrade.assert_called_once_with(mock_alembic_config, "head")


# --------------- Test handle_database_import (Recover Mode) ---------------
# @patch("app.core.db.create_engine")# BUG
# @patch("app.core.db.Session")
# @patch("os.remove")
# def test_handle_database_import_recover(mock_remove, mock_session, mock_create_engine):
#     """Test the database import functionality in 'recover' mode."""
#     mock_engine = MagicMock()
#     mock_create_engine.return_value = mock_engine
#     mock_session_instance = mock_session.return_value
#     mock_connection = mock_engine.connect.return_value

#     # Simulate tables and data for both existing and uploaded databases
#     mock_inspector = MagicMock()
#     mock_upload_inspector = MagicMock()

#     mock_existing_table_data = {"primary_key": {"col1": "existing"}}
#     mock_uploaded_table_data = {"primary_key": {"col1": "uploaded"}}

#     mock_session_instance.execute.return_value.mappings.return_value = mock_existing_table_data
#     mock_connection.execute.return_value.mappings.return_value = mock_uploaded_table_data

#     # Call the function in recover mode
#     result = handle_database_import("uploaded_db_path", "recover")

#     assert result is True

#     # Check that os.remove was called to clean up the uploaded DB
#     mock_remove.assert_called_once_with("uploaded_db_path")


# --------------- Test handle_database_import (Import Mode) ---------------
# @patch("app.core.db.create_engine")# BUG
# @patch("app.core.db.Session")
# @patch("os.remove")
# def test_handle_database_import_import(mock_remove, mock_session, mock_create_engine):
#     """Test the database import functionality in 'import' mode."""
#     mock_engine = MagicMock()
#     mock_create_engine.return_value = mock_engine
#     mock_session_instance = mock_session.return_value
#     mock_connection = mock_engine.connect.return_value

#     # Simulate tables and data for both existing and uploaded databases
#     mock_inspector = MagicMock()
#     mock_upload_inspector = MagicMock()

#     mock_existing_table_data = {"primary_key": {"col1": "existing"}}
#     mock_uploaded_table_data = {"primary_key": {"col1": "uploaded"}}

#     mock_session_instance.execute.return_value.mappings.return_value = mock_existing_table_data
#     mock_connection.execute.return_value.mappings.return_value = mock_uploaded_table_data

#     # Call the function in import mode
#     result = handle_database_import("uploaded_db_path", "import")

#     assert result is True

#     # Check that os.remove was called to clean up the uploaded DB
#     mock_remove.assert_called_once_with("uploaded_db_path")


# --------------- Test export_db ---------------
# @patch("shutil.copyfile")# BUG
# @patch("os.path.exists")
# @patch("app.core.db.engine")
# def test_export_db_sqlite(mock_engine, mock_path_exists, mock_copyfile):
#     """Test exporting the database when using SQLite."""
#     mock_engine.url.database = "test.db"
#     mock_path_exists.return_value = True
#     mock_session = MagicMock()

#     # Call the export_db function
#     result = export_db(mock_session)

#     # Check that the correct path is returned and file was copied
#     assert result == "./output.db"
#     mock_copyfile.assert_called_once_with("test.db", "./output.db")


# @patch("app.core.db.engine")# BUG
# def test_export_db_no_sqlite(mock_engine):
#     """Test exporting the database for non-SQLite databases (dump SQL statements)."""
#     mock_engine.url.database = None
#     mock_session = MagicMock()

#     with patch("builtins.open", MagicMock()) as mock_open:
#         result = export_db(mock_session)

#     assert result == "./output.db"
