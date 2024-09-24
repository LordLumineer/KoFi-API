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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def remove_expired_transactions():
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

def run_migrations():
    alembic_cfg = Config("alembic.ini")
    logger.info("Running Alembic migrations...")
    command.upgrade(alembic_cfg, "head")
    logger.disabled = False
    logger.info("Alembic migrations completed.")


async def handle_database_import(uploaded_db_path: str, mode: str):
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

    return


async def export_db(db: Session):
    EXPORT_PATH = "./output.db"
    if "sqlite" in str(engine.url):
        # If it's SQLite, serve the actual database file
        ENGINE_DB_PATH = engine.url.database
        if os.path.exists(ENGINE_DB_PATH):
            shutil.copyfile(ENGINE_DB_PATH, EXPORT_PATH)
            # return FileResponse(EXPORT_DB, filename="my_database.db", media_type="application/octet-stream")
        else:
            raise HTTPException(
                status_code=404, detail="SQLite database file not found.")
    else:
        # For non-SQLite databases, dump the SQL statements
        metadata = MetaData()
        metadata.reflect(bind=engine)  # Reflect the database schema
        with open(EXPORT_PATH, "w", encoding="utf-8") as file:
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
                        insert_stmt = f"INSERT INTO {
                            table.name} ({columns}) VALUES ({values});\n"
                        file.write(insert_stmt)
    return EXPORT_PATH
