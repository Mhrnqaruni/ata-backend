# /app/routers/history_router.py

from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import Optional

# Import the Pydantic models that define our API contract
from ..models import history_model

# Import the services that contain our business logic
from ..services import history_service
from ..services.database_service import DatabaseService, get_db_service

router = APIRouter()

@router.post(
    "", # Maps to /api/history
    response_model=history_model.GenerationRecord,
    status_code=status.HTTP_201_CREATED, # <<< [CRITICAL FIX] Corrected from 21 to 201
    summary="Save a Generation"
)
def save_generation_record(
    payload: history_model.GenerationCreate,
    db: DatabaseService = Depends(get_db_service)
):
    """
    Endpoint to persist a new generation record.
    """
    try:
        # The service is now guaranteed to return a Pydantic model that matches the response_model
        return history_service.save_generation(
            db=db,
            tool_id=payload.tool_id.value,
            settings=payload.settings,
            generated_content=payload.generated_content
        )
    except Exception as e:
        print(f"ERROR saving generation record: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the generation record."
        )


@router.get(
    "", # Maps to /api/history
    response_model=history_model.HistoryResponse,
    summary="Get Generation History"
)
def get_user_history(
    search: Optional[str] = None,
    tool_id: Optional[str] = None,
    db: DatabaseService = Depends(get_db_service)
):
    """
    Endpoint to retrieve the user's AI generation history.
    """
    try:
        return history_service.get_history(db=db, search=search, tool_id=tool_id)
    except Exception as e:
        print(f"ERROR fetching generation history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the generation history."
        )

# --- [START] NEW DELETE ENDPOINT ---
@router.delete(
    "/{generation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Generation Record",
    description="Permanently deletes a single generation record from the user's history.",
    responses={404: {"description": "Generation record not found"}}
)
def delete_generation_record(
    generation_id: str,
    db: DatabaseService = Depends(get_db_service)
):
    """
    Endpoint to delete a specific generation record by its ID.
    """
    was_deleted = history_service.delete_generation(db=db, generation_id=generation_id)
    
    if not was_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation record with ID {generation_id} not found.",
        )
    
    # On success, return a 204 response with no content in the body.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
# --- [END] NEW DELETE ENDPOINT ---