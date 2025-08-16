# /ata-backend/app/routers/chatbot_router.py (FINAL, SQL-COMPATIBLE VERSION)

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Response, status, HTTPException
from typing import List
import json

# Import the service and the Pydantic models
from ..services import chatbot_service
from ..services.database_service import DatabaseService, get_db_service
from ..models import chatbot_model

router = APIRouter()

# --- REST ENDPOINTS FOR SESSION MANAGEMENT ---
# These endpoints are already correct and do not need changes, as they delegate
# to the now-corrected chatbot_service.

@router.get(
    "/sessions",
    response_model=List[chatbot_model.ChatSessionSummary],
    summary="Get Chat History",
    description="Retrieves a list of all past chat session summaries for the user."
)
def get_chat_sessions(
    db: DatabaseService = Depends(get_db_service)
):
    user_id = "user_v1_demo" 
    return db.get_chat_sessions_by_user_id(user_id)


@router.get(
    "/sessions/{session_id}",
    response_model=chatbot_model.ChatSessionDetail,
    summary="Get a Single Chat Session with History",
    description="Retrieves the full details and message history for a specific chat session."
)
def get_chat_session_details(
    session_id: str,
    db: DatabaseService = Depends(get_db_service)
):
    user_id = "user_v1_demo"
    details = chatbot_service.get_chat_session_details_logic(session_id, user_id, db)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session with ID {session_id} not found or user does not have permission.",
        )
    return details


@router.post(
    "/sessions",
    response_model=chatbot_model.CreateChatSessionResponse,
    summary="Create a New Chat Session",
    description="Initiates a new chat session and returns its unique ID."
)
def create_new_chat_session(
    request: chatbot_model.NewChatSessionRequest,
    db: DatabaseService = Depends(get_db_service)
):
    user_id = "user_v1_demo"
    session_info = chatbot_service.start_new_chat_session(user_id, request, db)
    return session_info

@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Chat Session",
    description="Permanently deletes a chat session and all of its associated messages."
)
def delete_chat_session(
    session_id: str,
    db: DatabaseService = Depends(get_db_service)
):
    user_id = "user_v1_demo"
    was_deleted = chatbot_service.delete_chat_session_logic(session_id, user_id, db)
    if not was_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session with ID {session_id} not found or user does not have permission.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- REAL-TIME WEBSOCKET ENDPOINT ---

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: DatabaseService = Depends(get_db_service)
):
    user_id = "user_v1_demo"
    # session is now a SQLAlchemy ChatSession object
    session = db.get_chat_session_by_id(session_id)
    
    # --- [THE FIX IS HERE] ---
    # Use attribute access (session.user_id) for the authorization check
    # instead of the old dictionary-style access (session.get("user_id")).
    if not session or session.user_id != user_id:
    # --- [END OF FIX] ---
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data.get("type") == "user_message":
                message_text = message_data.get("payload", {}).get("text")
                file_id = message_data.get("payload", {}).get("file_id")

                if message_text:
                    await chatbot_service.add_new_message_to_session(
                        session_id=session_id,
                        user_id=user_id,
                        message_text=message_text,
                        file_id=file_id,
                        db=db,
                        websocket=websocket
                    )
            
    except WebSocketDisconnect:
        print(f"Client disconnected from chat session: {session_id}")
    except Exception as e:
        print(f"An unexpected error occurred in WebSocket for session {session_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error", 
                "payload": {"message": "A server error occurred. Please try reconnecting."}
            })
        except Exception:
            pass