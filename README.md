# Event Creation Chatbot

An AI-powered chatbot that guides users through creating events via conversation, validates inputs, and persists data to PostgreSQL.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Running Tests](#running-tests)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)
- [Sample Conversation & Test Plans](#sample-conversation--test-plans)

---

## Project Overview

A full-stack event registration system where users interact with an AI chatbot to create events through natural conversation. The chatbot extracts structured event data from free-form input, validates it, and saves it to PostgreSQL.

**Core Features:**
- Conversational event creation with multi-turn dialogue
- Structured data extraction from natural language (LangChain + OpenAI or Gemini — switchable via `LLM_PROVIDER` flag)
- Input validation and error handling (Pydantic)
- Duplicate event detection (same name + date)
- Conversation history stored in ChromaDB for semantic recall
- Session management via Redis
- Responsive chat widget UI (React + TypeScript)

## LLM Provider Configuration

Default provider is OpenAI. Switch by setting `LLM_PROVIDER` in `.env`:

```env
# Use OpenAI (default — pay-as-you-go)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4o-mini

# Use Gemini (free tier available, ~20 req/day on Google's free quota)
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your-google-key
GEMINI_MODEL=gemini-2.5-flash-lite
```

Both providers are wrapped through LangChain (`langchain_openai` and `langchain_google_genai`) and exposed via a unified `LLMProvider` interface in [backend/app/services/llm_provider.py](backend/app/services/llm_provider.py). To add a new provider, extend the abstract `LLMProvider` class and register it in `get_llm_provider()`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.10+ |
| AI / Conversation | LangChain + OpenAI / Google Gemini (switchable) |
| Data Validation | Pydantic v2 |
| Vector / Memory DB | ChromaDB |
| Session Store | Redis 7 |
| Relational DB | PostgreSQL 16 |
| Migrations | Alembic |
| Frontend | React 18, TypeScript, TailwindCSS, Vite |
| Infrastructure | Docker, Docker Compose |
| Testing | pytest, FastAPI TestClient |

How each item maps onto specific files & responsibilities: [docs/tech_stack.md](docs/tech_stack.md).

---

## Architecture

```
event-chatbot/
├── backend/    # FastAPI API + LangChain conversation engine
├── frontend/   # React SPA (chat widget)
└── docker-compose.yml
```

### High-Level Architecture

```
┌─────────────────┐
│ React Frontend  │ (Port 5173)
│  TypeScript     │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  FastAPI API    │ (Port 8000)
│  Python 3.10+   │
└──┬──────────┬───┘
   │          │
   ▼          ▼
┌──────┐  ┌──────────┐
│ PG16 │  │  Redis   │  ChromaDB (local)
└──────┘  └──────────┘
```

### Backend Architecture

```
HTTP Request
    ↓
Router (api/chat.py, api/events.py)
    ↓
ConversationService (LangChain → LLMProvider)
    ↓
EventService (validation, duplicate check, insert)
    ↓
SessionService (Redis) + VectorStore (ChromaDB)
    ↓
SQLAlchemy Models (db/models.py) → PostgreSQL
```

**Key Components:**
- **api/chat.py**: Chat endpoint — accepts messages, delegates to ConversationService; also exposes session & recall endpoints
- **api/events.py**: Event CRUD — list and register events
- **services/conversation.py**: Multi-turn dialogue logic, field extraction via LangChain
- **services/llm_provider.py**: Unified abstraction over OpenAI / Gemini (switchable via `LLM_PROVIDER`)
- **services/event_service.py**: Pydantic validation, duplicate detection, DB insert
- **services/session_service.py**: Redis-backed session draft and history
- **services/vector_store.py**: ChromaDB embeddings for semantic context retrieval
- **schemas/**: Pydantic request/response models (`event.py`, `chat.py`)
- **db/models.py**: SQLAlchemy ORM model (`Event` table)
- **db/migrations/**: Alembic migration scripts
- **db/seeds/**: Optional seed data scripts

### Frontend Architecture

```
App.tsx
    ↓
ChatWidget (popup widget)
    ↓
useChat hook (session management, API calls)
    ↓
api.ts (axios / fetch to backend)
    ↓
MessageList + MessageBubble + InputBar + EventList
```

---

## Project Structure

```
event-chatbot/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── chat.py             # Chat, session & recall endpoints
│   │   │   └── events.py           # Event list & register endpoints
│   │   ├── db/
│   │   │   ├── models.py           # SQLAlchemy ORM model (Event table)
│   │   │   ├── session.py          # SQLAlchemy session factory
│   │   │   ├── migrations/         # Alembic migrations (env.py + versions/)
│   │   │   └── seeds/
│   │   │       └── events.py       # Optional seed data
│   │   ├── schemas/
│   │   │   ├── event.py            # Pydantic EventCreate schema
│   │   │   └── chat.py             # Pydantic ChatRequest/ChatResponse
│   │   ├── prompts/
│   │   │   ├── system_prompt.txt
│   │   │   └── extraction_prompt.txt
│   │   ├── services/
│   │   │   ├── conversation.py     # LangChain conversation engine
│   │   │   ├── llm_provider.py     # Unified OpenAI/Gemini interface
│   │   │   ├── event_service.py    # Validation & DB insert
│   │   │   ├── session_service.py  # Redis session management
│   │   │   └── vector_store.py     # ChromaDB integration
│   │   ├── config.py               # Settings (pydantic-settings)
│   │   └── main.py                 # FastAPI app, CORS, lifespan
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   ├── test_conversation.py
│   │   ├── test_event_service.py
│   │   ├── test_models.py
│   │   └── test_db.py
│   ├── alembic.ini                 # script_location = app/db/migrations
│   ├── pytest.ini
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWidget.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── InputBar.tsx
│   │   │   └── EventList.tsx
│   │   ├── hooks/
│   │   │   └── useChat.ts
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── styles/
│   │   │   └── chat.css
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Prerequisites

- Docker 20.10+ and Docker Compose 2.x
- An OpenAI API key **or** a Google AI API key (Gemini) — pick one via `LLM_PROVIDER`
- (For local development without Docker) Python 3.10+, Node.js 18+, PostgreSQL 16, Redis 7

---

## Installation & Setup

### Option A: Docker (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd event-chatbot

# Copy and configure environment
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
# (or set LLM_PROVIDER=gemini and GOOGLE_API_KEY for the Gemini path)

# Build and start all services
docker compose up -d --build

# Run database migrations
docker compose exec app alembic upgrade head

# Seed initial data (optional)
docker compose exec app python -m app.db.seeds.events
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

**Services:**

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

**Docker Commands:**

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f app
docker compose logs -f frontend

# Rebuild after code changes
docker compose up -d --build

# Clean rebuild (remove containers, volumes, images)
docker compose down -v
docker compose up -d --build
```

### Option B: Local Development

Make sure PostgreSQL 16 and Redis 7 are running locally first.

#### Backend

```bash
# From event-chatbot/ root: prepare .env
cp .env.example .env
# Edit .env — for local dev (no Docker), switch hosts to localhost:
#   DATABASE_URL=postgresql://chatbot:chatbot@localhost:5432/event_chatbot
#   REDIS_URL=redis://localhost:6379/0
# Also set OPENAI_API_KEY (or LLM_PROVIDER=gemini + GOOGLE_API_KEY)

cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations (alembic.ini points to app/db/migrations)
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
# API available at http://localhost:8000
```

#### Frontend

```bash
cd frontend
npm install

# Vite reads BACKEND_URL from process.env (see vite.config.js) — pass it inline:
BACKEND_URL=http://localhost:8000 npm run dev
# App available at http://localhost:5173
```

---

## Running Tests

Tests run inside the `app` container with an in-memory SQLite database + `fakeredis`. The LLM provider is stubbed, so no API calls are made and tests are deterministic.

```bash
# Run all tests
docker compose exec app pytest

# Run with verbose output
docker compose exec app pytest -v

# Run a specific test file
docker compose exec app pytest tests/test_api.py
docker compose exec app pytest tests/test_event_service.py
docker compose exec app pytest tests/test_conversation.py
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/api/health` | Service health status |
| POST | `/api/chat` | Send a chat message |
| GET | `/api/chat/session/{session_id}` | Get session draft and history |
| GET | `/api/chat/recall/{session_id}?query=...` | Semantic context retrieval |
| GET | `/api/events` | List all registered events |
| POST | `/api/register-event` | Register a new event |

### Example Requests

**Send a chat message:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to create an event",
    "session_id": "my-session-123"
  }'
```

**Response:**
```json
{
  "session_id": "my-session-123",
  "role": "assistant",
  "scenario": "missing_field",
  "message": "What's the name of your event?"
}
```

**Get session draft:**
```bash
curl http://localhost:8000/api/chat/session/my-session-123
```

**List events:**
```bash
curl http://localhost:8000/api/events
```

**Register event directly:**
```bash
curl -X POST http://localhost:8000/api/register-event \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kyoto Jazz Night",
    "date": "2027-03-10",
    "time": "19:00",
    "description": "Jazz performance at Kyoto Concert Hall",
    "seat_types": {"VIP": 10000, "Regular": 5000},
    "ticket_limit": 4,
    "purchase_start": "2027-01-01",
    "purchase_end": "2027-03-09",
    "venue_name": "Kyoto Concert Hall",
    "venue_address": "123 Sakyo-ku, Kyoto",
    "capacity": 1000,
    "organizer_name": "Fenix Entertainment",
    "organizer_email": "info@fenix.co.jp",
    "category": "Concert",
    "language": "Japanese",
    "is_recurring": false,
    "is_online": false
  }'
```

Responses:
- `201 Created` with `{"status":"success","message":"Event 'X' registered successfully."}` on success
- `409 Conflict` if an event with the same name + date already exists
- `422 Unprocessable Entity` for schema/format violations (FastAPI returns field-level errors)
- `500 Internal Server Error` for other persistence failures

### Response Scenarios

| `scenario` | When triggered |
|------------|----------------|
| `missing_field` | A required field has not been provided yet |
| `invalid_input` | Input is wrong format or invalid value |
| `confirmation` | All fields collected — summary before saving |
| `success_save` | Event saved to database successfully |
| `error_db` | Database save failed or connection error |
| `update_previous_field` | User corrects a previously provided value |

---

## Environment Variables

```env
# Database
POSTGRES_USER=chatbot
POSTGRES_PASSWORD=chatbot
POSTGRES_DB=event_chatbot

# LLM Provider — "openai" (default) or "gemini"
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite

# Backend
DATABASE_URL=postgresql://chatbot:chatbot@db:5432/event_chatbot
REDIS_URL=redis://redis:6379/0
SESSION_TTL_SECONDS=1800
CHROMA_PERSIST_DIR=./chroma_data
APP_ENV=development
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Frontend
BACKEND_URL=http://app:8000

# Host ports
DB_PORT=5432
REDIS_PORT=6379
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

---

## Sample Conversation & Test Plans

- [docs/sample_conversation.md](docs/sample_conversation.md) — narrative transcripts for a successful event-creation flow and invalid-input handling.
- [docs/ui_test_scenarios.md](docs/ui_test_scenarios.md) — 6 manual scenarios for exercising every response tag (`missing_field`, `invalid_input`, `update_previous_field`, `confirmation`, `success_save`, `error_db`) via the web UI.

The bot collects fields in the order defined by `FIELD_PRIORITY` in [backend/app/services/conversation.py](backend/app/services/conversation.py):
`name → date → time → description → venue_name → venue_address → capacity → organizer_name → organizer_email → ticket_limit → purchase_start → purchase_end → is_recurring → (recurrence_frequency if recurring) → category → language → is_online → seat_types`.

All 17 fields are required per the spec; `recurrence_frequency` is only asked when `is_recurring=true`.
