# /ata-backend/app/services/assessment_service.py (SUPERVISOR-APPROVED FLAWLESS VERSION)

"""
This module defines the AssessmentService, the high-level orchestrator for the
entire assessment grading pipeline.

As a core business service, it is now fully "user-aware." Every public-facing
method requires a `user_id` to ensure that all orchestrated operations—from job
creation to result fetching—are securely scoped to the data owned by the
authenticated user. It threads this user context down to all underlying helpers
and data access layer calls.
"""

import uuid, json, os, datetime, asyncio, shutil
from fastapi import UploadFile, Depends
from typing import List, Dict, Optional, Union, Tuple

# Import all services and helpers
from . import ocr_service, gemini_service, prompt_library, report_service, zip_service, library_service
from .database_service import DatabaseService, get_db_service
from ..models import assessment_model
from .assessment_helpers import job_creation, grading_pipeline, data_assembly, document_parser, analytics_and_matching

ASSESSMENT_UPLOADS_DIR = "assessment_uploads" 

class AssessmentService:
    def __init__(self, db: DatabaseService = Depends(get_db_service)):
        self.db = db

    # --- V2 WORKFLOW (Pure parsing step, security check is in the calling router) ---
    async def parse_document_for_review(self, question_file: UploadFile, answer_key_file: Optional[UploadFile], class_id: str, assessment_name: str) -> Dict:
        """
        Parses document(s) to create a V2 assessment configuration.
        This is a pure data processor. The security check that the user owns the
        `class_id` is the responsibility of the calling router, which will verify
        ownership before calling this service.
        """
        return await document_parser.parse_document_to_config(question_file, answer_key_file, class_id, assessment_name)

    # --- JOB CREATION METHODS (Now User-Aware) ---
    def create_new_assessment_job_v2(
        self, 
        config: assessment_model.AssessmentConfigV2, 
        answer_sheets: List[UploadFile],
        user_id: str
    ) -> Dict:
        """Creates a V2 assessment job, securely associating it with the user."""
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        answer_sheet_data = job_creation._save_uploaded_files(job_id, answer_sheets)
        # The user_id is passed down to the helper to be stamped on the new record.
        job_creation._create_initial_job_records_v2(self.db, job_id, config, answer_sheet_data, user_id)
        return { "jobId": job_id, "status": assessment_model.JobStatus.QUEUED.value, "message": "Assessment job created." }
        
    def create_new_assessment_job(
        self, 
        config: assessment_model.AssessmentConfig, 
        answer_sheets: List[UploadFile],
        user_id: str
    ) -> Dict:
        """Creates a V1 assessment job, securely associating it with the user."""
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        answer_sheet_data = job_creation._save_uploaded_files(job_id, answer_sheets)
        # The user_id is passed down to the helper to be stamped on the new record.
        job_creation._create_initial_job_records(self.db, job_id, config, answer_sheet_data, user_id)
        return { "jobId": job_id, "status": assessment_model.JobStatus.QUEUED.value, "message": "Assessment job created." }

    # --- JOB DELETION (Now User-Aware) ---
    def delete_assessment_job(self, job_id: str, user_id: str) -> bool:
        """Orchestrates the cascading delete of a user-owned assessment job."""
        # The user_id is passed to the data access layer to ensure a user can
        # only delete an assessment that they own.
        was_deleted = self.db.delete_assessment_job(job_id=job_id, user_id=user_id)
        if not was_deleted:
            return False

        job_dir = os.path.join(ASSESSMENT_UPLOADS_DIR, job_id)
        if os.path.isdir(job_dir):
            shutil.rmtree(job_dir)
        
        return True

    # --- MAIN PROCESSING PIPELINE (Now Securely Context-Aware) ---
    async def process_assessment_job(self, job_id: str, user_id: str):
        """
        The main background task for processing a job. It is secure because it
        is invoked with the owner's `user_id`, which is then used for all
        subsequent database operations within the task.
        """
        try:
            self.db.update_job_status(job_id, user_id, assessment_model.JobStatus.PROCESSING.value)
            await analytics_and_matching.match_files_to_students(self.db, job_id, user_id)
            
            job_record = self.db.get_assessment_job(job_id, user_id)
            if not job_record:
                raise ValueError(f"Job {job_id} not found for user {user_id} during processing.")

            config = analytics_and_matching.get_validated_config_from_job(job_record)
            
            students_to_grade = self.db.get_students_with_paths(job_id, user_id)
            
            grading_tasks = [
                self._grade_entire_submission_for_student(job_id, student['student_id'], student['answer_sheet_path'], student['content_type'], config, user_id) 
                for student in students_to_grade
            ]
            await asyncio.gather(*grading_tasks)
            
            self.db.update_job_status(job_id, user_id, assessment_model.JobStatus.SUMMARIZING.value)
            await self._generate_analytic_summary(job_id, user_id)
            self.db.update_job_status(job_id, user_id, assessment_model.JobStatus.COMPLETED.value)
        except Exception as e:
            print(f"CRITICAL ERROR processing job {job_id} for user {user_id}: {e}")
            self.db.update_job_status(job_id, user_id, assessment_model.JobStatus.FAILED.value)

    async def _grade_entire_submission_for_student(self, job_id: str, student_id: str, answer_sheet_path: str, content_type: str, config: Union[assessment_model.AssessmentConfig, assessment_model.AssessmentConfigV2], user_id: str):
        """Internal helper for grading a single student's submission."""
        all_questions = [q for s in config.sections for q in s.questions] if isinstance(config, assessment_model.AssessmentConfigV2) else config.questions
        try:
            for q in all_questions:
                self.db.update_result_status(job_id, student_id, q.id, "processing", user_id)
            
            image_list = grading_pipeline._prepare_images_from_answersheet(answer_sheet_path, content_type)
            questions_json_str = json.dumps([q.model_dump() for q in all_questions], indent=2)
            
            answer_key_context = "No answer key was provided. Grade based on general knowledge."
            if isinstance(config, assessment_model.AssessmentConfigV2):
                if config.gradingMode == "library" and config.librarySource:
                    chapter_content = library_service.get_chapter_content(config.librarySource)
                    answer_key_context = f"The following text from the curriculum library is the definitive answer key:\n---\n{chapter_content}\n---"
                elif config.gradingMode == "answer_key_provided":
                    answer_key_context = "The correct answers are included within each question object in the JSON below. Use these as the ground truth."
            
            prompt = prompt_library.STUDENT_CENTRIC_GRADING_PROMPT.format(questions_json=questions_json_str, answer_key_context=answer_key_context)
            ai_response_str = await grading_pipeline._invoke_grading_ai(prompt, image_list)
            parsed_results = grading_pipeline._parse_ai_grading_response(ai_response_str)
            
            for result_data in parsed_results['results']:
                self.db.update_student_result_with_grade(
                    job_id=job_id, student_id=student_id,
                    question_id=result_data['question_id'],
                    grade=grading_pipeline._safe_float_convert(result_data.get('grade')),
                    feedback=result_data.get('feedback', ''),
                    status="ai_graded", user_id=user_id
                )

        except Exception as e:
            print(f"ERROR grading submission for student {student_id} in job {job_id}: {e}")
            for q in all_questions:
                self.db.update_result_status(job_id, student_id, q.id, "failed", user_id)

    # --- DATA FETCHING & ASSEMBLY (Now User-Aware) ---
    def get_all_assessment_jobs_summary(self, user_id: str) -> Dict:
        """Retrieves a summary list of all jobs for a specific user."""
        all_jobs = self.db.get_all_assessment_jobs(user_id=user_id)
        all_results = self.db.get_all_results_for_user(user_id=user_id)
        all_classes_objs = self.db.get_all_classes(user_id=user_id)
        
        all_classes_map = {c.id: c.name for c in all_classes_objs}
        
        summaries = data_assembly._assemble_job_summaries(all_jobs, all_results, all_classes_map)
        return {"assessments": summaries}

    def get_full_job_results(self, job_id: str, user_id: str) -> Optional[Dict]:
        """Retrieves the complete, aggregated results for a user-owned job."""
        job_record = self.db.get_assessment_job(job_id=job_id, user_id=user_id)
        if not job_record:
            return None
        
        config_v2 = analytics_and_matching.normalize_config_to_v2(job_record)
        class_students = self.db.get_students_by_class_id(class_id=config_v2.classId, user_id=user_id)
        all_results_for_job = self.db.get_all_results_for_job(job_id=job_id, user_id=user_id)
        
        final_results_dict = data_assembly._build_results_dictionary(class_students, config_v2, all_results_for_job)
        
        # --- [CRITICAL SECURITY FIX APPLIED HERE] ---
        # The call to get_student_result_path now includes the user_id,
        # ensuring that this nested data lookup is also secure.
        students_list = [{"id": s.id, "name": s.name, "answerSheetPath": self.db.get_student_result_path(job_id, s.id, user_id)} for s in class_students]
        
        analytics_data = None
        if job_record.status == assessment_model.JobStatus.COMPLETED.value:
            analytics_data = analytics_and_matching.calculate_analytics(all_results_for_job, config_v2)
            
        return {
            "jobId": job_record.id, "assessmentName": config_v2.assessmentName,
            "status": job_record.status, "config": config_v2,
            "students": students_list, "results": final_results_dict,
            "analytics": analytics_data, "aiSummary": job_record.ai_summary
        }

    async def generate_single_report_docx(self, job_id: str, student_id: str, user_id: str) -> Tuple[bytes, str]:
        """Generates a single student report, ensuring the user owns the data."""
        full_job_data = self.get_full_job_results(job_id=job_id, user_id=user_id)
        if not full_job_data:
            raise ValueError(f"Job with ID {job_id} not found or access denied.")
        
        student_details = next((s for s in full_job_data['students'] if s['id'] == student_id), None)
        if not student_details:
            raise ValueError(f"Student with ID {student_id} not found in job {job_id}.")

        config = full_job_data['config']
        class_info_obj = self.db.get_class_by_id(config.classId, user_id=user_id)
        class_name = class_info_obj.name if class_info_obj else "Unknown Class"
        
        all_questions = [q for section in config.sections for q in section.questions]
        student_results = full_job_data['results'].get(student_id, {})
        
        total_score = sum(float(res.get('grade', 0) or 0) for res in student_results.values())
        total_max_score = sum(q.maxScore or 0 for q in all_questions)
        final_grade_percent = round((total_score / total_max_score) * 100) if total_max_score > 0 else 0
        
        question_breakdown = []
        for q in all_questions:
            result = student_results.get(q.id, {})
            grade = result.get('grade')
            question_breakdown.append({
                "text": q.text,
                "grade": f"{grade if grade is not None else 'N/A'} / {q.maxScore}",
                "feedback": result.get('feedback', 'No feedback available.')
            })

        report_data = {
            "studentName": student_details['name'],
            "finalGrade": final_grade_percent,
            "questions": question_breakdown,
            "assessmentName": config.assessmentName,
            "className": class_name
        }
        report_bytes = await asyncio.to_thread(report_service.create_word_report, report_data)
        
        safe_student_name = "".join(c for c in student_details['name'] if c.isalnum() or c in " _-").rstrip()
        filename = f"Report_{config.assessmentName}_{safe_student_name}.docx"
        return report_bytes, filename
    
    def get_job_config(self, job_id: str, user_id: str) -> Dict:
        """Retrieves a job's configuration for cloning, ensuring user ownership."""
        job = self.db.get_assessment_job(job_id=job_id, user_id=user_id)
        if not job:
            raise ValueError("Assessment job not found or access denied.")
        
        v2_config = analytics_and_matching.normalize_config_to_v2(job)
        v1_questions = [q for s in v2_config.sections for q in s.questions]
        return {"assessmentName": v2_config.assessmentName, "questions": [q.model_dump() for q in v1_questions], "includeImprovementTips": v2_config.includeImprovementTips}
        
    async def _generate_analytic_summary(self, job_id: str, user_id: str):
        """Generates and saves an AI summary for a user-owned job."""
        job_results = self.get_full_job_results(job_id=job_id, user_id=user_id)
        if not job_results or not job_results.get('analytics'):
            return
            
        prompt = prompt_library.ANALYTICS_SUMMARY_PROMPT.format(analytics_json=json.dumps(job_results['analytics'], indent=2))
        summary_text = await gemini_service.generate_text(prompt, temperature=0.6)
        self.db.update_job_with_summary(job_id=job_id, user_id=user_id, summary=summary_text)

# --- SINGLETON & DEPENDENCY PROVIDER ---
def get_assessment_service(db: DatabaseService = Depends(get_db_service)):
    """Dependency provider for the AssessmentService."""
    return AssessmentService(db=db)