from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, String, Text, Time, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.session import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    description = Column(Text, nullable=False)

    # Tickets
    seat_types = Column(JSONB, nullable=False)
    purchase_start = Column(Date, nullable=False)
    purchase_end = Column(Date, nullable=False)
    ticket_limit = Column(Integer, nullable=False)

    # Venue
    venue_name = Column(String(255), nullable=False)
    venue_address = Column(String(255), nullable=False)
    capacity = Column(Integer, nullable=False)

    # Organizer
    organizer_name = Column(String(255), nullable=False)
    organizer_email = Column(String(255), nullable=False)

    # Other
    category = Column(String(100), nullable=False)
    language = Column(String(50), nullable=False)
    is_recurring = Column(Boolean, nullable=False, default=False)
    recurrence_frequency = Column(String(50), nullable=True)
    is_online = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('name', 'date', name='uix_event_name_date'),
    )
