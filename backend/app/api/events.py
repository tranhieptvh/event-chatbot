import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Event
from app.schemas.event import EventCreate
from app.services import event_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _serialize_event(e: Event) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "date": e.date.isoformat() if e.date else None,
        "time": e.time.strftime("%H:%M") if e.time else None,
        "description": e.description,
        "seat_types": e.seat_types,
        "purchase_start": e.purchase_start.isoformat() if e.purchase_start else None,
        "purchase_end": e.purchase_end.isoformat() if e.purchase_end else None,
        "ticket_limit": e.ticket_limit,
        "venue_name": e.venue_name,
        "venue_address": e.venue_address,
        "capacity": e.capacity,
        "organizer_name": e.organizer_name,
        "organizer_email": e.organizer_email,
        "category": e.category,
        "language": e.language,
        "is_recurring": e.is_recurring,
        "recurrence_frequency": e.recurrence_frequency,
        "is_online": e.is_online,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/events")
def list_events(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    events = db.query(Event).order_by(Event.date).all()
    return [_serialize_event(e) for e in events]


@router.post("/register-event", status_code=status.HTTP_201_CREATED)
def register_event(event: EventCreate, db: Session = Depends(get_db)):
    """Register a new event.

    FastAPI validates the body against ``EventCreate`` and returns 422 on
    invalid input. This handler only deals with persistence outcomes.
    """
    try:
        event_service.insert(event, db)
    except event_service.DuplicateEventError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        logger.exception("register-event failed for %s", event.name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save event.",
        )
    return {
        "status": "success",
        "message": f"Event '{event.name}' registered successfully.",
    }
