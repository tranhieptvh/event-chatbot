import pytest
from fastapi import status


VALID_PAYLOAD = {
    "name": "API Test Event",
    "date": "2026-12-30",
    "time": "19:00",
    "description": "Test Description",
    "venue_name": "Test Venue",
    "venue_address": "Test Address",
    "capacity": 200,
    "organizer_name": "Org",
    "organizer_email": "api@example.com",
    "ticket_limit": 4,
    "purchase_start": "2026-10-01",
    "purchase_end": "2026-12-25",
    "is_recurring": False,
    "category": "Workshop",
    "language": "English",
    "is_online": False,
    "seat_types": {"General": 75.0},
}


def test_health_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_event_valid_returns_201(client):
    response = client.post("/api/register-event", json=VALID_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert "API Test Event" in data["message"]


def test_register_event_missing_field_returns_422(client):
    response = client.post("/api/register-event", json={
        "name": "Incomplete Event",
        "venue_name": "Venue",
    })
    assert response.status_code == 422


def test_register_event_duplicate_returns_409(client):
    payload = VALID_PAYLOAD.copy()
    payload["name"] = "Duplicate API Event"
    payload["date"] = "2026-12-31"

    response1 = client.post("/api/register-event", json=payload)
    assert response1.status_code == 201

    response2 = client.post("/api/register-event", json=payload)
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"].lower()


@pytest.mark.skip(reason="Integration test — requires real LLM, skipped in unit runs")
def test_chat_valid_request_returns_200_with_role_scenario_message(client):
    response = client.post(
        "/api/chat",
        json={"session_id": "test-session-api", "message": "I want to create an event"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "role" in data
    assert "scenario" in data
    assert "message" in data
    assert "session_id" in data
    assert data["role"] == "assistant"


def test_chat_empty_body_returns_422(client):
    response = client.post("/api/chat", json={})
    assert response.status_code == 422


@pytest.mark.skip(reason="Integration test — requires real LLM, skipped in unit runs")
def test_get_session_existing_returns_draft_and_history(client):
    session_id = "test-session-get"
    client.post("/api/chat", json={"session_id": session_id, "message": "Create event"})

    response = client.get(f"/api/chat/session/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert "draft" in data
    assert "history" in data


def test_get_session_missing_returns_404(client):
    response = client.get("/api/chat/session/nonexistent-session")
    assert response.status_code == 404


@pytest.mark.skip(reason="Integration test — requires real LLM, skipped in unit runs")
def test_recall_returns_relevant_context(client):
    session_id = "test-session-recall"
    client.post("/api/chat", json={"session_id": session_id, "message": "Event name is Tech Summit"})
    client.post("/api/chat", json={"session_id": session_id, "message": "Venue is San Francisco"})

    response = client.get(f"/api/chat/recall/{session_id}?query=venue")
    assert response.status_code == 200
    data = response.json()
    assert "context" in data
    assert isinstance(data["context"], list)
