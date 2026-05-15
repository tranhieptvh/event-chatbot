from datetime import date, time

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import Event


def _event(**overrides) -> Event:
    base = dict(
        name="Tech Conference",
        date=date(2026, 12, 15),
        time=time(9, 30),
        description="Annual tech conference",
        venue_name="SF Convention Center",
        venue_address="747 Howard St",
        capacity=500,
        organizer_name="TechCorp",
        organizer_email="organizer@example.com",
        ticket_limit=4,
        purchase_start=date(2026, 10, 1),
        purchase_end=date(2026, 12, 10),
        is_recurring=True,
        recurrence_frequency="yearly",
        category="Conference",
        language="English",
        is_online=False,
        seat_types={"VIP": 299.99, "General": 99.99},
    )
    base.update(overrides)
    return Event(**base)


def test_insert_valid_event_persists(db_session):
    db_session.add(_event())
    db_session.commit()

    saved = db_session.query(Event).filter_by(name="Tech Conference").first()
    assert saved is not None
    assert saved.name == "Tech Conference"
    assert saved.date == date(2026, 12, 15)
    assert saved.time == time(9, 30)
    assert saved.organizer_email == "organizer@example.com"
    assert saved.seat_types == {"VIP": 299.99, "General": 99.99}


def test_insert_duplicate_raises_integrity_error(db_session):
    db_session.add(_event())
    db_session.commit()

    db_session.add(_event(venue_name="Other Venue", organizer_email="other@example.com"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_duplicate_insert_rolls_back_cleanly(db_session):
    db_session.add(_event(name="Workshop", date=date(2026, 11, 20)))
    db_session.commit()

    db_session.add(_event(name="Workshop", date=date(2026, 11, 20), venue_name="Other"))
    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()

    db_session.add(_event(name="Different Event", date=date(2026, 11, 25)))
    db_session.commit()

    saved = db_session.query(Event).filter_by(name="Different Event").first()
    assert saved is not None


def test_mid_transaction_exception_rolls_back(db_session):
    db_session.add(_event(name="Event A", date=date(2026, 10, 10)))
    db_session.flush()

    db_session.add(_event(name="Event A", date=date(2026, 10, 10), venue_name="Other"))

    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()

    count = db_session.query(Event).filter_by(name="Event A").count()
    assert count == 0


def test_update_refreshes_updated_at(db_session):
    event = _event(name="Updateable Event", date=date(2026, 12, 1))
    db_session.add(event)
    db_session.commit()

    event.venue_name = "New Venue"
    db_session.commit()
    db_session.refresh(event)

    assert event.updated_at is not None
