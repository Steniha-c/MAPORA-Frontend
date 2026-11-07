"""Database session management with SQLAlchemy 2.x and resilient fallback."""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import logger


def create_resilient_engine():
    """Create a database engine with fallback to SQLite if PostgreSQL is unreachable."""
    database_url = settings.DATABASE_URL
    connect_args = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(database_url, echo=settings.SQL_ECHO, connect_args=connect_args)

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
            f"Primary database ({database_url}) is unreachable: {e}. "
            "Falling back to local SQLite database: sqlite:///./mapora_dev.db"
        )
        fallback_url = "sqlite:///./mapora_dev.db"
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
