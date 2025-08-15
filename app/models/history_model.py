# /app/models/history_model.py

from pydantic import BaseModel, Field
from typing import Dict, Any, List

# Import ToolId for strong validation, using our established relative import path
from .tool_model import ToolId

class GenerationRecord(BaseModel):
    """
    Defines the data contract for a single generation history record
    when it is retrieved from the database. All fields use snake_case.
    """
    id: str
    title: str # <<< NEW FIELD
    tool_id: ToolId
    created_at: str
    # The settings_snapshot is deserialized from a JSON string by the service
    settings_snapshot: Dict[str, Any] 
    generated_content: str

class HistoryResponse(BaseModel):
    """
    Defines the data contract for the GET /api/history response.
    """
    results: List[GenerationRecord]
    total: int
    page: int
    hasNextPage: bool

class GenerationCreate(BaseModel):
    """
    Defines the contract for the data required to save a new generation.
    This model's payload does NOT include a title, as the title is
    generated on the server by the history_service.
    """
    tool_id: ToolId
    settings: Dict[str, Any]
    generated_content: str
    
    class Config:
        # Pydantic V2 configuration for aliasing if needed, but not required with consistent naming
        populate_by_name = True