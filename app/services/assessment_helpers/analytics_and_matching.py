# /app/services/assessment_helpers/analytics_and_matching.py (CORRECTED)

import json
from typing import List, Dict, Union
import pandas as pd
import asyncio

from ...models import assessment_model
from .. import ocr_service
from ..database_service import DatabaseService

def get_validated_config_from_job(job_record: 'Assessment') -> Union[assessment_model.AssessmentConfig, assessment_model.AssessmentConfigV2]:
    """Tries to parse config as V2 first, falls back to V1 for backward compatibility."""
    # --- [THE FIX IS HERE] ---
    # The job_record is now a SQLAlchemy object. Its 'config' is a dictionary.
    config_str = json.dumps(job_record.config)
    # --- [END OF FIX] ---
    try:
        return assessment_model.AssessmentConfigV2.model_validate_json(config_str)
    except Exception:
        return assessment_model.AssessmentConfig.model_validate_json(config_str)

def normalize_config_to_v2(job_record: 'Assessment') -> assessment_model.AssessmentConfigV2:
    """Takes a job record and ALWAYS returns an AssessmentConfigV2 model."""
    config = get_validated_config_from_job(job_record)
    if isinstance(config, assessment_model.AssessmentConfigV2):
        return config
    
    v1_questions_as_v2 = [assessment_model.QuestionConfigV2(**q.model_dump()) for q in config.questions]
    v1_as_v2_section = assessment_model.SectionConfigV2(title="Main Section", questions=v1_questions_as_v2)
    
    return assessment_model.AssessmentConfigV2(
        assessmentName=config.assessmentName, classId=config.classId,
        scoringMethod=assessment_model.ScoringMethod.PER_QUESTION,
        includeImprovementTips=getattr(config, 'includeImprovementTips', False),
        sections=[v1_as_v2_section]
    )

def calculate_analytics(all_results: List['Result'], config: assessment_model.AssessmentConfigV2) -> Dict:
    """Calculates aggregate statistics for a completed assessment."""
    all_questions = [q for section in config.sections for q in section.questions]
    
    # --- [THE FIX IS HERE] ---
    # Convert list of SQLAlchemy Result objects to a list of dictionaries for pandas
    results_dicts = [r.__dict__ for r in all_results]
    df = pd.DataFrame(results_dicts)
    # --- [END OF FIX] ---

    if df.empty or 'grade' not in df.columns:
         return {"classAverage": 0, "medianGrade": 0, "gradeDistribution": {}, "performanceByQuestion": {}}
    
    # ... (rest of pandas logic is correct and remains unchanged) ...
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
        "classAverage": round(float(student_percentages.mean()), 2),
        "medianGrade": round(float(student_percentages.median()), 2),
        "gradeDistribution": grade_dist,
        "performanceByQuestion": {k: round(v, 2) for k, v in question_perf.items()}
    }

async def match_files_to_students(db: DatabaseService, job_id: str):
    """Matches uploaded answer sheets to students in the class roster using OCR."""
    job = db.get_assessment_job(job_id) # Returns an Assessment object
    config = get_validated_config_from_job(job)
    students = db.get_students_by_class_id(config.classId) # Returns a list of Student objects
    
    # --- [THE FIX IS HERE] ---
    # Use attribute access (s.name, s.id)
    student_map = {s.name.lower().strip(): s.id for s in students}
    # Use attribute access (job.answer_sheet_paths)
    unassigned_files = job.answer_sheet_paths
    # --- [END OF FIX] ---

    for file_info in unassigned_files:
        path, content_type = file_info['path'], file_info['contentType']
        try:
            with open(path, "rb") as f: file_bytes = f.read()
            ocr_text = await asyncio.to_thread(ocr_service.extract_text_from_file, file_bytes, content_type)
            for student_name, student_id in student_map.items():
                if student_name in ocr_text[:250].lower():
                    # This db method is part of the old CSV repo, it will need to be updated
                    # in the new SQL repo to work correctly. For now, the call is the same.
                    db.update_student_result_path(job_id, student_id, path, content_type)
                    break
        except Exception as e:
            print(f"ERROR matching file {path}: {e}")