"""Database session management with SQLAlchemy 2.x and resilient fallback."""

import os
from pathlib import Path
import socket
from typing import Generator
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import logger


def _is_database_port_open(url: str, timeout: float = 0.3) -> bool:
    """Fast probe to determine if database host and port are listening before connection attempts."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def get_sqlite_fallback_url() -> str:
    """Return absolute SQLite fallback database URL located in backend directory."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    db_file = (backend_dir / "mapora_dev.db").resolve()
    return f"sqlite:///{db_file.as_posix()}"


def create_resilient_engine():
    """Create a database engine with fast fallback to SQLite if PostgreSQL is unreachable."""
    if settings.ENVIRONMENT == "testing" or os.environ.get("ENVIRONMENT") == "testing":
        return create_engine(
            "sqlite:///:memory:",
            echo=settings.SQL_ECHO,
            connect_args={"check_same_thread": False},
        )

    database_url = settings.DATABASE_URL
    fallback_url = get_sqlite_fallback_url()

    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            echo=settings.SQL_ECHO,
            connect_args={"check_same_thread": False},
        )

    # Check if remote or local PostgreSQL port is listening
    if not _is_database_port_open(database_url, timeout=0.3):
        logger.warning(
            f"Primary database ({database_url}) is unreachable (port not listening). "
            f"Falling back to local SQLite database: {fallback_url}"
        )
        return create_engine(
            fallback_url,
            echo=settings.SQL_ECHO,
            connect_args={"check_same_thread": False},
        )

    try:
        # Test connecting with a short timeout
        test_engine = create_engine(
            database_url,
            echo=settings.SQL_ECHO,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3} if "psycopg" in database_url else {},
        )
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Successfully connected to primary database: {database_url.split('@')[-1] if '@' in database_url else 'local'}")
        return test_engine
    except Exception as e:
        logger.warning(
            f"Primary database ({database_url}) connection failed: {e}. "
            f"Falling back to local SQLite database: {fallback_url}"
        )
        return create_engine(
            fallback_url,
            echo=settings.SQL_ECHO,
            connect_args={"check_same_thread": False},
        )


engine = create_resilient_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency providing a transactional database session per request."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
