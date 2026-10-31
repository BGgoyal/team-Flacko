import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SESSION_SECRET", "test-secret")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "")
os.environ.setdefault("TWILIO_VERIFY_SERVICE_SID", "")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("ANGEL_ONE_API_KEY", "")
os.environ.setdefault("ANGEL_ONE_JWT_TOKEN", "")

from app.config import get_settings  # noqa: E402
from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def authed_client(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "learner@example.com", "password": "password1", "name": "Asha"},
    )
    assert response.status_code == 200
    return client
