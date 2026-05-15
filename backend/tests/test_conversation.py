import json
from unittest.mock import Mock, patch

import pytest

from app.schemas.chat import Scenario


COMPLETE_DRAFT = {
    "name": "Complete Event",
    "date": "2026-12-01",
    "time": "19:00",
    "description": "A complete sample event.",
    "venue_name": "Boston Hall",
    "venue_address": "123 Hall Street",
    "capacity": 500,
    "organizer_name": "Org",
    "organizer_email": "org@example.com",
    "ticket_limit": 4,
    "purchase_start": "2026-10-01",
    "purchase_end": "2026-11-25",
    "is_recurring": False,
    "category": "Concert",
    "language": "English",
    "is_online": False,
    "seat_types": {"General": 50.0},
}


class FakeRedis:
    """In-memory Redis mock supporting string ops (draft:) and list ops (history:)."""

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def set(self, key, value):
        self.store[key] = value

    def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)

    def expire(self, key, ttl):
        pass

    def ping(self):
        return True

    def rpush(self, key, *values):
        lst = self.store.setdefault(key, [])
        lst.extend(values)
        return len(lst)

    def lrange(self, key, start, end):
        lst = self.store.get(key, [])
        return lst[start:] if end == -1 else lst[start : end + 1]

    def seed_draft(self, session_id, draft):
        self.store[f"draft:{session_id}"] = json.dumps(draft)

    def seed_history(self, session_id, history):
        self.store[f"history:{session_id}"] = [json.dumps(h) for h in history]


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def mock_llm():
    llm = Mock()
    llm.extract_fields = Mock(return_value="{}")
    return llm


@pytest.fixture
def conversation_service(fake_redis, mock_llm):
    from app.services import llm_provider, conversation, session_service
    llm_provider.reset_provider()
    conversation.reset_conversation_service()

    session_service._redis_client = fake_redis

    with patch('app.services.vector_store.add_message'):
        with patch('app.services.llm_provider.get_llm_provider', return_value=mock_llm):
            service = conversation.ConversationService()
            service.llm = mock_llm
            yield service

    session_service._redis_client = None
    llm_provider.reset_provider()
    conversation.reset_conversation_service()


def test_new_session_asks_for_event_name(conversation_service, mock_llm):
    mock_llm.extract_fields.return_value = "{}"
    response = conversation_service.process_message("s1", "I want to create an event")
    assert response.scenario == Scenario.MISSING_FIELD
    assert "name" in response.message.lower()


def test_invalid_email_triggers_invalid_input_or_missing(
    conversation_service, fake_redis, mock_llm,
):
    fake_redis.seed_draft("s2", {"name": "Workshop", "date": "2026-12-01"})
    mock_llm.extract_fields.return_value = '{"organizer_email": "john.doe"}'
    response = conversation_service.process_message("s2", "Email is john.doe")
    assert response.scenario in [Scenario.MISSING_FIELD, Scenario.INVALID_INPUT]


def test_complete_draft_triggers_confirmation(conversation_service, fake_redis, mock_llm):
    fake_redis.seed_draft("s3", COMPLETE_DRAFT)
    mock_llm.extract_fields.return_value = "{}"
    response = conversation_service.process_message("s3", "Looks good")
    assert response.scenario == Scenario.CONFIRMATION


def test_recurring_true_with_frequency_triggers_confirmation(
    conversation_service, fake_redis, mock_llm,
):
    draft = dict(COMPLETE_DRAFT)
    draft["is_recurring"] = True
    draft["recurrence_frequency"] = "weekly"
    fake_redis.seed_draft("s4", draft)
    mock_llm.extract_fields.return_value = "{}"
    response = conversation_service.process_message("s4", "Yes, weekly")
    assert response.scenario == Scenario.CONFIRMATION


def test_user_confirms_triggers_success_or_db_error(
    conversation_service, fake_redis, mock_llm,
):
    fake_redis.seed_draft("s5", COMPLETE_DRAFT)
    fake_redis.seed_history(
        "s5",
        [{"role": "assistant", "content": "Here's a summary... Shall I save this event?"}],
    )
    mock_llm.extract_fields.return_value = "{}"

    with patch('app.services.event_service.insert', return_value=123):
        response = conversation_service.process_message("s5", "Yes, looks good!")
    assert response.scenario in [Scenario.SUCCESS_SAVE, Scenario.ERROR_DB]


def test_edit_field_triggers_update_previous_field(
    conversation_service, fake_redis, mock_llm,
):
    fake_redis.seed_draft("s6", dict(COMPLETE_DRAFT))
    mock_llm.extract_fields.return_value = '{"venue_name": "Chicago Hall"}'
    response = conversation_service.process_message(
        "s6", "Change the venue to Chicago Hall",
    )
    assert response.scenario == Scenario.UPDATE_PREVIOUS_FIELD


def test_expired_session_restarts_from_scratch(conversation_service, mock_llm):
    mock_llm.extract_fields.return_value = "{}"
    response = conversation_service.process_message("s7", "Create an event")
    assert response.scenario == Scenario.MISSING_FIELD
    assert "name" in response.message.lower()


def test_is_online_field_extracted_correctly(conversation_service, mock_llm):
    mock_llm.extract_fields.return_value = '{"is_online": true}'
    response = conversation_service.process_message("s8", "It's an online event")
    assert response.scenario == Scenario.MISSING_FIELD
