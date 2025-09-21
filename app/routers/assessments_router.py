# /app/routers/assessments_router.py (SUPERVISOR-APPROVED FLAWLESS VERSION 2.0)

"""
This module defines all API endpoints related to assessment jobs.

Every endpoint is protected and requires user authentication. The router is
responsible for injecting the authenticated user's context into every call to
the business logic layer (the AssessmentService), ensuring all operations are
securely scoped to the correct user. Authorization checks are performed at the
earliest possible point within the router itself.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response, BackgroundTasks
from typing import List, Dict, Optional
import json

# --- Application-specific Imports ---
from ..services.assessment_service import AssessmentService, get_assessment_service
from ..models import assessment_model
from ..core.deps import get_current_active_user
from ..db.models.user_model import User as UserModel

router = APIRouter()


# --- V2 Endpoints (Now Secure with Router-Level Authorization) ---

@router.post(
    "/parse-document",
    summary="[V2] Parse uploaded document(s) to structure an assessment"
)
async def parse_assessment_document(
    question_file: UploadFile = File(..., description="The main exam document with questions."),
    answer_key_file: Optional[UploadFile] = File(None, description="An optional, separate answer key or rubric file."),
    class_id: str = Form(...),
    assessment_name: str = Form(...),
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    The endpoint for the V2 wizard's interactive step.
    This protected endpoint first verifies the user owns the target class
    before proceeding with the parsing operation.
    """
    # --- [ARCHITECTURAL REFINEMENT: AUTHORIZATION CHECK IN ROUTER] ---
    # Justification: This is the "Fail Fast" principle. We check for permission
    # at the earliest possible moment. If the user doesn't own the class, we
    # reject the request immediately without engaging the more resource-intensive
    # service logic (file processing, AI calls).
    target_class = assessment_svc.db.get_class_by_id(class_id=class_id, user_id=current_user.id)
    if not target_class:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Class with ID {class_id} not found or you do not have permission to access it."
        )
    # --- [END OF REFINEMENT] ---
    
    try:
        # The service call is now simpler as it's a pure data processor.
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
    config: str = Form(...),
    answer_sheets: List[UploadFile] = File(...),
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Creates a V2 assessment job and schedules it for background processing.
    This is a protected endpoint.
    """
    try:
        config_data = assessment_model.AssessmentConfigV2.model_validate_json(config)
        
        response = assessment_svc.create_new_assessment_job_v2(
            config=config_data,
            answer_sheets=answer_sheets,
            user_id=current_user.id
        )
        
        job_id = response.get("jobId")
        if job_id:
            background_tasks.add_task(assessment_svc.process_assessment_job, job_id, current_user.id)
            
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


# --- V1 & General Endpoints (Now Secure) ---

@router.get(
    "",
    response_model=assessment_model.AssessmentJobListResponse,
    summary="Get All Assessment Jobs"
)
def get_all_assessment_jobs(
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Retrieves a summary list of all assessment jobs for the authenticated user."""
    return assessment_svc.get_all_assessment_jobs_summary(user_id=current_user.id)


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
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Creates a V1 assessment job and schedules it for background processing."""
    try:
        config_data = assessment_model.AssessmentConfig.model_validate_json(config)
        response = assessment_svc.create_new_assessment_job(
            config=config_data,
            answer_sheets=answer_sheets,
            user_id=current_user.id
        )
        job_id = response.get("jobId")
        if job_id:
            background_tasks.add_task(assessment_svc.process_assessment_job, job_id, current_user.id)
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
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Saves a teacher's final grade/feedback for a single question."""
    try:
        assessment_svc.save_overrides(
            job_id=job_id,
            student_id=student_id,
            question_id=question_id,
            overrides=overrides,
            user_id=current_user.id
        )
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
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Retrieves the complete, aggregated results for a user-owned grading job."""
    full_results = assessment_svc.get_full_job_results(job_id=job_id, user_id=current_user.id)
    if full_results is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found or access denied.")
    return full_results


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an Assessment Job"
)
def delete_assessment_job(
    job_id: str,
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Permanently deletes a user-owned assessment job and all its associated data."""
    was_deleted = assessment_svc.delete_assessment_job(job_id=job_id, user_id=current_user.id)
    if not was_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found or access denied.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{job_id}/config",
    response_model=assessment_model.AssessmentConfigResponse,
    summary="Get Assessment Configuration for Cloning"
)
def get_assessment_config(
    job_id: str,
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Fetches a previous job's settings for the 'Clone' feature."""
    try:
        config_dict = assessment_svc.get_job_config(job_id=job_id, user_id=current_user.id)
        return assessment_model.AssessmentConfigResponse(**config_dict)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{job_id}/report/{student_id}", response_class=Response)
async def download_single_report(
    job_id: str,
    student_id: str,
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Generates and returns a single student's report as a .docx file."""
    try:
        report_bytes, filename = await assessment_svc.generate_single_report_docx(job_id, student_id, current_user.id)
        return Response(
            content=report_bytes, 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# --- NEW ENDPOINTS FOR MULTI-MODEL AI GRADING AND TEACHER REVIEW ---

@router.get(
    "/{job_id}/results/categorized",
    response_model=assessment_model.CategorizedResultsResponse,
    summary="Get Categorized Assessment Results (AI-graded vs Pending Review)"
)
def get_categorized_assessment_results(
    job_id: str,
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Retrieves assessment results categorized by AI-graded vs pending review status."""
    try:
        categorized_results = assessment_svc.get_categorized_job_results(job_id=job_id, user_id=current_user.id)
        if categorized_results is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found or access denied.")
        return categorized_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{job_id}/review/{student_id}",
    response_model=assessment_model.ReviewPageResponse,
    summary="Get Student Review Page Data"
)
def get_student_review_page(
    job_id: str,
    student_id: str,
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Retrieves data for the teacher review page for a specific student."""
    try:
        review_data = assessment_svc.get_student_review_data(
            job_id=job_id, 
            student_id=student_id, 
            user_id=current_user.id
        )
        if review_data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student review data not found or access denied.")
        return review_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{job_id}/review/{student_id}/{question_id}/pending",
    summary="Submit Teacher Review for Pending Question"
)
def submit_pending_review(
    job_id: str,
    student_id: str,
    question_id: str,
    review_request: assessment_model.PendingReviewRequest,
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Submits teacher's manual grade/feedback for a pending review question."""
    try:
        assessment_svc.submit_teacher_review(
            job_id=job_id,
            student_id=student_id, 
            question_id=question_id,
            grade=review_request.grade,
            feedback=review_request.feedback,
            user_id=current_user.id
        )
        return {"status": "success", "detail": "Teacher review submitted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{job_id}/review/{student_id}/{question_id}/override",
    summary="Save Teacher Override for AI-Graded Question"
)
def save_teacher_override(
    job_id: str,
    student_id: str,
    question_id: str,
    override_request: assessment_model.TeacherOverride,
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Saves teacher's override for an AI-graded question."""
    try:
        assessment_svc.save_teacher_override(
            job_id=job_id,
            student_id=student_id,
            question_id=question_id,
            override_data=override_request,
            user_id=current_user.id
        )
        return {"status": "success", "detail": "Teacher override saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{job_id}/regenerate-reports",
    summary="Regenerate Reports After Teacher Changes"
)
def regenerate_reports_after_changes(
    job_id: str,
    assessment_svc: AssessmentService = Depends(get_assessment_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Regenerates student reports after teacher makes manual changes."""
    try:
        assessment_svc.regenerate_reports_with_teacher_changes(
            job_id=job_id,
            user_id=current_user.id
        )
        return {"status": "success", "detail": "Reports regenerated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))