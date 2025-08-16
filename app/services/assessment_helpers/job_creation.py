# /app/services/assessment_helpers/job_creation.py (FINAL, CORRECTED VERSION)

import os
import uuid
import json
import datetime
from typing import List, Dict
from fastapi import UploadFile

from ..database_service import DatabaseService
from ...models import assessment_model

ASSESSMENT_UPLOADS_DIR = "assessment_uploads" # Use a relative path that's easier to manage

def _save_uploaded_files(job_id: str, answer_sheets: List[UploadFile]) -> List[Dict]:
    """
    Handles the file system operations for saving uploaded answer sheets.
    """
    # Ensure the root upload directory exists
    os.makedirs(ASSESSMENT_UPLOADS_DIR, exist_ok=True)
    
    job_dir = os.path.join(ASSESSMENT_UPLOADS_DIR, job_id)
    unassigned_dir = os.path.join(job_dir, 'unassigned')
    os.makedirs(unassigned_dir, exist_ok=True)
    
    answer_sheet_data = []
    for sheet in answer_sheets:
        # Use a simpler, safe filename
        safe_filename = f"answer_{uuid.uuid4().hex[:8]}_{os.path.basename(sheet.filename or 'untitled')}"
        path = os.path.join(unassigned_dir, safe_filename)
        with open(path, "wb") as buffer:
            # Read the file content from the UploadFile object
            content = sheet.file.read()
            buffer.write(content)
        answer_sheet_data.append({"path": path, "contentType": sheet.content_type})
    
    return answer_sheet_data

def _create_initial_job_records(db: DatabaseService, job_id: str, config: assessment_model.AssessmentConfig, answer_sheet_data: List[Dict]):
    """
    Specialist for creating the database records for a V1 assessment job.
    """
    job_record = {
        "id": job_id,
        "status": assessment_model.JobStatus.QUEUED.value,
        # --- [THE FIX IS HERE] ---
        "config": config.model_dump(), # Use model_dump() to get a dict
        "answer_sheet_paths": answer_sheet_data, # Pass the list of dicts directly
        # --- [END OF FIX] ---
        "created_at": datetime.datetime.utcnow().isoformat(),
        "ai_summary": ""
    }
    db.add_assessment_job(job_record)
    
    class_students = db.get_students_by_class_id(config.classId)
    for student in class_students:
        for question in config.questions:
            result_id = f"res_{uuid.uuid4().hex[:16]}"
            unique_token = f"tok_{uuid.uuid4().hex}"
            db.save_student_grade_result({
                "id": result_id, "job_id": job_id, "student_id": student.id,
                "question_id": question.id, "grade": None, "feedback": None,
                "extractedAnswer": None, "status": "pending_match",
                "report_token": unique_token, "answer_sheet_path": "", "content_type": ""
            })

def _create_initial_job_records_v2(db: DatabaseService, job_id: str, config: assessment_model.AssessmentConfigV2, answer_sheet_data: List[Dict]):
    """
    A new specialist that understands the hierarchical V2 config structure.
    """
    job_record = {
        "id": job_id,
        "status": assessment_model.JobStatus.QUEUED.value,
        # --- [THE FIX IS HERE] ---
        "config": config.model_dump(), # Use model_dump() to get a dict
        "answer_sheet_paths": answer_sheet_data, # Pass the list of dicts directly
        # --- [END OF FIX] ---
        "created_at": datetime.datetime.utcnow().isoformat(),
        "ai_summary": ""
    }
    db.add_assessment_job(job_record)
    
    class_students = db.get_students_by_class_id(config.classId)
    for student in class_students:
        for section in config.sections:
            for question in section.questions:
                result_id = f"res_{uuid.uuid4().hex[:16]}"
                unique_token = f"tok_{uuid.uuid4().hex}"
                db.save_student_grade_result({
                    "id": result_id, "job_id": job_id, "student_id": student.id,
                    "question_id": question.id, "grade": None, "feedback": None,
                    "extractedAnswer": None, "status": "pending_match",
                    "report_token": unique_token, "answer_sheet_path": "", "content_type": ""
                })