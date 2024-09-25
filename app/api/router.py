"""./app/api/router.py"""
from fastapi import APIRouter

from app.api.routes import admin, db, kofi, user


api_router = APIRouter()
api_router.include_router(kofi.router, prefix="/kofi", tags=["Ko-Fi"])
api_router.include_router(user.router, prefix="/user", tags=["User"])
api_router.include_router(db.router, prefix="/db", tags=["Database"])
api_router.include_router(admin.router, prefix="/admin", tags=["DEBUG"])
