# /ata-backend/app/services/chatbot_service.py (FINAL, HARDENED, PANDAS-DECOUPLED VERSION)

from typing import Dict, Optional, List
from datetime import datetime
import uuid
import json
import asyncio
from fastapi import WebSocket

from .database_service import DatabaseService
from ..models import chatbot_model
from . import gemini_service, prompt_library

from RestrictedPython import compile_restricted, safe_globals
# We no longer need pandas in this file for the sandbox
# import pandas as pd

# --- Helper Functions ---
# This section is unchanged and correct.
class PrintCollector:
    def __init__(self): self.text = ""
    def __call__(self, *args): self.text += " ".join(map(str, args)) + "\n"
    def _call_print(self, *args): self.__call__(*args)

def _generate_chat_name(first_message: str) -> str:
    return " ".join(first_message.split()[:5]) + ("..." if len(first_message.split()) > 5 else "")


# --- [START OF REFACTORED AGENTIC LOOP] ---

async def _generate_code_plan(user_id: str, query_text: str, db: DatabaseService) -> str:
    """
    Step 1 of the agentic loop: Generate a Python script based on a schema of lists of dictionaries.
    """
    # Fetch the data as simple, secure lists of dictionaries
    classes_list = db.get_classes_for_chatbot(user_id=user_id)
    students_list = db.get_students_for_chatbot(user_id=user_id)
    assessments_list = db.get_assessments_for_chatbot(user_id=user_id)
    
    # Describe the schema of the dictionaries for the AI
    schema = f"""
- `classes`: A list of dictionaries. Each dictionary has keys: {list(classes_list[0].keys()) if classes_list else ['id', 'name', 'description']}
- `students`: A list of dictionaries. Each dictionary has keys: {list(students_list[0].keys()) if students_list else ['id', 'name', 'studentId', 'class_id', 'overallGrade']}
- `assessments`: A list of dictionaries. Each dictionary has keys: {list(assessments_list[0].keys()) if assessments_list else ['id', 'job_id', 'student_id', 'grade', 'feedback']}
"""
    # Use the new, updated prompt from the library
    prompt = prompt_library.CODE_GENERATION_PROMPT.format(schema=schema, query=query_text)
    try:
        response_json = await gemini_service.generate_json(prompt, temperature=0.1)
        return response_json["code"]
    except (KeyError, ValueError) as e:
        raise ValueError(f"AI failed to generate a valid code plan. Error: {e}")

async def _execute_code_in_sandbox(user_id: str, code_to_execute: str, db: DatabaseService) -> str:
    """
    Step 2 of the agentic loop: Securely execute the AI-generated code without pandas.
    """
    
    def sync_execute():
        # Fetch the data as simple lists of dictionaries
        classes_list = db.get_classes_for_chatbot(user_id=user_id)
        students_list = db.get_students_for_chatbot(user_id=user_id)
        assessments_list = db.get_assessments_for_chatbot(user_id=user_id)

        output_capture = []
        def capture_output(*args):
            output_capture.append(" ".join(map(str, args)))

        restricted_globals = safe_globals.copy()
        # DO NOT inject the pandas library. Inject the simple lists instead.
        restricted_globals['classes'] = classes_list
        restricted_globals['students'] = students_list
        restricted_globals['assessments'] = assessments_list
        restricted_globals['_print_'] = capture_output
        
        # _getitem_ is still useful for safe dictionary access like `c['name']`
        restricted_globals['_getitem_'] = lambda obj, key: obj[key]
        
        # The AI will now generate code with print(), so no replacement is needed.
        modified_code = code_to_execute

        try:
            byte_code = compile_restricted(modified_code, '<string>', 'exec')
            exec(byte_code, restricted_globals, None)
            raw_result = "\n".join(output_capture).strip()
        except Exception as e:
            print("--- FAILING AI-GENERATED CODE (Original) ---")
            print(code_to_execute)
            print("------------------------------------------")
            raise ValueError(f"The analysis plan failed during execution: {e}")

        if not raw_result:
            return "The analysis ran successfully but produced no output."
            
        return raw_result
    
    return await asyncio.to_thread(sync_execute)

# --- [END OF REFACTORED AGENTIC LOOP] ---


async def _synthesize_natural_language_response(query_text: str, raw_result: str, websocket: WebSocket) -> str:
    """Step 3 of the agentic loop: Convert the raw result into a natural language response."""
    prompt = prompt_library.NATURAL_LANGUAGE_SYNTHESIS_PROMPT.format(query=query_text, data=raw_result)
    return await gemini_service.generate_text_streaming(prompt, websocket)


# --- Public Service Functions ---
# This section is now fully correct and SQL-compatible.

def start_new_chat_session(user_id: str, request: chatbot_model.NewChatSessionRequest, db: DatabaseService) -> Dict:
    """Creates a new chat session record in the database."""
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    session_name = _generate_chat_name(request.first_message)
    session_record = {
        "id": session_id, 
        "user_id": user_id, 
        "name": session_name,
        # created_at is handled by the database default
    }
    db.create_chat_session(session_record)
    return {"sessionId": session_id}

async def add_new_message_to_session(session_id: str, user_id: str, message_text: str, file_id: Optional[str], db: DatabaseService, websocket: WebSocket):
    """Orchestrates the full agentic loop for a single user message."""
    user_message_record = {
        "id": f"msg_{uuid.uuid4().hex[:12]}", 
        "session_id": session_id, 
        "role": "user", 
        "content": message_text, 
        "file_id": file_id
    }
    db.add_chat_message(user_message_record)
    
    bot_response_text = ""
    try:
        # Execute the newly refactored, safer agentic loop
        code_plan = await _generate_code_plan(user_id, message_text, db)
        raw_result = await _execute_code_in_sandbox(user_id, code_plan, db)
        bot_response_text = await _synthesize_natural_language_response(message_text, raw_result, websocket)
    except Exception as e:
        print(f"Error in agentic loop for session {session_id}: {e}")
        error_message = f"Sorry, I encountered an error and could not answer your question."
        await websocket.send_json({"type": "error", "payload": {"message": error_message}})
        bot_response_text = f"Agentic Loop Error: {e}" # Save the error for debugging
        
    if bot_response_text:
        bot_message_record = {
            "id": f"msg_{uuid.uuid4().hex[:12]}", 
            "session_id": session_id, 
            "role": "bot", 
            "content": bot_response_text, 
            "file_id": None
        }
        db.add_chat_message(bot_message_record)

def delete_chat_session_logic(session_id: str, user_id: str, db: DatabaseService) -> bool:
    """Business logic to safely delete a chat session."""
    session = db.get_chat_session_by_id(session_id)
    if not session or session.user_id != user_id:
        return False
    return db.delete_chat_session(session_id)


def get_chat_session_details_logic(session_id: str, user_id: str, db: DatabaseService) -> Optional[Dict]:
    """Business logic to get the full details of a chat session."""
    session = db.get_chat_session_by_id(session_id)
    if not session or session.user_id != user_id:
        return None

    messages = db.get_messages_by_session_id(session_id)
    
    session_details = {
        "id": session.id,
        "name": session.name,
        "created_at": session.created_at,
        "history": messages 
    }
    return session_details