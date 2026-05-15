from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Scenario(str, Enum):
    """Conversation scenarios for chatbot responses."""
    MISSING_FIELD = "missing_field"
    INVALID_INPUT = "invalid_input"
    CONFIRMATION = "confirmation"
    SUCCESS_SAVE = "success_save"
    ERROR_DB = "error_db"
    UPDATE_PREVIOUS_FIELD = "update_previous_field"


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    session_id: str
    role: str
    scenario: Scenario
    message: str
