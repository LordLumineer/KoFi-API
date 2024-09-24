import os

from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, UploadFile, Depends, File
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db, handle_database_import, export_db


router = APIRouter()


@router.get("/export")
async def db_export(ADMIN_SECRET_KEY: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")
    try:
        def remove_file(file_path: str):
            """Background task to delete the file after sending it."""
            if os.path.exists(file_path):
                os.remove(file_path)
        file_path = await export_db(db)
        background_tasks.add_task(remove_file, file_path)
        return FileResponse(file_path, filename=f'{settings.PROJECT_NAME}_export_{int(datetime.now(timezone.utc).timestamp())}.db', media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to export database: {str(e)}") from e


@router.post("/recover")
async def db_recover(
    ADMIN_SECRET_KEY: str,
    file: UploadFile = File(...),
):
    if ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")

    # Save the uploaded file temporarily
    uploaded_db_path = f"./temp_{file.filename}"
    with open(uploaded_db_path, "wb") as buffer:
        buffer.write(await file.read())

    # Call function to handle database import logic
    await handle_database_import(uploaded_db_path, "recover")

    return {"message": f"Database recovered from {file.filename}"}


@router.post("/import")
async def db_import(
    ADMIN_SECRET_KEY: str,
    file: UploadFile = File(...),
):
    if ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=401, detail="Invalid admin secret key")

    # Save the uploaded file temporarily
    uploaded_db_path = f"./temp_{file.filename}"
    with open(uploaded_db_path, "wb") as buffer:
        buffer.write(await file.read())

    # Call function to handle database import logic
    await handle_database_import(uploaded_db_path, "import")

    return {"message": f"Database imported from {file.filename}"}
