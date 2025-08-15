# /app/services/assessment_service.py (FINAL, WITH REPORT GENERATION AND DELETE LOGIC)

import uuid, json, os, datetime, asyncio, shutil
from fastapi import UploadFile, Depends
from typing import List, Dict, Optional, Union, Tuple
import pandas as pd

# Import all services and helpers
from . import ocr_service, gemini_service, prompt_library, library_service, report_service, zip_service
from .database_service import DatabaseService, get_db_service
from ..models import assessment_model
from .assessment_helpers import job_creation, grading_pipeline, data_assembly, document_parser, analytics_and_matching

# This constant needs to be defined for the delete logic to work
ASSESSMENT_UPLOADS_DIR = "assessment_uploads" 

class AssessmentService:
    def __init__(self, db: DatabaseService = Depends(get_db_service)):
        self.db = db

    # --- V2 WORKFLOW & JOB CREATION (Unchanged and Stable) ---
    async def parse_document_for_review(self, question_file: UploadFile, answer_key_file: Optional[UploadFile], class_id: str, assessment_name: str) -> Dict:
        return await document_parser.parse_document_to_config(question_file, answer_key_file, class_id, assessment_name)

    def create_new_assessment_job_v2(self, config: assessment_model.AssessmentConfigV2, answer_sheets: List[UploadFile]) -> Dict:
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        answer_sheet_data = job_creation._save_uploaded_files(job_id, answer_sheets)
        job_creation._create_initial_job_records_v2(self.db, job_id, config, answer_sheet_data)
        return { "jobId": job_id, "status": assessment_model.JobStatus.QUEUED, "message": "Assessment job created." }
        
    def create_new_assessment_job(self, config: assessment_model.AssessmentConfig, answer_sheets: List[UploadFile]) -> Dict:
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        answer_sheet_data = job_creation._save_uploaded_files(job_id, answer_sheets)
        job_creation._create_initial_job_records(self.db, job_id, config, answer_sheet_data)
        return { "jobId": job_id, "status": assessment_model.JobStatus.QUEUED, "message": "Assessment job created." }

    # --- [NEW DELETE METHOD] ---
    def delete_assessment_job(self, job_id: str) -> bool:
        """
        Orchestrates the cascading delete of an assessment job.
        This is a destructive operation.
        """
        # 1. Verify the job exists.
        job_record = self.db.get_assessment_job(job_id)
        if not job_record:
            return False

        # 2. Delete all associated results from the results "table".
        self.db.delete_results_by_job_id(job_id)

        # 3. Delete the main job record from the assessments "table".
        self.db.delete_assessment_job(job_id)

        # 4. Delete the entire job directory from the file system.
        job_dir = os.path.join(ASSESSMENT_UPLOADS_DIR, job_id)
        if os.path.isdir(job_dir):
            shutil.rmtree(job_dir)
        
        return True
    # --- [END OF NEW METHOD] ---

    # --- MAIN PROCESSING & GRADING PIPELINE (Unchanged and Stable) ---
    async def process_assessment_job(self, job_id: str):
        try:
            self.db.update_job_status(job_id, assessment_model.JobStatus.PROCESSING.value)
            await analytics_and_matching.match_files_to_students(self.db, job_id)
            job_record = self.db.get_assessment_job(job_id)
            config = analytics_and_matching.get_validated_config_from_job(job_record)
            students_to_grade = self.db.get_students_with_paths(job_id)
            grading_tasks = [self._grade_entire_submission_for_student(job_id, student['student_id'], student['answer_sheet_path'], student['content_type'], config) for student in students_to_grade]
            await asyncio.gather(*grading_tasks)
            self.db.update_job_status(job_id, assessment_model.JobStatus.SUMMARIZING.value)
            await self._generate_analytic_summary(job_id)
            self.db.update_job_status(job_id, assessment_model.JobStatus.COMPLETED.value)
        except Exception as e:
            print(f"CRITICAL ERROR processing job {job_id}: {e}")
            self.db.update_job_status(job_id, assessment_model.JobStatus.FAILED.value)

    async def _grade_entire_submission_for_student(self, job_id: str, student_id: str, answer_sheet_path: str, content_type: str, config: Union[assessment_model.AssessmentConfig, assessment_model.AssessmentConfigV2]):
        
        # This helper logic is now more complex as it handles different config versions.
        all_questions = []
        is_v2_config = isinstance(config, assessment_model.AssessmentConfigV2)
        if is_v2_config:
            for section in config.sections: all_questions.extend(section.questions)
        else:
            all_questions = config.questions
        
        try:
            for q in all_questions: self.db.update_result_status(job_id, student_id, q.id, "processing")
            
            image_list = grading_pipeline._prepare_images_from_answersheet(answer_sheet_path, content_type)
            
            # --- [NEW LOGIC: DYNAMICALLY BUILD PROMPT CONTEXT] ---
            # We now build a dynamic context for the AI based on the teacher's choices.
            
            # 1. Prepare the questions JSON (unchanged)
            questions_json_str = json.dumps([q.model_dump() for q in all_questions], indent=2)

            # 2. Prepare the answer key context
            answer_key_context = "No answer key was provided. Grade based on general knowledge."
            if is_v2_config:
                if config.gradingMode == "library" and config.librarySource:
                    # If grading from the library, fetch the chapter content.
                    try:
                        chapter_content = library_service.get_chapter_content(config.librarySource)
                        answer_key_context = f"The following text from the curriculum library is the definitive answer key:\n---\n{chapter_content}\n---"
                    except Exception as e:
                        print(f"Could not load library source {config.librarySource}: {e}")
                        answer_key_context = "ERROR: The specified library source could not be loaded. Grade based on general knowledge."
                elif config.gradingMode == "answer_key_provided":
                    answer_key_context = "The correct answers are included within each question object in the JSON below. Use these as the ground truth."

            # 3. Format the final prompt
            prompt = prompt_library.STUDENT_CENTRIC_GRADING_PROMPT.format(
                questions_json=questions_json_str,
                answer_key_context=answer_key_context # Pass the new context to the prompt
            )
            # --- [END OF NEW LOGIC] ---

            ai_response_str = await grading_pipeline._invoke_grading_ai(prompt, image_list)
            parsed_results = grading_pipeline._parse_ai_grading_response(ai_response_str)
            grading_pipeline._save_grading_results_to_db(self.db, job_id, student_id, parsed_results)

        except Exception as e:
            print(f"ERROR grading submission for student {student_id}: {e}")
            for q in all_questions: self.db.update_result_status(job_id, student_id, q.id, "failed")

    # --- DATA FETCHING & ASSEMBLY (Unchanged and Stable) ---
    def get_all_assessment_jobs_summary(self) -> Dict:
        # ... (This method is complete and correct)
        all_jobs = self.db.get_all_assessment_jobs()
        all_results = self.db.get_all_results()
        all_classes = {c['id']: c['name'] for c in self.db.get_all_classes()}
        summaries = data_assembly._assemble_job_summaries(all_jobs, all_results, all_classes)
        return {"assessments": summaries}

    def get_full_job_results(self, job_id: str) -> Optional[Dict]:
        # ... (This method is complete and correct)
        job_record = self.db.get_assessment_job(job_id)
        if not job_record: return None
        config_v2 = analytics_and_matching.normalize_config_to_v2(job_record)
        class_students = self.db.get_students_by_class_id(config_v2.classId)
        all_results_for_job = self.db.get_all_results_for_job(job_id)
        final_results_dict = data_assembly._build_results_dictionary(class_students, config_v2, all_results_for_job)
        students_list = [{"id": s['id'], "name": s['name'], "answerSheetPath": self.db.get_student_result_path(job_id, s['id']) or ""} for s in class_students]
        analytics_data = None
        if job_record['status'] == assessment_model.JobStatus.COMPLETED.value:
            analytics_data = analytics_and_matching.calculate_analytics(all_results_for_job, config_v2)
        return {
            "jobId": job_record["id"], "assessmentName": config_v2.assessmentName,
            "status": job_record["status"], "config": config_v2,
            "students": students_list, "results": final_results_dict,
            "analytics": analytics_data, "aiSummary": job_record.get("ai_summary")
        }

    # --- [THE FIX IS HERE: IMPLEMENTING THE REPORTING LOGIC] ---
    async def generate_single_report_docx(self, job_id: str, student_id: str) -> Tuple[bytes, str]:
        """
        Orchestrates the generation of a single student's .docx report.
        """
        full_job_data = self.get_full_job_results(job_id)
        if not full_job_data:
            raise ValueError(f"Job with ID {job_id} not found.")

        student_details = next((s for s in full_job_data['students'] if s['id'] == student_id), None)
        if not student_details:
            raise ValueError(f"Student with ID {student_id} not found in job {job_id}.")

        config = full_job_data['config']
        all_questions = [q for section in config.sections for q in section.questions]
        
        student_results = full_job_data['results'].get(student_id, {})
        
        total_score = 0
        total_max_score = 0
        question_breakdown = []

        for q in all_questions:
            result = student_results.get(q.id, {})
            grade = result.get('grade', 0)
            total_score += grade if grade is not None else 0
            total_max_score += q.maxScore if q.maxScore is not None else 0
            question_breakdown.append({
                "text": q.text,
                "grade": f"{grade or 'N/A'} / {q.maxScore or 'N/A'}",
                "feedback": result.get('feedback', 'No feedback available.')
            })
        
        # This calculation is for a percentage, which we might use elsewhere, but is NOT the final grade sum.
        # final_percentage = round((total_score / total_max_score) * 100, 1) if total_max_score > 0 else 0
        
        class_info = self.db.get_class_by_id(config.classId)
        class_name = class_info['name'] if class_info else "Unknown Class"

        report_data = {
            "studentName": student_details['name'],
            # The fix: Pass the 'total_score' (the sum), not the 'final_percentage'.
            "finalGrade": total_score,
            # We can also add the max score for context in the report.
            "totalMaxScore": total_max_score,
            "questions": question_breakdown,
            "assessmentName": config.assessmentName,
            "className": class_name
        }

        report_bytes = await asyncio.to_thread(report_service.create_word_report, report_data)
        
        safe_student_name = "".join(c for c in student_details['name'] if c.isalnum() or c in " _-").rstrip()
        filename = f"Report_{config.assessmentName}_{safe_student_name}.docx"
        
        return report_bytes, filename
    
    async def generate_batch_reports_zip(self, job_id: str) -> Tuple[bytes, str]:
        # This method would follow a similar pattern, looping through all students.
        # For now, it remains a placeholder.
        pass
    # --- [END OF FIX] ---

    # --- OTHER HELPERS & METHODS (Unchanged and Stable) ---
    def get_job_config(self, job_id: str) -> Dict:
        # ... (This method is complete and correct)
        job = self.db.get_assessment_job(job_id)
        if not job: raise ValueError("Assessment job not found")
        v2_config = analytics_and_matching.normalize_config_to_v2(job)
        v1_questions = [q for s in v2_config.sections for q in s.questions]
        return {"assessmentName": v2_config.assessmentName, "questions": [q.model_dump() for q in v1_questions], "includeImprovementTips": v2_config.includeImprovementTips}
        
    async def _generate_analytic_summary(self, job_id: str):
        # ... (This method is complete and correct)
        job_results = self.get_full_job_results(job_id)
        if not job_results or not job_results['analytics']: return
        prompt = prompt_library.ANALYTICS_SUMMARY_PROMPT.format(analytics_json=json.dumps(job_results['analytics'], indent=2))
        summary_text = await gemini_service.generate_text(prompt, temperature=0.6)
        self.db.update_job_with_summary(job_id, summary_text)

# --- SINGLETON & DEPENDENCY PROVIDER ---
def get_assessment_service(db: DatabaseService = Depends(get_db_service)):
    return AssessmentService(db=db)