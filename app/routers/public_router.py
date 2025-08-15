# /app/routers/public_router.py

from fastapi import APIRouter, Depends, HTTPException, status
import json
from typing import Optional

from ..services import database_service
from ..models import assessment_model

router = APIRouter()

# --- FIX: Define and use a specific Pydantic model for the public response ---
# This acts as a security filter, ensuring only these fields are ever exposed.
class PublicReportResponse(assessment_model.BaseModel):
    studentName: str
    assessmentName: str
    questionText: str
    maxScore: int
    grade: int
    feedback: str


@router.get(
    "/report/{report_token}",
    response_model=PublicReportResponse, # Use the specific, secure model
    summary="Get a Single Student Report via Secure Token",
    tags=["Public"]
)
def get_public_report_by_token(
    report_token: str,
    db: database_service.DatabaseService = Depends(database_service.get_db_service)
):
    """
    An unauthenticated endpoint to retrieve the data for a single student's
    graded report using a unique, unguessable token.
    """
    result_record = db.get_result_by_token(report_token)
    
    if not result_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found. The link may be invalid or expired."
        )

    job_record = db.get_assessment_job(result_record['job_id'])
    student_record = db.get_student_by_id(result_record['student_id'])
    
    if not job_record or not student_record:
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not retrieve full report details."
        )
    
    config = json.loads(job_record["config"])
    
    # Assemble the payload. The response_model will validate this structure.
    response_payload = {
        "studentName": student_record["name"],
        "assessmentName": config["assessmentName"],
        "questionText": config.get("questionsText", "N/A"),
        "maxScore": config.get("maxScore", 10),
        "grade": result_record["grade"],
        "feedback": result_record["feedback"],
    }

    return response_payload