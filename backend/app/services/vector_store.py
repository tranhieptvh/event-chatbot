"""Vector store service using ChromaDB for conversation history and context retrieval."""
import logging
import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from app.config import settings

logger = logging.getLogger(__name__)

_chroma_client: Optional[chromadb.Client] = None


def get_vector_store() -> chromadb.Client:
    """Get or create ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_collection(session_id: str):
    """Get or create collection for a session."""
    client = get_vector_store()
    collection_name = f"session_{session_id}".replace("-", "_")
    return client.get_or_create_collection(name=collection_name)


def add_message(session_id: str, role: str, content: str) -> None:
    """Add a message to the vector store."""
    collection = get_collection(session_id)
    collection.add(
        documents=[content],
        metadatas=[{"role": role}],
        ids=[str(uuid.uuid4())],
    )


def query_context(session_id: str, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """Query relevant context from conversation history."""
    try:
        collection = get_collection(session_id)
        results = collection.query(query_texts=[query], n_results=n_results)
    except Exception:
        logger.exception("vector_store.query_context failed for session %s", session_id)
        return []

    if not results or not results.get("documents"):
        return []

    context = []
    for i, doc in enumerate(results["documents"][0]):
        metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
        context.append({"role": metadata.get("role", "unknown"), "content": doc})
    return context


def get_history(session_id: str) -> List[Dict[str, str]]:
    """Get all messages from the vector store for a session."""
    try:
        collection = get_collection(session_id)
        results = collection.get()
    except Exception:
        logger.exception("vector_store.get_history failed for session %s", session_id)
        return []

    if not results or not results.get("documents"):
        return []

    history = []
    for i, doc in enumerate(results["documents"]):
        metadata = results["metadatas"][i] if results.get("metadatas") else {}
        history.append({"role": metadata.get("role", "unknown"), "content": doc})
    return history


def delete_collection(session_id: str) -> None:
    """Delete a session's collection."""
    client = get_vector_store()
    collection_name = f"session_{session_id}".replace("-", "_")
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        logger.exception("vector_store.delete_collection failed for session %s", session_id)
