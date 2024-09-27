"""
Test cases for the main FastAPI application.

@file: ./app/test/test_main.py
@date: 2024-09-27
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
from unittest.mock import patch, MagicMock
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import pytest

from app.main import app, custom_generate_unique_id

# Initialize the FastAPI TestClient
client = TestClient(app)


# Test the /ping endpoint


def test_ping():
    """Test the /ping healthcheck endpoint."""
    response = client.get("/ping")
    assert response.status_code == 200
    # Since FastAPI automatically returns a JSON response
    assert response.text == '"pong"'


# Test the custom_generate_unique_id function
def test_custom_generate_unique_id():
    """Test the custom route unique ID generator."""
    # Mock a route with a tag and name
    mock_route = MagicMock(spec=APIRoute)
    mock_route.tags = ["TEST"]
    mock_route.name = "test-route"

    # Call the function and verify the unique ID
    unique_id = custom_generate_unique_id(mock_route)
    assert unique_id == "TEST-test-route"


@pytest.mark.asyncio(loop_scope="session")
@patch("app.main.run_migrations")
@patch("app.main.remove_expired_transactions")
async def test_lifespan(mock_remove_expired_transactions, mock_run_migrations):  # pylint: disable=W0613, W0621
    """Test the lifespan function to ensure startup and shutdown behavior."""
    # Mock scheduler behavior
    with patch("app.main.BackgroundScheduler.start") as mock_scheduler_start, \
            patch("app.main.BackgroundScheduler.shutdown") as mock_scheduler_shutdown:

        # Simulate the FastAPI lifespan context
        async with app.router.lifespan_context(app):
            # Check if run_migrations was called on startup
            mock_run_migrations.assert_called_once()
            # Ensure the scheduler started
            mock_scheduler_start.assert_called_once()

        # After exiting the context, check if the scheduler was shut down
        mock_scheduler_shutdown.assert_called_once()


# Run the tests using pytest
