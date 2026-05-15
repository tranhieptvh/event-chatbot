import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, events
from app.config import settings
from app.services import session_service, vector_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        session_service.get_redis().ping()
        logger.info("Redis connected")
    except Exception:
        logger.exception("Redis connection failed")

    try:
        vector_store.get_vector_store()
        logger.info("ChromaDB initialized")
    except Exception:
        logger.exception("ChromaDB initialization failed")

    yield


app = FastAPI(title="Event Creation Chatbot", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/")
async def root():
    return {"message": "Event Chatbot API"}
