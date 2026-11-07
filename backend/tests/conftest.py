"""Pytest fixtures for MAPORA backend tests."""

import os
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Force testing environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test_mapora_secret_key_1234567890_abcdef"
os.environ["STORAGE_BACKEND"] = "local"

from app.core.config import settings
from app.core.security import get_password_hash, create_access_token, UserRole
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User

# In-memory SQLite engine for fast, isolated tests
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all tables in memory once for the test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Provide a clean transactional session for each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """Test client overriding the get_db dependency."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create a verified admin user."""
    admin = User(
        email="admin@mapora.test",
        hashed_password=get_password_hash("AdminSecretPass1!"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Return JWT access token for admin."""
    return create_access_token(admin_user.id, admin_user.email, admin_user.role)


@pytest.fixture
def surveyor_user(db: Session) -> User:
    """Create primary surveyor user."""
    surveyor = User(
        email="surveyor1@mapora.test",
        hashed_password=get_password_hash("SurveyorPass1!"),
        role=UserRole.SURVEYOR.value,
        is_active=True,
    )
    db.add(surveyor)
    db.commit()
    db.refresh(surveyor)
    return surveyor


@pytest.fixture
def surveyor_token(surveyor_user: User) -> str:
    """Return JWT access token for surveyor."""
    return create_access_token(surveyor_user.id, surveyor_user.email, surveyor_user.role)


@pytest.fixture
def other_surveyor_user(db: Session) -> User:
    """Create secondary surveyor user for cross-user isolation testing."""
    other = User(
        email="surveyor2@mapora.test",
        hashed_password=get_password_hash("SurveyorPass2!"),
        role=UserRole.SURVEYOR.value,
        is_active=True,
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    return other


@pytest.fixture
def other_surveyor_token(other_surveyor_user: User) -> str:
    """Return JWT access token for secondary surveyor."""
    return create_access_token(other_surveyor_user.id, other_surveyor_user.email, other_surveyor_user.role)
