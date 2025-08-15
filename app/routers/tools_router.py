# /app/routers/tools_router.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
import json

from ..models import tool_model
from ..services import tool_service
from ..services.database_service import DatabaseService, get_db_service

router = APIRouter()

@router.post(
    "/generate/text",
    response_model=tool_model.ToolGenerationResponse,
    summary="Generate Content from Text or Library",
    description="The primary endpoint for text-based and library-based generation, accepting a JSON body."
)
async def generate_tool_content_from_text(
    request: tool_model.ToolGenerationRequest,
    db: DatabaseService = Depends(get_db_service)
):
    """Handles generation where the source is either direct text or library paths."""
    try:
        response_data = await tool_service.generate_content_for_tool(
            settings_payload=request.dict(),
            source_file=None,
            db=db
        )
        return response_data
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        print(f"ERROR during text generation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


@router.post(
    "/generate/upload",
    response_model=tool_model.ToolGenerationResponse,
    summary="Generate Content from an Uploaded File",
    description="The specialized endpoint for file-based generation using OCR."
)
async def generate_tool_content_from_upload(
    db: DatabaseService = Depends(get_db_service),
    settings: str = Form(...),
    source_file: UploadFile = File(...)
):
    """Handles generation where the source is an uploaded file."""
    try:
        settings_data = json.loads(settings)
        response_data = await tool_service.generate_content_for_tool(
            settings_payload=settings_data,
            source_file=source_file,
            db=db
        )
        return response_data
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The 'settings' form field is not valid JSON.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        print(f"ERROR during upload generation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")