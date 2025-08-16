# /app/services/assessment_helpers/data_assembly.py (CORRECTED)

import json
from typing import List, Dict, Union
import pandas as pd

from ...models import assessment_model

def _get_validated_config_from_job(job_record: 'Assessment') -> Union[assessment_model.AssessmentConfig, assessment_model.AssessmentConfigV2]:
    """A specialist helper that robustly parses a job's config JSON."""
    # --- [THE FIX IS HERE] ---
    config_str = json.dumps(job_record.config)
    # --- [END OF FIX] ---
    try:
        return assessment_model.AssessmentConfigV2.model_validate_json(config_str)
    except Exception:
        return assessment_model.AssessmentConfig.model_validate_json(config_str)

def _safe_float_convert(value):
    if value is None or str(value).strip() == '': return None
    try: return float(value)
    except (ValueError, TypeError): return None

def _assemble_job_summaries(all_jobs: List['Assessment'], all_results: List['Result'], all_classes: Dict) -> List[Dict]:
    """Specialist for assembling the dashboard summary list."""
    summaries = []
    # --- [THE FIX IS HERE] ---
    # Convert results to a DataFrame for efficient processing
    results_df = pd.DataFrame([r.__dict__ for r in all_results]) if all_results else pd.DataFrame()
    # --- [END OF FIX] ---

    for job in all_jobs:
        try:
            config = _get_validated_config_from_job(job)
            class_id = config.classId
            
            job_results_df = pd.DataFrame()
            if not results_df.empty:
                job_results_df = results_df[results_df['job_id'] == job.id]
            
            total_students = len(job_results_df['student_id'].unique())
            processed_students = len(job_results_df[~job_results_df['status'].isin(['pending_match', 'matched', 'pending'])]['student_id'].unique())
            
            progress = {"total": total_students, "processed": processed_students}
            
            summary = {
                "id": job.id, "assessmentName": config.assessmentName,
                "className": all_classes.get(class_id, "Unknown Class"),
                "createdAt": job.created_at.isoformat(), "status": job.status,
                "progress": progress
            }
            summaries.append(summary)
        except Exception as e:
            print(f"Error parsing job summary for {getattr(job, 'id', 'N/A')}, skipping: {e}")
    
    return summaries

def _build_results_dictionary(class_students: List['Student'], config: assessment_model.AssessmentConfigV2, all_results_for_job: List['Result']) -> Dict:
    """Specialist for assembling the complex, nested results dictionary."""
    # --- [THE FIX IS HERE] ---
    # Create a map from the list of Result objects for fast lookup
    results_map = {}
    for res in all_results_for_job:
        s_id = res.student_id; q_id = res.question_id
        if s_id not in results_map: results_map[s_id] = {}
        results_map[s_id][q_id] = res
    # --- [END OF FIX] ---

    final_results_dict = {}
    all_questions = [q for section in config.sections for q in section.questions]

    for s in class_students:
        s_id = s.id
        final_results_dict[s_id] = {}
        for q in all_questions:
            q_id = q.id
            # --- [THE FIX IS HERE] ---
            # Get the result object from the map
            result_obj = results_map.get(s_id, {}).get(q_id)
            # Access data using attributes
            final_grade = _safe_float_convert(getattr(result_obj, 'grade', None))
            final_results_dict[s_id][q_id] = {
                "grade": final_grade,
                "feedback": getattr(result_obj, 'feedback', None),
                "extractedAnswer": getattr(result_obj, 'extractedAnswer', None),
                "status": getattr(result_obj, 'status', 'pending')
            }
            # --- [END OF FIX] ---
    return final_results_dict