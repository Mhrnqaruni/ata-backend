# /ata-backend/app/services/chatbot_service.py (FINAL, CORRECTED, SQL-COMPATIBLE VERSION)

from typing import Dict, Optional
from datetime import datetime
import uuid
import json
import asyncio
import re
from fastapi import WebSocket

from .database_service import DatabaseService
from ..models import chatbot_model
from . import gemini_service, prompt_library

from RestrictedPython import compile_restricted, safe_globals
import pandas as pd

# --- This section is unchanged and correct ---
class PrintCollector:
    def __init__(self): self.text = ""
    def __call__(self, *args): self.text += " ".join(map(str, args)) + "\n"
    def _call_print(self, *args): self.__call__(*args)

def _generate_chat_name(first_message: str) -> str:
    return " ".join(first_message.split()[:5]) + ("..." if len(first_message.split()) > 5 else "")

async def _generate_code_plan(user_id: str, query_text: str, db: DatabaseService) -> str:
    # ... (This function is correct and remains unchanged)
    classes_df = db.get_classes_as_dataframe(user_id=user_id)
    students_df = db.get_students_as_dataframe(user_id=user_id)
    assessments_df = db.get_assessments_as_dataframe(user_id=user_id)
    schema = f"""
- `classes_df`: columns: {list(classes_df.columns)}
- `students_df`: columns: {list(students_df.columns)}
- `assessments_df`: columns: {list(assessments_df.columns)}
"""
    prompt = prompt_library.CODE_GENERATION_PROMPT.format(schema=schema, query=query_text)
    try:
        response_json = await gemini_service.generate_json(prompt, temperature=0.1)
        return response_json["code"]
    except (KeyError, ValueError) as e:
        raise ValueError(f"AI failed to generate a valid code plan. Error: {e}")

async def _execute_code_in_sandbox(user_id: str, code_to_execute: str, db: DatabaseService) -> str:
    # ... (This function is correct and remains unchanged)
    def sync_execute():
        classes_df = db.get_classes_as_dataframe(user_id=user_id)
        students_df = db.get_students_as_dataframe(user_id=user_id)
        assessments_df = db.get_assessments_as_dataframe(user_id=user_id)
        output_capture = []
        def capture_output(*args): output_capture.append(" ".join(map(str, args)))
        restricted_globals = safe_globals.copy()
        restricted_globals['pd'] = pd
        restricted_globals['classes_df'] = classes_df
        restricted_globals['students_df'] = students_df
        restricted_globals['assessments_df'] = assessments_df
        restricted_globals['capture_output'] = capture_output
        restricted_globals['_getitem_'] = lambda obj, key: obj[key]
        modified_code = code_to_execute.replace("print(", "capture_output(")
        try:
            byte_code = compile_restricted(modified_code, '<string>', 'exec')
            exec(byte_code, restricted_globals, None)
            raw_result = "\n".join(output_capture).strip()
        except Exception as e:
            print("--- FAILING AI-GENERATED CODE (Original) ---"); print(code_to_execute); print("------------------------------------------")
            raise ValueError(f"The analysis plan failed during execution: {e}")
        if not raw_result: return "The analysis ran successfully but produced no output."
        return raw_result
    return await asyncio.to_thread(sync_execute)

async def _synthesize_natural_language_response(query_text: str, raw_result: str, websocket: WebSocket) -> str:
    # ... (This function is correct and remains unchanged)
    prompt = prompt_library.NATURAL_LANGUAGE_SYNTHESIS_PROMPT.format(query=query_text, data=raw_result)
    return await gemini_service.generate_text_streaming(prompt, websocket)

def start_new_chat_session(user_id: str, request: chatbot_model.NewChatSessionRequest, db: DatabaseService) -> Dict:
    # ... (This function is correct and remains unchanged)
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    session_name = _generate_chat_name(request.firstMessage)
    session_record = {"id": session_id, "user_id": user_id, "name": session_name, "created_at": datetime.now().isoformat()}
    db.create_chat_session(session_record)
    return {"sessionId": session_id}

async def add_new_message_to_session(session_id: str, user_id: str, message_text: str, file_id: Optional[str], db: DatabaseService, websocket: WebSocket):
    # ... (This function is correct and remains unchanged)
    user_message_record = {"id": f"msg_{uuid.uuid4().hex[:12]}", "session_id": session_id, "role": "user", "content": message_text, "file_id": file_id, "created_at": datetime.now().isoformat()}
    db.add_chat_message(user_message_record)
    bot_response_text = ""
    try:
        code_plan = await _generate_code_plan(user_id, message_text, db)
        raw_result = await _execute_code_in_sandbox(user_id, code_plan, db)
        bot_response_text = await _synthesize_natural_language_response(message_text, raw_result, websocket)
    except Exception as e:
        print(f"Error in agentic loop for session {session_id}: {e}")
        error_message = f"Sorry, I encountered an error and could not answer your question."
        await websocket.send_json({"type": "error", "payload": {"message": error_message}})
        bot_response_text = f"Agentic Loop Error: {e}"
    if bot_response_text:
        bot_message_record = {"id": f"msg_{uuid.uuid4().hex[:12]}", "session_id": session_id, "role": "bot", "content": bot_response_text, "file_id": None, "created_at": datetime.now().isoformat()}
        db.add_chat_message(bot_message_record)

# --- [THIS SECTION IS REWRITTEN] ---

def delete_chat_session_logic(session_id: str, user_id: str, db: DatabaseService) -> bool:
    """
    Business logic to safely delete a chat session.
    This performs an ownership check before deleting.
    """
    session = db.get_chat_session_by_id(session_id) # This is now a ChatSession object
    
    # Use attribute access (session.user_id) instead of dictionary access
    if not session or session.user_id != user_id:
        return False # Fails authorization

    # The database service's delete_chat_session method will now handle the cascading delete
    # of messages automatically because of the relationship we defined in the SQLAlchemy model.
    return db.delete_chat_session(session_id)


def get_chat_session_details_logic(session_id: str, user_id: str, db: DatabaseService) -> Optional[Dict]:
    """
    Business logic to get the full details of a chat session, including history.
    Performs an ownership check.
    """
    session = db.get_chat_session_by_id(session_id) # ChatSession object
    
    # Use attribute access (session.user_id) instead of dictionary access
    if not session or session.user_id != user_id:
        return None # Fails authorization

    messages = db.get_messages_by_session_id(session_id) # List of ChatMessage objects
    
    # Assemble the data to match the ChatSessionDetail Pydantic model.
    # Because our Pydantic model has `from_attributes = True`, we can pass the
    # SQLAlchemy objects directly and Pydantic will serialize them correctly.
    session_details = {
        "id": session.id,
        "name": session.name,
        "created_at": session.created_at,
        "history": messages 
    }
    return session_details

# --- [END OF REWRITTEN SECTION] ---