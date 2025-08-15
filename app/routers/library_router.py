# /app/routers/library_router.py

from fastapi import APIRouter
from typing import List, Dict, Any

from ..services import library_service

router = APIRouter()

@router.get(
    "/tree",
    response_model=List[Dict[str, Any]],
    summary="Get Book Library Structure",
    description="Retrieves the complete, hierarchical structure of the book library as a nested JSON object. This is used to populate the cascading dropdowns in the UI.",
)
def get_library_structure():
    """
    Endpoint to retrieve the cached book library tree.
    The tree is scanned and cached on server startup for high performance.
    """
    return library_service.get_library_tree()