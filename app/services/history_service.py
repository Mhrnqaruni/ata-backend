# /app/services/history_service.py (FINAL, CORRECTED, SQL-COMPATIBLE VERSION)

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
        # --- [THE FIX IS HERE] ---
        # We now save the dictionary directly. SQLAlchemy's JSON type will handle serialization.
        "settings_snapshot": settings,
        # --- [END OF FIX] ---
        "generated_content": generated_content,
    }
    
    # This returns the newly created SQLAlchemy Generation object
    new_generation_obj = db.add_generation_record(history_record_data)
    
    # --- [THE SECOND FIX IS HERE] ---
    # Pydantic's `model_validate` with `from_attributes=True` will now work seamlessly
    # because our `history_model.GenerationRecord` expects a datetime object and a dict,
    # which is exactly what the SQLAlchemy object provides.
    return GenerationRecord.model_validate(new_generation_obj)
    # --- [END OF FIX] ---


def delete_generation(db: DatabaseService, generation_id: str) -> bool:
    """
    Deletes a generation record from the database by delegating to the database service.
    """
    # --- [THE FIX IS HERE] ---
    # This now correctly calls the method we added to the DatabaseService facade.
    was_deleted = db.delete_generation_record(generation_id)
    return was_deleted
    # --- [END OF FIX] ---


def get_history(
    db: DatabaseService,
    search: Optional[str] = None,
    tool_id: Optional[str] = None
) -> HistoryResponse:
    """
    Retrieves the user's AI generation history from the database,
    processes it, and performs filtering.
    """
    # This now returns a list of SQLAlchemy Generation objects
    all_history_objects = db.get_all_generations()
    
    # --- [THE FIX IS HERE] ---
    # The conversion from SQLAlchemy object to Pydantic model is now much simpler.
    # Pydantic handles the type validation directly.
    processed_records = [GenerationRecord.model_validate(obj) for obj in all_history_objects]
    # --- [END OF FIX] ---

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
    
    # The sorting also works perfectly on the Pydantic models.
    # Note: The database query already sorts, but this is a safe fallback.
    filtered_results.sort(key=lambda r: r.created_at, reverse=True)
    
    return HistoryResponse(
        results=filtered_results,
        total=len(filtered_results),
        page=1,
        hasNextPage=False
    )