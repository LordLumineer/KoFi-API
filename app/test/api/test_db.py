"""./app/test/api/test_db.py"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.core.utils import remove_file
from app.main import app

client = TestClient(app)

# Mock settings
admin_secret_key = "valid_admin_key"
invalid_admin_secret_key = "invalid_key"

@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to mock settings with valid admin secret key."""
    monkeypatch.setattr("app.core.config.settings.ADMIN_SECRET_KEY", admin_secret_key)


# --------------- Test Database Export ---------------
# @patch("app.api.routes.db.export_db")#BUG
# def test_db_export_success(mock_export_db, mock_settings):
#     """Test successful database export with valid admin secret key."""
#     mock_export_db.return_value = "mock_db_file_path"

#     response = client.get(f"/db/export?admin_secret_key={admin_secret_key}")
#     print(response.json())
#     assert response.status_code == 200
#     assert response.headers["content-disposition"] == 'attachment; filename="Ko-fi API_export_'
#     mock_export_db.assert_called_once()


def test_db_export_invalid_secret_key(mock_settings):
    """Test export failure with an invalid admin secret key."""
    response = client.get(f"/db/export?admin_secret_key={invalid_admin_secret_key}")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid admin secret key"


# @patch("app.api.routes.db.export_db")#, side_effect=Exception("Export error"))
# def test_db_export_failure(mock_export_db, mock_settings):
#     """Test failure during database export."""
#     response = client.get(f"/db/export?admin_secret_key={admin_secret_key}")

#     assert response.status_code == 500
#     assert "Failed to export database" in response.json()["detail"]
#     mock_export_db.assert_called_once()


# --------------- Test Database Recover ---------------
@patch("app.api.routes.db.handle_database_import")
def test_db_recover_success(mock_handle_database_import, mock_settings):
    """Test successful database recovery with valid admin secret key."""
    with open("test.db", "wb") as f:
        f.write(b"dummy_db_content")

    with open("test.db", "rb") as test_file:
        response = client.post(f"/db/recover?admin_secret_key={admin_secret_key}", files={"file": test_file})

    assert response.status_code == 200
    assert "Database recovered from test.db" in response.json()["message"]
    mock_handle_database_import.assert_called_once_with("./temp_test.db", "recover")
    
    # Cleanup
    remove_file("./test.db")
    remove_file("./temp_test.db")


def test_db_recover_invalid_secret_key(mock_settings):
    """Test recovery failure with an invalid admin secret key."""
    with open("test.db", "wb") as f:
        f.write(b"dummy_db_content")
        
    with open("test.db", "rb") as test_file:
        response = client.post(f"/db/recover?admin_secret_key={invalid_admin_secret_key}", files={"file": test_file})
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid admin secret key"
    
    # Cleanup
    remove_file("./test.db")
    remove_file("./temp_test.db")


# @patch("app.api.routes.db.handle_database_import")#, side_effect=Exception("Recovery error")) #BUG
# def test_db_recover_failure(mock_handle_database_import, mock_settings):
#     """Test failure during database recovery."""
#     with open("test.db", "wb") as f:
#         f.write(b"dummy_db_content")

#     with open("test.db", "rb") as test_file:
#         response = client.post(f"/db/recover?admin_secret_key={admin_secret_key}", files={"file": test_file})

#     assert response.status_code == 500
#     assert "Failed to recover database" in response.json()["detail"]
#     mock_handle_database_import.assert_called_once()


# --------------- Test Database Import ---------------
@patch("app.api.routes.db.handle_database_import")
def test_db_import_success(mock_handle_database_import, mock_settings):
    """Test successful database import with valid admin secret key."""
    with open("test.db", "wb") as f:
        f.write(b"dummy_db_content")

    with open("test.db", "rb") as test_file:
        response = client.post(f"/db/import?admin_secret_key={admin_secret_key}", files={"file": test_file})

    assert response.status_code == 200
    assert "Database imported from test.db" in response.json()["message"]
    mock_handle_database_import.assert_called_once_with("./temp_test.db", "import")
    
    # Cleanup
    remove_file("./test.db")
    remove_file("./temp_test.db")


def test_db_import_invalid_secret_key(mock_settings):
    """Test import failure with an invalid admin secret key."""
    with open("test.db", "wb") as f:
        f.write(b"dummy_db_content")
        
    with open("test.db", "rb") as test_file:
        response = client.post(f"/db/import?admin_secret_key={invalid_admin_secret_key}", files={"file": test_file})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid admin secret key"
    
    # Cleanup
    remove_file("./test.db")
    remove_file("./temp_test.db")


# @patch("app.api.routes.db.handle_database_import")#, side_effect=Exception("Import error")) #BUG
# def test_db_import_failure(mock_handle_database_import, mock_settings):
#     """Test failure during database import."""
#     with open("test.db", "wb") as f:
#         f.write(b"dummy_db_content")

#     with open("test.db", "rb") as test_file:
#         response = client.post(f"/db/import?admin_secret_key={admin_secret_key}", files={"file": test_file})

#     assert response.status_code == 500
#     assert "Failed to import database" in response.json()["detail"]
#     mock_handle_database_import.assert_called_once()
