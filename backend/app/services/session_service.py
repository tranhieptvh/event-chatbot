"""Session management service using Redis for storing conversation state."""
import json
from typing import Optional, Dict, Any, List

import redis

from app.config import settings


_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def get_draft(session_id: str) -> Optional[Dict[str, Any]]:
    """Get event draft from Redis."""
    client = get_redis()
    key = f"draft:{session_id}"
    data = client.get(key)
    if data:
        return json.loads(data)
    return None


def set_draft(session_id: str, draft: Dict[str, Any]) -> None:
    """Save event draft to Redis with TTL."""
    client = get_redis()
    key = f"draft:{session_id}"
    client.setex(key, settings.SESSION_TTL_SECONDS, json.dumps(draft))


def get_history(session_id: str) -> List[Dict[str, str]]:
    """Get conversation history from Redis (stored as a Redis LIST)."""
    client = get_redis()
    items = client.lrange(f"history:{session_id}", 0, -1)
    return [json.loads(item) for item in items]


def append_history(session_id: str, role: str, content: str) -> None:
    """Append message to conversation history. O(1) via RPUSH."""
    client = get_redis()
    key = f"history:{session_id}"
    client.rpush(key, json.dumps({"role": role, "content": content}))
    client.expire(key, settings.SESSION_TTL_SECONDS)


def delete_session(session_id: str) -> None:
    """Delete session data from Redis."""
    client = get_redis()
    client.delete(f"draft:{session_id}", f"history:{session_id}")
