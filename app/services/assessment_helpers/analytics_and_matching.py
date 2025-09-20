
# /app/services/assessment_helpers/analytics_and_matching.py (FINAL, CORRECTED, SUPERVISOR-APPROVED VERSION)

"""
This module contains specialist helper functions for the middle and end stages
of the assessment grading pipeline.

It is called by the main `assessment_service` and is responsible for:
1. Automatically matching uploaded answer sheet files to students in a roster.
2. Calculating aggregate analytics and statistics for a completed job.
3. Normalizing and validating the job's configuration data.

The `match_files_to_students` function has been made "user-aware" to ensure
all its database operations are securely scoped.
"""

import json
from typing import List, Dict, Union
import pandas as pd
import asyncio

from ...models import assessment_model
from .. import ocr_service
from ..database_service import DatabaseService

# --- PURE UTILITY FUNCTIONS (Correct and Unchanged) ---
# These functions do not interact with the database directly. They operate on
# data that has already been securely fetched, so they do not require user context.

def get_validated_config_from_job(job_record: 'Assessment') -> Union[assessment_model.AssessmentConfig, assessment_model.AssessmentConfigV2]:
    """
    Tries to parse config as V2 first, falls back to V1 for backward compatibility.
    This version is hardened to handle both dict and str config types.
    """
    config_data = job_record.config
    
    if isinstance(config_data, str):
        try:
            config_data = json.loads(config_data)
        except json.JSONDecodeError:
            raise ValueError("Config is a malformed JSON string.")

    try:
        return assessment_model.AssessmentConfigV2.model_validate(config_data)
    except Exception:
        return assessment_model.AssessmentConfig.model_validate(config_data)

def normalize_config_to_v2(job_record: 'Assessment') -> assessment_model.AssessmentConfigV2:
    """Takes a job record and ALWAYS returns an AssessmentConfigV2 model."""
    config = get_validated_config_from_job(job_record)
    
    if isinstance(config, assessment_model.AssessmentConfigV2):
        return config
    
    # This logic correctly upgrades a V1 config to the V2 structure.
    v1_questions_as_v2 = [assessment_model.QuestionConfigV2(**q.model_dump()) for q in config.questions]
    
    v1_as_v2_section = assessment_model.SectionConfigV2(
        title="Main Section",
        questions=v1_questions_as_v2
    )
    
    return assessment_model.AssessmentConfigV2(
        assessmentName=config.assessmentName,
        classId=config.classId,
        scoringMethod=assessment_model.ScoringMethod.PER_QUESTION,
        includeImprovementTips=getattr(config, 'includeImprovementTips', False),
        sections=[v1_as_v2_section]
    )

def calculate_analytics(all_results: List['Result'], config: assessment_model.AssessmentConfigV2) -> Dict:
    """Calculates aggregate statistics for a completed assessment."""
    all_questions = [q for section in config.sections for q in section.questions]
    
    results_dicts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in all_results]
    df = pd.DataFrame(results_dicts)

    # Robust checks for empty or invalid data.
    if df.empty or 'grade' not in df.columns:
         return {"classAverage": 0, "medianGrade": 0, "gradeDistribution": {}, "performanceByQuestion": {}}
    
    df['grade'] = pd.to_numeric(df['grade'], errors='coerce')
    df.dropna(subset=['grade'], inplace=True)
    if df.empty: return {"classAverage": 0, "medianGrade": 0, "gradeDistribution": {}, "performanceByQuestion": {}}
    
    total_max_score = sum(q.maxScore for q in all_questions if q.maxScore is not None)
    if total_max_score == 0: return {"classAverage": 0, "medianGrade": 0, "gradeDistribution": {}, "performanceByQuestion": {}}
    
    student_scores = df.groupby('student_id')['grade'].sum()
    student_percentages = (student_scores / total_max_score) * 100

    question_perf = {}
    for q in all_questions:
        q_grades = df[df['question_id'] == q.id]['grade'].dropna().tolist()
        avg_score = (sum(q_grades) / len(q_grades)) if q_grades else 0
        question_perf[q.id] = (avg_score / q.maxScore) * 100 if q.maxScore and q.maxScore > 0 else 0
    
    bins = [0, 59.99, 69.99, 79.99, 89.99, 101]
    labels = ["F (0-59)", "D (60-69)", "C (70-79)", "B (80-89)", "A (90-100)"]
    grade_dist = pd.cut(student_percentages, bins=bins, labels=labels, right=False).value_counts().sort_index().to_dict()
    
    return {
        "classAverage": round(float(student_percentages.mean()), 2) if not student_percentages.empty else 0,
        "medianGrade": round(float(student_percentages.median()), 2) if not student_percentages.empty else 0,
        "gradeDistribution": grade_dist,
        "performanceByQuestion": {k: round(v, 2) for k, v in question_perf.items()}
    }

# --- DATABASE-INTERACTIVE HELPER (Corrected and Secure) ---
async def match_files_to_students(
    db: DatabaseService, 
    job_id: str,
    user_id: str
):
    """
    Matches uploaded answer sheets to students in the class roster using OCR.
    This function is now fully user-aware.
    """
    # 1. Securely fetch the parent assessment job to verify ownership.
    job = db.get_assessment_job(job_id=job_id, user_id=user_id)
    if not job:
        print(f"ERROR: Job {job_id} not found or access denied for user {user_id} during file matching.")
        return

    config = get_validated_config_from_job(job)

    # 2. Securely fetch the student roster for the associated class.
    students = db.get_students_by_class_id(class_id=config.classId, user_id=user_id)
    
    student_map = {s.name.lower().strip(): s.id for s in students}
    
    # Robustly handle the unassigned_files JSON data.
    unassigned_files_data = job.answer_sheet_paths
    if isinstance(unassigned_files_data, str):
        unassigned_files = json.loads(unassigned_files_data)
    else:
        unassigned_files = unassigned_files_data

    if not isinstance(unassigned_files, list):
        print(f"WARNING: answer_sheet_paths for job {job_id} is not a list. Skipping matching.")
        return

    # 3. Process each unassigned file.
    for file_info in unassigned_files:
        path = file_info.get('path')
        content_type = file_info.get('contentType')
        if not path or not content_type:
            continue

        try:
            with open(path, "rb") as f:
                file_bytes = f.read()
            # The ocr_service call is CPU-bound and is correctly run in a thread.
            ocr_text = await asyncio.to_thread(ocr_service.extract_text_from_file, file_bytes, content_type)
            
            # Simple matching logic.
            for student_name, student_id in student_map.items():
                if student_name in ocr_text[:250].lower():
                    # --- [THE DEFINITIVE FIX IS HERE] ---
                    # The call to `update_student_result_path` now correctly includes
                    # the `user_id`, satisfying the method's signature and completing
                    # the security context propagation. This resolves the TypeError.
                    db.update_student_result_path(
                        job_id=job_id, 
                        student_id=student_id, 
                        path=path, 
                        content_type=content_type, 
                        user_id=user_id
                    )
                    # --- [END OF FIX] ---
                    break 
        except FileNotFoundError:
            print(f"ERROR: File not found during matching for job {job_id}: {path}")
        except Exception as e:
            print(f"ERROR matching file {path} for job {job_id}: {e}")