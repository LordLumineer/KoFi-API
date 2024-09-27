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
from typing import Generator
from fastapi import HTTPException
from sqlalchemy import Connection, Inspector, MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker
from alembic import command
from alembic.config import Config

from app.core.models import KofiTransaction, KofiUser
from app.core.config import settings, logger


engine = create_engine(url=settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
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
    upload_conn, upload_engine = await connect_to_uploaded_db(uploaded_db_path)
    inspector, upload_inspector = await get_inspectors(upload_conn)

    with Session(engine) as session:
        for table_name in inspector.get_table_names():
            if table_name not in upload_inspector.get_table_names():
                # Skip tables not present in the uploaded database
                continue

            await process_table(session, table_name, upload_conn, inspector, mode)

    await upload_conn.close()
    await upload_engine.dispose()
    return True


async def connect_to_uploaded_db(uploaded_db_path: str) -> Connection:
    """
    Connect to the uploaded SQLite database.
    """
    new_engine = create_engine(f"sqlite:///{uploaded_db_path}")
    new_conn = new_engine.connect()
    return new_conn, new_engine


async def get_inspectors(upload_conn: Connection) -> tuple[Inspector, Inspector]:
    """
    Get the metadata and inspector of the running and uploaded databases.
    """
    meta = MetaData()
    meta.reflect(bind=engine)

    upload_meta = MetaData()
    upload_meta.reflect(bind=upload_conn)

    inspector = inspect(engine)
    upload_inspector = inspect(upload_conn)

    return inspector, upload_inspector


async def process_table(
    session: Session,
    table_name: str,
    upload_conn: Connection,
    inspector: Inspector,
    # upload_inspector: Inspector,
    mode: str
) -> None:
    """
    Process a table by comparing rows based on primary keys.

    The function takes a session, table name, inspectors of the running and uploaded
    databases, and a mode string as arguments.

    If a row does not exist in the current database, it will be added. If a row exists, its
    data will be replaced with the data from the uploaded database if the data is different.
    """
    primary_keys = inspector.get_pk_constraint(table_name).get('constrained_columns')

    stmt_existing = select(Table(table_name, MetaData(), autoload_with=engine))
    stmt_uploaded = select(Table(table_name, MetaData(), autoload_with=upload_conn))

    rows_existing = {tuple(row[key] for key in primary_keys):
                     row for row in session.execute(stmt_existing).mappings()}

    rows_uploaded = {tuple(row[key] for key in primary_keys):
                     row for row in upload_conn.execute(stmt_uploaded).mappings()}

    for pk, row_uploaded in rows_uploaded.items():
        if pk not in rows_existing:
            # Row does not exist in the existing DB, add it
            new_row = {
                key: row_uploaded[key] for key in inspector.get_columns(table_name)}
            session.execute(
                Table(table_name, MetaData(), autoload_with=engine).insert().values(new_row))
        else:
            # Row exists, check data differences
            row_existing = rows_existing[pk]
            for col in inspector.get_columns(table_name):
                if col in row_uploaded and col in row_existing:
                    if mode == "recover" and (
                        row_uploaded[col] is not None and row_uploaded[col] != row_existing[col]
                    ):
                        # In 'recover', replace data if different
                        session.execute(
                            Table(table_name, MetaData(), autoload_with=engine).update().where(
                                Table(table_name, MetaData(), autoload_with=engine).c[primary_keys[0]]
                                == pk[0]
                            ).values({col: row_uploaded[col]}))
                    elif mode == "import" and (
                        row_existing[col] is None and row_uploaded[col] is not None
                    ):
                        # In 'import', do not replace existing data
                        session.execute(
                            Table(table_name, MetaData(), autoload_with=engine).update().where(
                                Table(table_name, MetaData(), autoload_with=engine).c[primary_keys[0]]
                                == pk[0]
                            ).values({col: row_uploaded[col]}))

                    # if mode == "recover":
                    #     # In 'recover', replace data if different
                    #     if row_uploaded[col] is not None and row_uploaded[col] != row_existing[col]:
                    #         session.execute(
                    #             Table(table_name, MetaData(), autoload_with=engine).update().where(
                    #                 Table(table_name, MetaData(), autoload_with=engine).c[primary_keys[0]]
                    #                 == pk[0]
                    #             ).values({col: row_uploaded[col]}))
                    # elif mode == "import":
                    #     # In 'import', do not replace existing data
                    #     if row_existing[col] is None and row_uploaded[col] is not None:
                    #         session.execute(
                    #             Table(table_name, MetaData(), autoload_with=engine).update().where(
                    #                 Table(table_name, MetaData(), autoload_with=engine).c[primary_keys[0]]
                    #                 == pk[0]
                    #             ).values({col: row_uploaded[col]}))

    # Commit changes
    session.commit()


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
        engine_db_path = engine.url.database
        if os.path.exists(engine_db_path):
            shutil.copyfile(engine_db_path, export_path)
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
                    columns = ", ".join(list(result.keys()))
                    for row in rows:
                        values = ", ".join([f"'{str(val)}'" for val in row])
                        insert_stmt = f"INSERT INTO {table.name} ({columns}) VALUES ({values});\n"
                        file.write(insert_stmt)
    return export_path
