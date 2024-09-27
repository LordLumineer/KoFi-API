"""
API endpoints for Ko-fi database management.

@file: ./app/api/routes/db.py
@date: 2024-09-22
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, UploadFile, Depends, File
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db, handle_database_import, export_db
from app.core.utils import remove_file


router = APIRouter()


@router.get("/export")
async def db_export(
    admin_secret_key: str,
    background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Export the current database to a file.

    Args:
        admin_secret_key (str): The secret key to authorize the export.
        background_tasks (BackgroundTasks): FastAPI's BackgroundTasks object.
        db (Session): The database session.

    Returns:
        FileResponse: The exported database file.

    Raises:
        HTTPException: If the secret key is invalid or there is an error exporting the database.
    """
    if admin_secret_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")
    file_path = await export_db(db)
    background_tasks.add_task(remove_file, file_path)
    return FileResponse(
        path=file_path,
        filename=f'{settings.PROJECT_NAME}_export_{
            int(datetime.now(timezone.utc).timestamp())}.db',
        media_type="application/octet-stream"
    )


@router.post("/recover")
async def db_recover(
    admin_secret_key: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Recover a database from an uploaded file. This will overwrite the existing
    database.

    Args:
        admin_secret_key (str): The secret key to authorize the import.
        file (UploadFile): The uploaded file containing the database to import.

    Returns:
        dict: A JSON response with a success message.
    """
    if admin_secret_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")
    # Save the uploaded file temporarily
    uploaded_db_path = f"./temp_{file.filename}"
    with open(uploaded_db_path, "wb") as buffer:
        buffer.write(await file.read())

    # Call function to handle database import logic
    success = await handle_database_import(uploaded_db_path, "recover")
    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to recover database")
    background_tasks.add_task(remove_file, uploaded_db_path)

    return {"message": f"Database recovered from {file.filename}"}


@router.post("/import")
async def db_import(
    admin_secret_key: str,
    file: UploadFile = File(...),
):
    """
    Import a database from an uploaded file. This will overwrite the existing
    database.

    Args:
        admin_secret_key (str): The secret key to authorize the import.
        file (UploadFile): The uploaded file containing the database to import.

    Returns:
        dict: A JSON response with a success message.
    """
    if admin_secret_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")

    # Save the uploaded file temporarily
    uploaded_db_path = f"./temp_{file.filename}"
    with open(uploaded_db_path, "wb") as buffer:
        buffer.write(await file.read())

    # Call function to handle database import logic
    await handle_database_import(uploaded_db_path, "import")

    return {"message": f"Database imported from {file.filename}"}
