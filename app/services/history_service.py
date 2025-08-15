# /app/services/history_service.py

import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import os

from .database_service import DatabaseService
from ..models.history_model import GenerationRecord, HistoryResponse
from ..models.tool_model import ToolId

# --- [START] DEFINITIVELY CORRECTED TITLE GENERATION HELPER ---
def _generate_title_from_settings(settings: Dict[str, Any], source_filename: Optional[str] = None) -> str:
    """
    Intelligently generates a concise title for a history record based on its settings.
    This version correctly handles all three source types in the correct order of priority.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    source_preview = "Untitled Generation" # Default fallback

    # Priority 1: Use the uploaded filename if it exists. This is the most specific source.
    if source_filename:
        source_preview = source_filename
    # Priority 2: If no file, use the book name from library paths.
    elif settings.get("selected_chapter_paths"):
        try:
            # Assumes path like ../Books/Level/Year/Subject/Book Name/Chapter.txt
            book_name = settings["selected_chapter_paths"][0].split(os.path.sep)[-2]
            source_preview = book_name
        except IndexError:
            source_preview = "Library Selection"
    # Priority 3: If no file or library, use a preview of the source text.
    elif settings.get("source_text"):
        # Create a preview of the first 5 words
        source_preview = ' '.join(settings["source_text"].split()[:5])
        if len(settings["source_text"].split()) > 5:
            source_preview += "..."
    
    # Truncate long previews to keep titles clean and readable in the UI
    if len(source_preview) > 50:
        source_preview = source_preview[:47] + "..."

    return f"{date_str}: {source_preview}"
# --- [END] DEFINITIVELY CORRECTED TITLE GENERATION HELPER ---


def save_generation(
    db: DatabaseService,
    tool_id: str,
    settings: Dict[str, Any],
    generated_content: str,
    source_filename: Optional[str] = None # <<< ACCEPTS THE FILENAME
) -> GenerationRecord:
    """
    Constructs a history record, generates its title, persists it,
    and returns a validated Pydantic model.
    """
    # Pass the optional filename to the corrected title generator
    title = _generate_title_from_settings(settings, source_filename)

    history_record_data = {
        "id": f"gen_{uuid.uuid4().hex[:16]}",
        "title": title,
        "tool_id": tool_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "settings_snapshot": json.dumps(settings),
        "generated_content": generated_content,
    }
    
    db.add_generation_record(history_record_data)
    
    api_ready_data = {
        "id": history_record_data["id"],
        "title": history_record_data["title"],
        "tool_id": ToolId(history_record_data["tool_id"]),
        "created_at": history_record_data["created_at"],
        "settings_snapshot": settings,
        "generated_content": history_record_data["generated_content"]
    }
    return GenerationRecord(**api_ready_data)


def delete_generation(db: DatabaseService, generation_id: str) -> bool:
    # ... (This function is unchanged)
    was_deleted = db.delete_generation_record(generation_id)
    return was_deleted


def get_history(
    db: DatabaseService,
    search: Optional[str] = None,
    tool_id: Optional[str] = None
) -> HistoryResponse:
    # ... (This function is unchanged)
    all_history: List[Dict] = db.get_all_generations()
    processed_records = []
    for record in all_history:
        try:
            record['settings_snapshot'] = json.loads(record.get('settings_snapshot', '{}'))
            processed_records.append(GenerationRecord(**record))
        except Exception as e:
            print(f"Skipping corrupted history record: {record.get('id')}. Error: {e}")
            continue
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