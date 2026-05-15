import pytest
from pydantic import ValidationError

from app.schemas.event import EventDraft, EventCreate
from app.schemas.chat import Scenario


VALID_EVENT_DATA = {
    "name": "Tech Conference 2026",
    "date": "2026-12-15",
    "time": "09:30",
    "description": "Annual tech conference",
    "venue_name": "SF Convention Center",
    "venue_address": "747 Howard St, San Francisco",
    "capacity": 1000,
    "organizer_name": "TechCorp",
    "organizer_email": "organizer@example.com",
    "ticket_limit": 4,
    "purchase_start": "2026-10-01",
    "purchase_end": "2026-12-10",
    "is_recurring": True,
    "recurrence_frequency": "yearly",
    "category": "Conference",
    "language": "English",
    "is_online": False,
    "seat_types": {"VIP": 299.99, "General": 99.99},
}


def _data(**overrides):
    data = VALID_EVENT_DATA.copy()
    data.update(overrides)
    return data


def test_event_create_valid_full():
    event = EventCreate(**VALID_EVENT_DATA)
    assert event.name == "Tech Conference 2026"
    assert event.ticket_limit == 4
    assert event.seat_types == {"VIP": 299.99, "General": 99.99}


def test_event_create_rejects_invalid_date_format():
    with pytest.raises(ValidationError) as exc_info:
        EventCreate(**_data(date="15-12-2026"))
    assert "date" in str(exc_info.value).lower()


def test_event_create_rejects_invalid_time_format():
    with pytest.raises(ValidationError) as exc_info:
        EventCreate(**_data(time="7pm"))
    assert "time" in str(exc_info.value).lower()


def test_event_create_rejects_invalid_email():
    with pytest.raises(ValidationError) as exc_info:
        EventCreate(**_data(organizer_email="not-an-email"))
    assert "email" in str(exc_info.value).lower()


def test_event_create_rejects_purchase_end_before_start():
    with pytest.raises(ValidationError) as exc_info:
        EventCreate(**_data(purchase_start="2026-12-01", purchase_end="2026-11-01"))
    assert "purchase" in str(exc_info.value).lower()


def test_event_create_rejects_purchase_end_on_or_after_event_date():
    with pytest.raises(ValidationError) as exc_info:
        EventCreate(**_data(purchase_end="2026-12-15"))
    assert "purchase" in str(exc_info.value).lower() and "end" in str(exc_info.value).lower()


def test_event_create_rejects_missing_recurrence_frequency_when_recurring():
    with pytest.raises(ValidationError) as exc_info:
        EventCreate(**_data(is_recurring=True, recurrence_frequency=None))
    assert "recurrence" in str(exc_info.value).lower()


def test_event_create_allows_no_frequency_when_not_recurring():
    event = EventCreate(**_data(is_recurring=False, recurrence_frequency=None))
    assert event.is_recurring is False
    assert event.recurrence_frequency is None


def test_event_create_rejects_zero_ticket_limit():
    with pytest.raises(ValidationError) as exc_info:
        EventCreate(**_data(ticket_limit=0))
    assert "ticket_limit" in str(exc_info.value).lower()


def test_event_create_rejects_zero_capacity():
    with pytest.raises(ValidationError) as exc_info:
        EventCreate(**_data(capacity=0))
    assert "capacity" in str(exc_info.value).lower()


def test_event_create_rejects_empty_seat_types():
    with pytest.raises(ValidationError) as exc_info:
        EventCreate(**_data(seat_types={}))
    assert "seat_types" in str(exc_info.value).lower()


def test_event_create_rejects_nonpositive_seat_price():
    with pytest.raises(ValidationError) as exc_info:
        EventCreate(**_data(seat_types={"VIP": 0.0}))
    assert "price" in str(exc_info.value).lower()


def test_event_create_requires_description_category_language_is_online():
    for field in ("description", "category", "language", "is_online"):
        data = _data()
        data.pop(field)
        with pytest.raises(ValidationError) as exc_info:
            EventCreate(**data)
        assert field in str(exc_info.value).lower()


def test_event_draft_missing_fields_lists_unfilled():
    draft = EventDraft(
        name="Event",
        date="2026-12-15",
        venue_name=None,
        organizer_email=None,
    )
    missing = draft.missing_fields()
    assert "venue_name" in missing
    assert "organizer_email" in missing
    assert "name" not in missing


def test_event_draft_is_complete_when_all_required_set():
    draft = EventDraft(
        name="Event",
        date="2026-12-15",
        time="19:00",
        description="A sample event.",
        venue_name="Venue",
        venue_address="123 Street",
        capacity=500,
        organizer_name="Org",
        organizer_email="test@example.com",
        ticket_limit=4,
        purchase_start="2026-10-01",
        purchase_end="2026-12-10",
        is_recurring=False,
        category="Concert",
        language="English",
        is_online=False,
        seat_types={"General": 50.0},
    )
    assert draft.is_complete() is True


def test_event_draft_not_complete_without_seat_types():
    draft = EventDraft(
        name="Event",
        date="2026-12-15",
        time="19:00",
        venue_name="Venue",
        venue_address="123 Street",
        capacity=500,
        organizer_name="Org",
        organizer_email="test@example.com",
        ticket_limit=4,
        purchase_start="2026-10-01",
        purchase_end="2026-12-10",
        is_recurring=False,
        seat_types={},
    )
    assert draft.is_complete() is False


def test_scenario_enum_has_required_values():
    assert hasattr(Scenario, "MISSING_FIELD")
    assert hasattr(Scenario, "INVALID_INPUT")
    assert hasattr(Scenario, "CONFIRMATION")
    assert hasattr(Scenario, "SUCCESS_SAVE")
    assert hasattr(Scenario, "ERROR_DB")
    assert hasattr(Scenario, "UPDATE_PREVIOUS_FIELD")
