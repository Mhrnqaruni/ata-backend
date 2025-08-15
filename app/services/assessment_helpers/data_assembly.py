# /app/services/assessment_helpers/data_assembly.py (CORRECTED AND V2-AWARE)

import json
from typing import List, Dict, Union
import pandas as pd

from ...models import assessment_model

# --- [NEW HELPER FOR VERSION-AWARE PARSING] ---
def _get_validated_config_from_job(job_record: Dict) -> Union[assessment_model.AssessmentConfig, assessment_model.AssessmentConfigV2]:
    """
    A specialist helper that robustly parses a job's config JSON.
    It tries to parse as V2 first, and falls back to V1 for backward compatibility.
    """
    try:
        # Attempt to parse as the new, richer V2 model first.
        return assessment_model.AssessmentConfigV2.model_validate_json(job_record["config"])
    except Exception:
        # If that fails, it must be an old V1 job.
        return assessment_model.AssessmentConfig.model_validate_json(job_record["config"])

# --- [EXISTING HELPERS - UNCHANGED] ---
def _safe_float_convert(value):
    if value is None or str(value).strip() == '': return None
    try: return float(value)
    except (ValueError, TypeError): return None

# --- [REFACTORED SUMMARY ASSEMBLY] ---
def _assemble_job_summaries(all_jobs: List[Dict], all_results: List[Dict], all_classes: Dict) -> List[Dict]:
    """
    Specialist for assembling the dashboard summary list.
    REFACTORED: This function is now version-aware and can correctly process
    summaries for both V1 and V2 assessment jobs.
    """
    summaries = []
    for job in all_jobs:
        try:
            # --- [THE FIX IS HERE] ---
            # Use our new version-aware helper to parse the config.
            # This will correctly handle both old and new job structures.
            config = _get_validated_config_from_job(job)
            # --- [END OF FIX] ---

            # The rest of the logic can now safely access common fields like
            # .classId and .assessmentName which exist on both models.
            class_id = config.classId
            
            job_results = [r for r in all_results if r['job_id'] == job['id']]
            student_ids_in_job = {r['student_id'] for r in job_results}
            total_students = len(student_ids_in_job)
            
            processed_students_set = {r['student_id'] for r in job_results if r.get('status') not in ['pending_match', 'matched', 'pending']}
            processed_students = len(processed_students_set)
            
            progress = {"total": total_students, "processed": processed_students}
            
            summary = {
                "id": job["id"], "assessmentName": config.assessmentName,
                "className": all_classes.get(class_id, "Unknown Class"),
                "createdAt": job.get("created_at", ""), "status": job["status"],
                "progress": progress
            }
            summaries.append(summary)
        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"Error parsing job summary for {job.get('id', 'N/A')}, skipping: {e}")
    
    return summaries

# --- [UNCHANGED RESULTS DICTIONARY BUILDER] ---
def _build_results_dictionary(class_students: List[Dict], config: assessment_model.AssessmentConfigV2, all_results_for_job: List[Dict]) -> Dict:
    """
    Specialist for assembling the complex, nested results dictionary.
    NOTE: This function already correctly expects a V2 config, thanks to our
    normalization logic in the main assessment_service. No changes are needed here.
    """
    results_map = {}
    for res in all_results_for_job:
        s_id = res['student_id']; q_id = res['question_id']
        if s_id not in results_map: results_map[s_id] = {}
        results_map[s_id][q_id] = res

    final_results_dict = {}
    all_questions = [q for section in config.sections for q in section.questions]

    for s in class_students:
        s_id = s['id']
        final_results_dict[s_id] = {}
        for q in all_questions:
            q_id = q.id
            result_data = results_map.get(s_id, {}).get(q_id, {})
            final_grade = _safe_float_convert(result_data.get('grade'))
            final_results_dict[s_id][q_id] = {
                "grade": final_grade,
                "feedback": result_data.get('feedback'),
                "extractedAnswer": result_data.get('extractedAnswer'),
                "status": result_data.get('status', 'pending')
            }
    return final_results_dict