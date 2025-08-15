# /ata-backend/app/routers/chatbot_router.py

# --- [THE FIX IS HERE: ADD 'Response' TO THE IMPORT] ---
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Response, status, HTTPException
# --- [END OF FIX] ---
from typing import List
import json

from ..services import chatbot_service, database_service
from ..models import chatbot_model

router = APIRouter()

@router.get(
    "/sessions",
    response_model=List[chatbot_model.ChatSessionSummary],
    summary="Get Chat History",
    description="Retrieves a list of all past chat session summaries for the user."
)
def get_chat_sessions(
    db: database_service.DatabaseService = Depends(database_service.get_db_service)
):
    user_id = "user_v1_demo" 
    return db.get_chat_sessions_by_user_id(user_id)


# Add inside the chatbot_router.py file, after the GET /sessions endpoint

@router.get(
    "/sessions/{session_id}",
    response_model=chatbot_model.ChatSessionDetail,
    summary="Get a Single Chat Session with History",
    description="Retrieves the full details and message history for a specific chat session."
)
def get_chat_session_details(
    session_id: str,
    db: database_service.DatabaseService = Depends(database_service.get_db_service)
):
    user_id = "user_v1_demo" # In V2, this comes from an auth dependency.
    
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
    db: database_service.DatabaseService = Depends(database_service.get_db_service)
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
    db: database_service.DatabaseService = Depends(database_service.get_db_service)
):
    user_id = "user_v1_demo"
    
    was_deleted = chatbot_service.delete_chat_session_logic(session_id, user_id, db)
    
    if not was_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session with ID {session_id} not found or user does not have permission.",
        )
    
    # This line will now work correctly because 'Response' has been imported.
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: database_service.DatabaseService = Depends(database_service.get_db_service)
):
    # ... (The WebSocket endpoint code remains unchanged and is correct) ...
    user_id = "user_v1_demo"
    session = db.get_chat_session_by_id(session_id)
    
    if not session or session.get("user_id") != user_id:
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



