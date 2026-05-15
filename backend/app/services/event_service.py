from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schemas.event import EventCreate
from app.db.models import Event


class DuplicateEventError(Exception):
    """Raised when attempting to create a duplicate event (same name + date)."""


def check_duplicate(name: str, event_date, db: Session) -> None:
    """Raise DuplicateEventError if (name, date) already exists."""
    if isinstance(event_date, str):
        event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
    existing = db.query(Event).filter_by(name=name, date=event_date).first()
    if existing:
        raise DuplicateEventError(f"Event '{name}' on {event_date} already exists")


def insert(event_create: EventCreate, db: Session) -> int:
    """Insert an event into the DB. Returns the new event ID."""
    try:
        event = Event(
            name=event_create.name,
            date=datetime.strptime(event_create.date, "%Y-%m-%d").date(),
            time=datetime.strptime(event_create.time, "%H:%M").time(),
            description=event_create.description,
            seat_types=event_create.seat_types,
            purchase_start=datetime.strptime(event_create.purchase_start, "%Y-%m-%d").date(),
            purchase_end=datetime.strptime(event_create.purchase_end, "%Y-%m-%d").date(),
            ticket_limit=event_create.ticket_limit,
            venue_name=event_create.venue_name,
            venue_address=event_create.venue_address,
            capacity=event_create.capacity,
            organizer_name=event_create.organizer_name,
            organizer_email=event_create.organizer_email,
            category=event_create.category,
            language=event_create.language,
            is_recurring=event_create.is_recurring,
            recurrence_frequency=event_create.recurrence_frequency,
            is_online=event_create.is_online,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event.id
    except IntegrityError:
        db.rollback()
        raise DuplicateEventError(
            f"Event '{event_create.name}' on {event_create.date} already exists"
        )
