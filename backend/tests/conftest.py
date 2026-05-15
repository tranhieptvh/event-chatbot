from unittest.mock import Mock

import pytest
import fakeredis
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.session import Base, get_db


TEST_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Fresh DB session per test, wrapped in a transaction that rolls back."""
    Base.metadata.create_all(bind=engine)

    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def mock_llm_provider(request, monkeypatch):
    """Auto-mock the LLM provider so tests never hit real Gemini/OpenAI APIs.

    Tests that need the LLM client can request the `mock_llm` fixture directly
    to inspect/customize the canned response.
    """
    if "no_mock_llm" in request.keywords:
        yield None
        return

    mock_llm = Mock()
    mock_llm.extract_fields = Mock(return_value="{}")

    from app.services import llm_provider, conversation
    llm_provider.reset_provider()
    conversation.reset_conversation_service()

    monkeypatch.setattr(llm_provider, "get_llm_provider", lambda: mock_llm)

    yield mock_llm

    llm_provider.reset_provider()
    conversation.reset_conversation_service()


@pytest.fixture(autouse=True)
def fake_redis_client(monkeypatch):
    """Auto-replace the Redis client with fakeredis so tests never need a real broker."""
    from app.services import session_service
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(session_service, "_redis_client", fake)
    yield fake
    monkeypatch.setattr(session_service, "_redis_client", None)


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient with the DB dependency overridden to use the rolled-back session."""
    from app.main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm(mock_llm_provider):
    """Alias for tests that want to customize the LLM mock response."""
    return mock_llm_provider
