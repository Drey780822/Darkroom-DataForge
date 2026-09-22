import logging
import sqlite3
from sqlalchemy import create_engine, text, event, Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

logger = logging.getLogger("dataforge.database")

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign keys and check constraints on all SQLite connections."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

def get_engine():
    db_url = settings.DATABASE_URL
    # If using sqlite, add check_same_thread=False
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False}
        )
    try:
        connect_args = {}
        if "postgresql" in db_url:
            connect_args["connect_timeout"] = 2
        engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
        # Test connection
        with engine.connect() as conn:
            pass
        return engine
    except Exception as e:
        logger.warning(
            f"Failed to connect to primary database ({db_url}): {e}. "
            f"Falling back to SQLite at {settings.SQLITE_FALLBACK_URL}."
        )
        return create_engine(
            settings.SQLITE_FALLBACK_URL,
            connect_args={"check_same_thread": False}
        )

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _sync_sqlite_columns(conn):
    """Ensure newly added columns exist in existing SQLite tables without breaking data."""
    try:
        # Check extraction_jobs columns
        res = conn.execute(text("PRAGMA table_info(extraction_jobs)")).fetchall()
        existing_cols = {row[1] for row in res}
        
        job_cols_to_add = [
            ("extraction_mode", "VARCHAR(50) DEFAULT 'high_accuracy'"),
            ("primary_model", "VARCHAR(100)"),
            ("secondary_model", "VARCHAR(100)"),
            ("provider", "VARCHAR(50)"),
            ("prompt_version", "VARCHAR(50)"),
            ("tokens_used", "INTEGER DEFAULT 0"),
            ("estimated_cost", "FLOAT DEFAULT 0.0"),
            ("step_status", "VARCHAR(50) DEFAULT 'pending'"),
            ("conflicts", "TEXT DEFAULT '[]'"),
        ]
        for col_name, col_def in job_cols_to_add:
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE extraction_jobs ADD COLUMN {col_name} {col_def}"))

        # Check datasets columns
        res = conn.execute(text("PRAGMA table_info(datasets)")).fetchall()
        ds_cols = {row[1] for row in res}
        ds_cols_to_add = [
            ("is_verified", "BOOLEAN DEFAULT 0"),
            ("verified_by", "VARCHAR(100)"),
            ("verified_at", "TIMESTAMP"),
            ("verification_notes", "TEXT"),
            ("data_dictionary", "TEXT DEFAULT '[]'"),
            ("document_map", "TEXT DEFAULT '{}'"),
        ]
        for col_name, col_def in ds_cols_to_add:
            if col_name not in ds_cols:
                conn.execute(text(f"ALTER TABLE datasets ADD COLUMN {col_name} {col_def}"))

        conn.commit()
    except Exception as e:
        logger.warning(f"Schema column sync notice: {e}")

def init_db():
    # Import all models so they are registered on Base.metadata before create_all
    import backend.app.models
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        if "sqlite" in str(engine.url):
            _sync_sqlite_columns(conn)

def clear_database(clear_files: bool = False) -> dict:
    """Completely resets the SQLite database.
    Drops all tables in child-to-parent order, clears sequences,
    and cleanly reinitializes all tables and schemas from scratch.
    Optionally cleans storage uploads and exports.
    """
    import backend.app.models
    import shutil

    logger.warning("Clearing database and starting afresh...")

    # 1. Disable FK checks during drop for SQLite
    with engine.connect() as conn:
        if "sqlite" in str(engine.url):
            conn.execute(text("PRAGMA foreign_keys = OFF;"))
            conn.commit()

    # 2. Drop all tables
    Base.metadata.drop_all(bind=engine)

    # 3. Re-create all tables fresh
    Base.metadata.create_all(bind=engine)

    # 4. Re-enable FK checks and run sync
    with engine.connect() as conn:
        if "sqlite" in str(engine.url):
            conn.execute(text("PRAGMA foreign_keys = ON;"))
            _sync_sqlite_columns(conn)
            conn.commit()

    files_removed = 0
    if clear_files:
        try:
            for folder in [settings.uploads_path, settings.exports_path]:
                if folder.exists():
                    for item in folder.iterdir():
                        if item.is_file():
                            item.unlink()
                            files_removed += 1
                        elif item.is_dir():
                            shutil.rmtree(item)
                            files_removed += 1
        except Exception as file_err:
            logger.warning(f"Storage clean notice: {file_err}")

    logger.info("Database reset complete. All tables are fresh and empty.")
    return {
        "status": "success",
        "message": "Database cleared and reinitialized cleanly from scratch.",
        "tables_recreated": len(Base.metadata.tables),
        "files_removed": files_removed,
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Darkroom DataForge Database Management")
    parser.add_argument("--reset", action="store_true", help="Clear everything and start afresh")
    parser.add_argument("--clear-files", action="store_true", help="Also clear uploaded files and exports")
    args = parser.parse_args()

    if args.reset:
        res = clear_database(clear_files=args.clear_files)
        print(f"[SUCCESS] {res['message']} ({res['tables_recreated']} tables recreated)")
    else:
        init_db()
        print("[SUCCESS] Database initialized.")
