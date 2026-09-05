import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BACKEND_DIR, "spend_intel.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
if DATABASE_URL.startswith("sqlite:///."):
    DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH}"

# connect_args={"check_same_thread": False} is required for SQLite in multithreaded FastAPI apps
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize all tables and auto-migrate missing columns for SQLite."""
    Base.metadata.create_all(bind=engine)
    
    # Safe SQLite schema migration
    from sqlalchemy import text
    with engine.connect() as conn:
        # Check and add scan_run_id to transactions
        try:
            res = conn.execute(text("PRAGMA table_info(transactions)")).fetchall()
            col_names = [r[1] for r in res]
            if "scan_run_id" not in col_names and len(col_names) > 0:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN scan_run_id INTEGER REFERENCES scan_runs(id) ON DELETE CASCADE"))
                conn.commit()
                print("[DB MIGRATION] Added scan_run_id column to transactions table.")
        except Exception as e:
            print(f"[DB MIGRATION NOTICE] transactions scan_run_id check: {e}")

        # Check and add scan_run_id to anomaly_flags
        try:
            res = conn.execute(text("PRAGMA table_info(anomaly_flags)")).fetchall()
            col_names = [r[1] for r in res]
            if "scan_run_id" not in col_names and len(col_names) > 0:
                conn.execute(text("ALTER TABLE anomaly_flags ADD COLUMN scan_run_id INTEGER REFERENCES scan_runs(id) ON DELETE CASCADE"))
                conn.commit()
                print("[DB MIGRATION] Added scan_run_id column to anomaly_flags table.")
        except Exception as e:
            print(f"[DB MIGRATION NOTICE] anomaly_flags scan_run_id check: {e}")


