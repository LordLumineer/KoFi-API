"""
Database module for Ko-fi donation API.

@file: ./app/core/db.py
@date: 2024-09-22
@author: Lord Lumineer (lordlumineer@gmail.com)
"""
import logging
import os
from datetime import datetime, timedelta
import shutil
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.models import KofiTransaction, KofiUser
from app.core.config import settings, logger


engine = create_engine(url=settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency to get a new database session.

    This function is a FastAPI dependency that returns a new database session
    each time it is called. The session is properly closed after the generator
    is exhausted.

    Yields:
        Session: A new database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def remove_expired_transactions() -> None:
    """
    Remove expired transactions from the database.

    This function removes all transactions that are older than the number of days
    specified in the user's data_retention_days field. The function is meant to be
    called as a background task to periodically clean up the database.

    The function first retrieves all users from the database, and then iterates
    over each user, deleting all transactions that are older than the specified
    number of days.

    Finally, the database session is properly closed.
    """
    db_generator = get_db()
    db = next(db_generator)
    try:
        users = db.query(KofiUser).all()
        for user in users:
            latest_day = datetime.now() - timedelta(days=user.data_retention_days)
            db.get(KofiTransaction).filter(
                KofiTransaction.timestamp < latest_day,
            ).delete()
    finally:
        db.close()


def run_migrations() -> None:
    """
    Run Alembic migrations to the latest version.

    This function is meant to be called at application startup. It configures
    Alembic with the `alembic.ini` file and upgrades the database to the latest
    version. The logger is temporarily disabled to prevent logging while the
    migrations are being run.

    The function blocks until the migrations are complete.
    """
    alembic_cfg = Config("alembic.ini")
    logger.info("Running Alembic migrations...")
    command.upgrade(alembic_cfg, "head")
    logger.disabled = False
    logging.getLogger("uvicorn.access").disabled = False
    logger.info("Alembic migrations completed.")


async def handle_database_import(uploaded_db_path: str, mode: str) -> bool:
    """
    Handles importing a database from an uploaded SQLite file.

    The function takes an uploaded SQLite database file path and a mode string as arguments.
    The mode string can be either "recover" or "import".

    In "recover" mode, the function will replace all existing data in the current database
    with the data from the uploaded database. If a row does not exist in the current database,
    it will be added. If a row exists, its data will be replaced with the data from the
    uploaded database if the data is different.

    In "import" mode, the function will not replace existing data in the current database.
    If a row does not exist in the current database, it will be added. If a row exists, its
    data will not be replaced with the data from the uploaded database.

    The function returns a boolean indicating whether the import was successful.

    After the import is complete, the uploaded database file is removed.
    """
    # Connect to the uploaded SQLite database
    upload_engine = create_engine(f"sqlite:///{uploaded_db_path}")
    upload_conn = upload_engine.connect()

    # Get the metadata and inspector of the running and uploaded databases
    meta = MetaData()
    meta.reflect(bind=engine)

    upload_meta = MetaData()
    upload_meta.reflect(bind=upload_engine)

    inspector = inspect(engine)  # Inspect the running DB
    upload_inspector = inspect(upload_engine)  # Inspect the uploaded DB

    with Session(engine) as (session, upload_conn):
        for table_name in inspector.get_table_names():
            if table_name not in upload_inspector.get_table_names():
                # Skip tables not present in the uploaded database
                continue

            # Compare columns in both databases
            columns_existing = [col['name']
                                for col in inspector.get_columns(table_name)]
            # columns_uploaded = [col['name']
            #                     for col in upload_inspector.get_columns(table_name)]

            # Create a SQLAlchemy Table object for both DBs
            table_existing = Table(table_name, meta, autoload_with=engine)
            table_uploaded = Table(
                table_name, upload_meta, autoload_with=upload_engine)

            # Compare rows based on primary keys
            primary_keys = [
                key.name for key in inspector.get_primary_keys(table_name)]
            stmt_existing = select(table_existing)
            stmt_uploaded = select(table_uploaded)

            rows_existing = {tuple([row[key] for key in primary_keys]):
                             row for row in session.execute(stmt_existing).mappings()}
            rows_uploaded = {tuple([row[key] for key in primary_keys]):
                             row for row in upload_conn.execute(stmt_uploaded).mappings()}

            # Add or update rows based on mode
            for pk, row_uploaded in rows_uploaded.items():
                if pk not in rows_existing:
                    # Row does not exist in the existing DB, add it
                    new_row = {
                        key: row_uploaded[key] for key in columns_existing if key in row_uploaded}
                    session.execute(table_existing.insert().values(new_row))
                else:
                    # Row exists, check data differences
                    row_existing = rows_existing[pk]
                    for col in columns_existing:
                        if col in row_uploaded and col in row_existing:
                            if mode == "recover":
                                # In 'recover', replace data if different
                                if row_uploaded[col] is not None and row_uploaded[col] != row_existing[col]:
                                    session.execute(table_existing.update().where(
                                        table_existing.c[primary_keys[0]
                                                         ] == pk[0]
                                    ).values({col: row_uploaded[col]}))
                            elif mode == "import":
                                # In 'import', do not replace existing data
                                if row_existing[col] is None and row_uploaded[col] is not None:
                                    session.execute(table_existing.update().where(
                                        table_existing.c[primary_keys[0]
                                                         ] == pk[0]
                                    ).values({col: row_uploaded[col]}))

        # Commit changes
        session.commit()

    # Clean up the uploaded database file
    upload_conn.close()
    os.remove(uploaded_db_path)

    return True


async def export_db(db: Session) -> str:
    """
    Export the current database to a file.

    Args:
        db (Session): The database session.

    Returns:
        str: The path to the exported database file.

    Raises:
        HTTPException: If the database file is not found.
    """
    export_path = "./output.db"
    if "sqlite" in str(engine.url):
        # If it's SQLite, serve the actual database file
        ENGINE_DB_PATH = engine.url.database
        if os.path.exists(ENGINE_DB_PATH):
            shutil.copyfile(ENGINE_DB_PATH, export_path)
        else:
            raise HTTPException(
                status_code=404, detail="SQLite database file not found.")
    else:
        # For non-SQLite databases, dump the SQL statements
        metadata = MetaData()
        metadata.reflect(bind=engine)  # Reflect the database schema
        with open(export_path, "w", encoding="utf-8") as file:
            # Write schema first
            for table in reversed(metadata.sorted_tables):
                file.write(str(table))
                file.write("\n\n")

            # Write data
            for table in metadata.sorted_tables:
                result = db.execute(text(f"SELECT * FROM {table.name}"))
                rows = result.fetchall()
                if rows:
                    columns = ", ".join([col for col in result.keys()])
                    for row in rows:
                        values = ", ".join([f"'{str(val)}'" for val in row])
                        insert_stmt = f"INSERT INTO {table.name} ({columns}) VALUES ({values});\n"
                        file.write(insert_stmt)
    return export_path