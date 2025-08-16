# /app/routers/public_router.py (CORRECTED)

from fastapi import APIRouter, Depends, HTTPException, status
import json
from typing import Optional
from pydantic import BaseModel # <<< ADD THIS IMPORT

from ..services.database_service import DatabaseService, get_db_service
from ..models import assessment_model

router = APIRouter()

# --- FIX: Inherit from the imported BaseModel ---
class PublicReportResponse(BaseModel):
    studentName: str
    assessmentName: str
    questionText: str
    maxScore: int
    grade: int
    feedback: str

    class Config:
        from_attributes = True


@router.get(
    "/report/{report_token}",
    response_model=PublicReportResponse,
    summary="Get a Single Student Report via Secure Token",
    tags=["Public"]
)
def get_public_report_by_token(
    report_token: str,
    db: DatabaseService = Depends(get_db_service)
):
    # ... (The rest of this function is correct and does not need to be changed)
    result_record = db.get_result_by_token(report_token)
    
    if not result_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found. The link may be invalid or expired."
        )

    job_record = db.get_assessment_job(result_record.job_id)
    student_record = db.get_student_by_id(result_record.student_id)
    
    if not job_record or not student_record:
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not retrieve full report details."
        )
    
    config = job_record.config
    
    response_payload = {
        "studentName": student_record.name,
        "assessmentName": config.get("assessmentName"),
        "questionText": config.get("questionsText", "N/A"),
        "maxScore": config.get("maxScore", 10),
        "grade": result_record.grade,
        "feedback": result_record.feedback,
    }

    return response_payload