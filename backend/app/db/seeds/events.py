"""Seed events table with sample data.

Assumes the schema has already been created by Alembic (`alembic upgrade head`).
"""
import sys
from datetime import datetime

from app.db.session import SessionLocal
from app.db.models import Event

EVENTS = [
    {
        "name": "Kyoto Jazz Night",
        "date": "2026-03-10",
        "time": "19:00",
        "description": "A live jazz performance in Kyoto featuring local and international artists.",
        "venue_name": "Kyoto Concert Hall",
        "venue_address": "1-26 Hanakawacho, Sakyo-ku, Kyoto",
        "capacity": 1000,
        "organizer_name": "Fenix Entertainment",
        "organizer_email": "info@fenix.co.jp",
        "ticket_limit": 4,
        "purchase_start": "2026-01-01",
        "purchase_end": "2026-03-09",
        "is_recurring": False,
        "recurrence_frequency": None,
        "category": "Concert",
        "language": "Japanese",
        "is_online": False,
        "seat_types": {"VIP": 10000, "Regular": 5000, "Standing": 3000},
    },
    {
        "name": "AI Engineering Summit 2026",
        "date": "2026-06-15",
        "time": "09:00",
        "description": "Annual conference on applied AI engineering covering LLMs, agents, and evaluation.",
        "venue_name": "Tokyo International Forum",
        "venue_address": "3-5-1 Marunouchi, Chiyoda, Tokyo",
        "capacity": 800,
        "organizer_name": "AI Engineering Society",
        "organizer_email": "summit@aieng.org",
        "ticket_limit": 2,
        "purchase_start": "2026-03-01",
        "purchase_end": "2026-06-14",
        "is_recurring": True,
        "recurrence_frequency": "yearly",
        "category": "Conference",
        "language": "English",
        "is_online": False,
        "seat_types": {"Standard": 25000, "Workshop Pass": 60000, "Speaker": 0},
    },
    {
        "name": "Remote Web3 Hackathon",
        "date": "2026-08-22",
        "time": "10:00",
        "description": "48-hour online hackathon for Web3 builders. Prizes for best dApp and best tooling.",
        "venue_name": "Online (Discord + Devpost)",
        "venue_address": "N/A",
        "capacity": 500,
        "organizer_name": "Open Builders",
        "organizer_email": "hack@openbuilders.dev",
        "ticket_limit": 1,
        "purchase_start": "2026-06-01",
        "purchase_end": "2026-08-21",
        "is_recurring": False,
        "recurrence_frequency": None,
        "category": "Hackathon",
        "language": "English",
        "is_online": True,
        "seat_types": {"Participant": 0, "Sponsor": 100000},
    },
]


def _parse_date(s: str):
    return datetime.strptime(s, "%Y-%m-%d").date()


def _parse_time(s: str):
    return datetime.strptime(s, "%H:%M").time()


def run() -> None:
    db = SessionLocal()
    inserted = skipped = 0
    try:
        for data in EVENTS:
            event_date = _parse_date(data["date"])
            if db.query(Event).filter_by(name=data["name"], date=event_date).first():
                print(f"  skip   {data['name']} ({data['date']}) — already exists")
                skipped += 1
                continue

            db.add(Event(
                name=data["name"],
                date=event_date,
                time=_parse_time(data["time"]),
                description=data["description"],
                seat_types=data["seat_types"],
                purchase_start=_parse_date(data["purchase_start"]),
                purchase_end=_parse_date(data["purchase_end"]),
                ticket_limit=data["ticket_limit"],
                venue_name=data["venue_name"],
                venue_address=data["venue_address"],
                capacity=data["capacity"],
                organizer_name=data["organizer_name"],
                organizer_email=data["organizer_email"],
                category=data["category"],
                language=data["language"],
                is_recurring=data["is_recurring"],
                recurrence_frequency=data["recurrence_frequency"],
                is_online=data["is_online"],
            ))
            print(f"  insert {data['name']} ({data['date']})")
            inserted += 1

        db.commit()
        print(f"\nDone: {inserted} inserted, {skipped} skipped.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run()
