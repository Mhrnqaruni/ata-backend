# /app/routers/public_router.py (CORRECTED)

from fastapi import APIRouter, Depends, HTTPException, status
import json
from typing import Optional

# We need the DatabaseService class for type hinting
from ..services.database_service import DatabaseService, get_db_service
from ..models import assessment_model

router = APIRouter()

# The Pydantic model for the response is correct.
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
    """
    An unauthenticated endpoint to retrieve the data for a single student's
    graded report using a unique, unguessable token.
    """
    # result_record is now a SQLAlchemy Result object
    result_record = db.get_result_by_token(report_token)
    
    if not result_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    # --- [THE FIX IS HERE] ---
    # Use attribute access (.job_id, .student_id) on the SQLAlchemy objects
    job_record = db.get_assessment_job(result_record.job_id)
    student_record = db.get_student_by_id(result_record.student_id)
    # --- [END OF FIX] ---
    
    if not job_record or not student_record:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Could not retrieve full report details.")
    
    # The config from the DB is now a dictionary, not a string. No need for json.loads.
    config = job_record.config
    
    # --- [THE FIX IS HERE] ---
    # Assemble the payload using attribute access
    response_payload = {
        "studentName": student_record.name,
        "assessmentName": config.get("assessmentName"), # Config is still a dict
        "questionText": config.get("questionsText", "N/A"),
        "maxScore": config.get("maxScore", 10),
        "grade": result_record.grade,
        "feedback": result_record.feedback,
    }
    # --- [END OF FIX] ---

    return response_payload