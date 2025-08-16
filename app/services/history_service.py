# /app/services/history_service.py (FINAL, HARDENED, SQL-COMPATIBLE VERSION)

import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import os

from .database_service import DatabaseService
from ..models.history_model import GenerationRecord, HistoryResponse
from ..models.tool_model import ToolId

# --- HELPER FUNCTION (Unchanged and Correct) ---
def _generate_title_from_settings(settings: Dict[str, Any], source_filename: Optional[str] = None) -> str:
    """
    Intelligently generates a concise title for a history record based on its settings.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    source_preview = "Untitled Generation"
    if source_filename:
        source_preview = source_filename
    elif settings.get("selected_chapter_paths"):
        try:
            book_name = settings["selected_chapter_paths"][0].split(os.path.sep)[-2]
            source_preview = book_name
        except IndexError:
            source_preview = "Library Selection"
    elif settings.get("source_text"):
        source_preview = ' '.join(settings["source_text"].split()[:5])
        if len(settings["source_text"].split()) > 5:
            source_preview += "..."
    if len(source_preview) > 50:
        source_preview = source_preview[:47] + "..."
    return f"{date_str}: {source_preview}"


# --- PUBLIC SERVICE FUNCTIONS (Corrected) ---

def save_generation(
    db: DatabaseService,
    tool_id: str,
    settings: Dict[str, Any],
    generated_content: str,
    source_filename: Optional[str] = None
) -> GenerationRecord:
    """
    Constructs a history record, generates its title, persists it,
    and returns a validated Pydantic model.
    """
    title = _generate_title_from_settings(settings, source_filename)

    history_record_data = {
        "id": f"gen_{uuid.uuid4().hex[:16]}",
        "title": title,
        "tool_id": tool_id,
        "settings_snapshot": settings, # Pass the dictionary directly
        "generated_content": generated_content,
    }
    
    new_generation_obj = db.add_generation_record(history_record_data)
    
    # Pydantic's `model_validate` with `from_attributes=True` will now work seamlessly
    return GenerationRecord.model_validate(new_generation_obj)


def delete_generation(db: DatabaseService, generation_id: str) -> bool:
    """
    Deletes a generation record from the database by delegating to the database service.
    """
    was_deleted = db.delete_generation_record(generation_id)
    return was_deleted


def get_history(
    db: DatabaseService,
    search: Optional[str] = None,
    tool_id: Optional[str] = None
) -> HistoryResponse:
    """
    Retrieves the user's AI generation history from the database,
    processes it, and performs filtering. This is the corrected,
    SQL-compatible version for the "read" path.
    """
    all_history_objects = db.get_all_generations()
    
    processed_records = []
    for record_obj in all_history_objects:
        try:
            # --- [THE FIX IS HERE] ---
            # Create the Pydantic model from the SQLAlchemy object first.
            pydantic_record = GenerationRecord.model_validate(record_obj)
            
            # Now, explicitly check if the snapshot is a string and parse it.
            # This makes the code robust to however the DB driver returns the JSON.
            if isinstance(pydantic_record.settings_snapshot, str):
                pydantic_record.settings_snapshot = json.loads(pydantic_record.settings_snapshot)
            # --- [END OF FIX] ---
            
            processed_records.append(pydantic_record)

        except Exception as e:
            print(f"Skipping corrupted history record: {getattr(record_obj, 'id', 'N/A')}. Error: {e}")
            continue

    # The rest of the filtering logic works perfectly on the list of Pydantic models.
    filtered_results = processed_records
    if tool_id:
        filtered_results = [r for r in filtered_results if r.tool_id.value == tool_id]
    if search:
        search_lower = search.lower()
        filtered_results = [
            r for r in filtered_results 
            if search_lower in r.generated_content.lower() or search_lower in r.title.lower()
        ]
    
    filtered_results.sort(key=lambda r: r.created_at, reverse=True)
    
    return HistoryResponse(
        results=filtered_results,
        total=len(filtered_results),
        page=1,
        hasNextPage=False
    )