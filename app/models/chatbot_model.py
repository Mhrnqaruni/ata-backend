# /ata-backend/app/models/chatbot_model.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ChatMessage(BaseModel):
    """
    Defines the shape of a single message. Used for persisting and retrieving
    conversation history.
    """
    role: str = Field(..., description="The role of the message author, either 'user' or 'bot'.")
    content: str = Field(..., description="The text content of the message.")
    file_id: Optional[str] = Field(None, description="An optional ID for a file associated with this message.")

class ChatSessionSummary(BaseModel):
    """
    A lightweight summary of a chat session.
    PURPOSE: Used for the response of the GET /api/chat/sessions endpoint.
    """
    id: str = Field(..., description="The unique ID of the chat session.")
    name: str = Field(..., description="The auto-generated name of the chat session.")
    created_at: datetime = Field(..., description="The timestamp when the session was created.")

class ChatSessionDetail(ChatSessionSummary):
    """
    Represents the full detail of a single chat session, including its complete message history.
    PURPOSE: Used for the response of the GET /api/chat/sessions/{session_id} endpoint.
    """
    history: List[ChatMessage] = Field(..., description="The complete list of messages in the conversation.")

# --- [THE FIX IS HERE] ---
class NewChatSessionRequest(BaseModel):
    """
    Defines the request body for creating a new chat session.
    PURPOSE: Used by the POST /api/chat/sessions endpoint.
    """
    # Fields are now camelCase to match JavaScript/JSON conventions.
    firstMessage: str = Field(..., alias="first_message")
    fileId: Optional[str] = Field(None, alias="file_id")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "firstMessage": "What was the class average on the Mid-Term Exam?",
                "fileId": "file_abc123"
            }
        }
# --- [END OF FIX] ---

class CreateChatSessionResponse(BaseModel):
    """
    Defines the response when a new chat session is created via REST.
    """
    sessionId: str = Field(..., description="The unique ID of the newly created chat session.")