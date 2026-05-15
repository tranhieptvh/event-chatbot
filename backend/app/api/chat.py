from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import uuid

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.conversation import get_conversation_service
from app.services import session_service, vector_store

router = APIRouter()


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Process chat message and return response."""
    # Generate session_id if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    # Get conversation service
    conv_service = get_conversation_service()
    
    # Process message
    response = conv_service.process_message(session_id, request.message)
    
    return response


@router.get("/chat/session/{session_id}")
def get_session(session_id: str):
    """Get session draft and history."""
    draft = session_service.get_draft(session_id)
    history = session_service.get_history(session_id)
    
    if draft is None and not history:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "draft": draft or {},
        "history": history
    }


@router.get("/chat/recall/{session_id}")
def recall_context(session_id: str, query: str = Query(..., description="Query string for context retrieval")):
    """Retrieve relevant context from conversation history."""
    context = vector_store.query_context(session_id, query, n_results=5)
    
    return {
        "session_id": session_id,
        "query": query,
        "context": context
    }
