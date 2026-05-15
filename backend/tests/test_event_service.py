from datetime import date

import pytest

from app.services import event_service
from app.schemas.event import EventCreate
from app.db.models import Event


VALID_DATA = {
    "name": "New Event",
    "date": "2026-12-20",
    "time": "19:00",
    "description": "A sample event.",
    "venue_name": "New Venue",
    "venue_address": "Some Street",
    "capacity": 500,
    "organizer_name": "Org",
    "organizer_email": "new@example.com",
    "ticket_limit": 4,
    "purchase_start": "2026-10-01",
    "purchase_end": "2026-12-15",
    "is_recurring": False,
    "category": "Concert",
    "language": "English",
    "is_online": False,
    "seat_types": {"VIP": 100.0},
}


def test_check_duplicate_raises_when_event_exists(db_session):
    db_session.add(Event(
        name="Existing Event",
        date=date(2026, 12, 15),
        time=__import__('datetime').time(19, 0),
        description="A sample event.",
        venue_name="Venue",
        venue_address="Addr",
        capacity=100,
        organizer_name="Org",
        organizer_email="test@example.com",
        ticket_limit=4,
        purchase_start=date(2026, 10, 1),
        purchase_end=date(2026, 12, 10),
        is_recurring=False,
        category="Concert",
        language="English",
        is_online=False,
        seat_types={"General": 50.0},
    ))
    db_session.commit()

    with pytest.raises(event_service.DuplicateEventError):
        event_service.check_duplicate("Existing Event", date(2026, 12, 15), db_session)


def test_insert_returns_new_event_id(db_session):
    event_data = EventCreate(**VALID_DATA)
    event_id = event_service.insert(event_data, db_session)

    assert event_id is not None
    assert isinstance(event_id, int)

    saved = db_session.query(Event).filter_by(id=event_id).first()
    assert saved is not None
    assert saved.name == "New Event"
    assert saved.seat_types == {"VIP": 100.0}


def test_insert_wraps_integrity_error_as_duplicate_error(db_session):
    data = VALID_DATA.copy()
    data["name"] = "Duplicate Test"
    data["date"] = "2026-12-25"
    event_service.insert(EventCreate(**data), db_session)

    duplicate = VALID_DATA.copy()
    duplicate["name"] = "Duplicate Test"
    duplicate["date"] = "2026-12-25"
    duplicate["venue_name"] = "Different Venue"
    duplicate["organizer_email"] = "other@example.com"

    with pytest.raises(event_service.DuplicateEventError):
        event_service.insert(EventCreate(**duplicate), db_session)
