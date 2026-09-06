"""backend 테스트가 공유하는 픽스처.

DB 와 TestClient 를 세우는 방식은 라우터마다 같아야 한다. 파일마다 다시
쓰면 한 곳만 고쳐지고 나머지가 조용히 옛 방식으로 남는다.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from backend.database.database import get_db
from backend.database.models import Base
from backend.main import app
from core import config


@pytest.fixture(name="db_session")
def fixture_db_session():
    """테스트마다 새 인메모리 DB. StaticPool 이라야 커넥션이 공유된다."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture(name="client")
def fixture_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="secret")
def fixture_secret(monkeypatch):
    monkeypatch.setattr(config, "SESSION_SECRET", "test-secret-key-do-not-use")
