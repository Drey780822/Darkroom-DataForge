import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

logger = logging.getLogger("dataforge.database")

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
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        if "sqlite" in str(engine.url):
            _sync_sqlite_columns(conn)
