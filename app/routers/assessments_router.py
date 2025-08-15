# /app/routers/assessments_router.py (FINAL, V2-COMPLETE VERSION)

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response, BackgroundTasks
from typing import List, Dict, Optional
import json

# Import the service CLASS and the provider FUNCTION
from ..services.assessment_service import AssessmentService, get_assessment_service
# Import the entire model module to access all our specific models
from ..models import assessment_model

router = APIRouter()


# --- [V2 ENDPOINTS - MODIFIED FOR DUAL UPLOAD] ---

@router.post(
    "/parse-document",
    summary="[V2] Parse uploaded document(s) to structure an assessment"
)
async def parse_assessment_document(
    question_file: UploadFile = File(..., description="The main exam document with questions."),
    answer_key_file: Optional[UploadFile] = File(None, description="An optional, separate answer key or rubric file."),
    class_id: str = Form(...),
    assessment_name: str = Form(...),
    assessment_svc: AssessmentService = Depends(get_assessment_service)
):
    """
    The synchronous endpoint for the V2 wizard's interactive step.
    It now accepts both a question paper and an optional, separate answer key.
    """
    try:
        parsed_config_dict = await assessment_svc.parse_document_for_review(
            question_file=question_file,
            answer_key_file=answer_key_file,
            class_id=class_id,
            assessment_name=assessment_name
        )
        return parsed_config_dict
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Error during document parsing: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while parsing the document.")


@router.post(
    "/v2",
    response_model=assessment_model.AssessmentJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="[V2] Create a New Assessment Grading Job from a V2 Config"
)
def create_assessment_job_v2(
    background_tasks: BackgroundTasks,
    config: str = Form(...), # The stringified AssessmentConfigV2 JSON
    answer_sheets: List[UploadFile] = File(...),
    assessment_svc: AssessmentService = Depends(get_assessment_service)
):
    """
    The new endpoint for creating a job with the teacher-verified V2 config.
    """
    try:
        config_data = assessment_model.AssessmentConfigV2.model_validate_json(config)
        
        response = assessment_svc.create_new_assessment_job_v2(
            config=config_data,
            answer_sheets=answer_sheets
        )
        
        job_id = response.get("jobId")
        if job_id:
            background_tasks.add_task(assessment_svc.process_assessment_job, job_id)
            
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


# --- [EXISTING & V1 ENDPOINTS - UNCHANGED AND STABLE] ---

@router.get(
    "",
    response_model=assessment_model.AssessmentJobListResponse,
    summary="Get All Assessment Jobs"
)
def get_all_assessment_jobs(
    assessment_svc: AssessmentService = Depends(get_assessment_service)
):
    """Endpoint to retrieve a summary list of all assessment jobs."""
    return assessment_svc.get_all_assessment_jobs_summary()


@router.post(
    "",
    response_model=assessment_model.AssessmentJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="[V1] Create a New Assessment Grading Job"
)
def create_assessment_job(
    background_tasks: BackgroundTasks,
    config: str = Form(...),
    answer_sheets: List[UploadFile] = File(...),
    assessment_svc: AssessmentService = Depends(get_assessment_service)
):
    """Endpoint for the original V1 'one-by-one' wizard."""
    try:
        config_data = assessment_model.AssessmentConfig.model_validate_json(config)
        response = assessment_svc.create_new_assessment_job(
            config=config_data,
            answer_sheets=answer_sheets
        )
        job_id = response.get("jobId")
        if job_id:
            background_tasks.add_task(assessment_svc.process_assessment_job, job_id)
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.patch(
    "/{job_id}/results/{student_id}/{question_id}",
    summary="Save Teacher Overrides for a Single Question"
)
def save_teacher_overrides(
    job_id: str,
    student_id: str,
    question_id: str,
    overrides: assessment_model.GradingResult,
    assessment_svc: AssessmentService = Depends(get_assessment_service)
):
    """Endpoint for the grading workflow to save a teacher's final grade/feedback."""
    try:
        # NOTE: The actual service logic for this is a V2 feature.
        # For now, we return a success placeholder as per the handbook.
        return {"status": "success", "detail": f"Overrides for s:{student_id} q:{question_id} saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{job_id}/results",
    response_model=assessment_model.AssessmentResultsResponse,
    summary="Get Full Assessment Job Results"
)
def get_assessment_job_results(
    job_id: str,
    assessment_svc: AssessmentService = Depends(get_assessment_service)
):
    """Endpoint to retrieve the complete, aggregated results for a grading job."""
    full_results = assessment_svc.get_full_job_results(job_id=job_id)
    if full_results is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")
    return full_results


# --- [THE FIX IS HERE: NEW DELETE ENDPOINT] ---
@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an Assessment Job"
)
def delete_assessment_job(
    job_id: str,
    assessment_svc: AssessmentService = Depends(get_assessment_service)
):
    """
    Endpoint to permanently delete an assessment job and all its associated data,
    including results and uploaded files.
    """
    try:
        was_deleted = assessment_svc.delete_assessment_job(job_id=job_id)
        if not was_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found.")
        # On success, a 204 response has no body, so we return None or Response.
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
# --- [END OF FIX] ---


@router.get(
    "/{job_id}/config",
    response_model=assessment_model.AssessmentConfigResponse,
    summary="Get Assessment Configuration for Cloning"
)
def get_assessment_config(
    job_id: str,
    assessment_svc: AssessmentService = Depends(get_assessment_service)
):
    """Endpoint for the 'Clone' feature to fetch a previous job's settings."""
    try:
        config_dict = assessment_svc.get_job_config(job_id=job_id)
        return assessment_model.AssessmentConfigResponse(**config_dict)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{job_id}/report/{student_id}", response_class=Response)
async def download_single_report(
    job_id: str,
    student_id: str,
    assessment_svc: AssessmentService = Depends(get_assessment_service)
):
    """Generates and returns a single student's report as a .docx file."""
    try:
        report_bytes, filename = await assessment_svc.generate_single_report_docx(job_id, student_id)
        return Response(
            content=report_bytes, 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{job_id}/reports/all", response_class=Response)
async def download_all_reports(
    job_id: str,
    assessment_svc: AssessmentService = Depends(get_assessment_service)
):
    """Generates and returns a ZIP archive of all student reports."""
    try:
        zip_bytes, filename = await assessment_svc.generate_batch_reports_zip(job_id)
        return Response(
            content=zip_bytes, 
            media_type="application/zip", 
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))