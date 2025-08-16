# /ata-backend/app/models/history_model.py (CORRECTED AND MODERNIZED)

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List

# Import ToolId for strong validation, using our established relative import path
from .tool_model import ToolId

class GenerationRecord(BaseModel):
    """
    Defines the data contract for a single generation history record
    when it is retrieved from the database. All fields use snake_case.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    tool_id: ToolId
    created_at: str
    # The settings_snapshot is deserialized from a JSON string by the service
    settings_snapshot: Dict[str, Any] 
    generated_content: str

class HistoryResponse(BaseModel):
    """
    Defines the data contract for the GET /api/history response.
    """
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(populate_by_name=True)

    tool_id: ToolId
    settings: Dict[str, Any]
    generated_content: str