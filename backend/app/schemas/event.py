from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator


REQUIRED_FIELDS = [
    'name', 'date', 'time', 'description',
    'seat_types', 'purchase_start', 'purchase_end', 'ticket_limit',
    'venue_name', 'venue_address', 'capacity',
    'organizer_name', 'organizer_email',
    'category', 'language', 'is_recurring', 'is_online',
]


def _parse_iso_date(value: str) -> datetime:
    return datetime.strptime(value, '%Y-%m-%d')


class EventDraft(BaseModel):
    """Incremental draft built up through chat. All fields optional."""

    name: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    description: Optional[str] = None

    seat_types: Optional[Dict[str, float]] = None
    purchase_start: Optional[str] = None
    purchase_end: Optional[str] = None
    ticket_limit: Optional[int] = None

    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    capacity: Optional[int] = None

    organizer_name: Optional[str] = None
    organizer_email: Optional[str] = None

    category: Optional[str] = None
    language: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_frequency: Optional[str] = None
    is_online: Optional[bool] = None

    def missing_fields(self) -> list:
        missing = [f for f in REQUIRED_FIELDS if getattr(self, f) is None]
        if self.is_recurring and not self.recurrence_frequency:
            missing.append('recurrence_frequency')
        return missing

    def is_complete(self) -> bool:
        if self.missing_fields():
            return False
        return bool(self.seat_types)


class EventCreate(BaseModel):
    """Validated event ready to persist. Strict types, all required fields enforced."""

    name: str
    date: str
    time: str
    description: str

    seat_types: Dict[str, float]
    purchase_start: str
    purchase_end: str
    ticket_limit: int

    venue_name: str
    venue_address: str
    capacity: int

    organizer_name: str
    organizer_email: EmailStr

    category: str
    language: str
    is_recurring: bool
    recurrence_frequency: Optional[str] = None
    is_online: bool

    @field_validator('date', 'purchase_start', 'purchase_end')
    @classmethod
    def _date_format(cls, v: str) -> str:
        try:
            _parse_iso_date(v)
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v

    @field_validator('time')
    @classmethod
    def _time_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError('Time must be in HH:MM (24-hour) format')
        return v

    @field_validator('ticket_limit')
    @classmethod
    def _positive_ticket_limit(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Ticket limit must be greater than 0')
        return v

    @field_validator('capacity')
    @classmethod
    def _positive_capacity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Capacity must be greater than 0')
        return v

    @field_validator('seat_types')
    @classmethod
    def _seat_types_valid(cls, v: Dict[str, float]) -> Dict[str, float]:
        if not v:
            raise ValueError('Seat types cannot be empty')
        for seat_name, price in v.items():
            if price <= 0:
                raise ValueError(f'Seat price for {seat_name!r} must be greater than 0')
        return v

    @model_validator(mode='after')
    def _date_relationships(self):
        start = _parse_iso_date(self.purchase_start)
        end = _parse_iso_date(self.purchase_end)
        event = _parse_iso_date(self.date)

        if end <= start:
            raise ValueError('Purchase end must be after purchase start')
        if end >= event:
            raise ValueError('Purchase end must be before event date')

        if self.is_recurring and not self.recurrence_frequency:
            raise ValueError('Recurrence frequency is required when event is recurring')

        return self
