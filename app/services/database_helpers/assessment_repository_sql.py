# /ata-backend/app/services/database_helpers/assessment_repository_sql.py (FINAL, CORRECTED VERSION)

from typing import List, Dict, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select, distinct
from app.db.models.assessment_models import Assessment, Result

class AssessmentRepositorySQL:
    def __init__(self, db_session: Session):
        self.db = db_session

    # --- Assessment Job Methods (Unchanged and Correct) ---
    def add_job(self, record: Dict):
        new_job = Assessment(**record)
        self.db.add(new_job)
        self.db.commit()
        self.db.refresh(new_job)
        return new_job

    def get_job(self, job_id: str) -> Optional[Assessment]:
        return self.db.query(Assessment).filter(Assessment.id == job_id).first()

    def get_all_jobs(self) -> List[Assessment]:
        return self.db.query(Assessment).order_by(Assessment.created_at.desc()).all()

    def update_job_status(self, job_id: str, status: str):
        job = self.get_job(job_id)
        if job:
            job.status = status
            self.db.commit()

    def update_job_summary(self, job_id: str, summary: str):
        job = self.get_job(job_id)
        if job:
            job.ai_summary = summary
            self.db.commit()

    def delete_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if job:
            self.db.delete(job)
            self.db.commit()
            return True
        return False

    # --- Assessment Result Methods (Unchanged and Correct) ---
    def add_result(self, record: Dict):
        new_result = Result(**record)
        self.db.add(new_result)
        self.db.commit()
        self.db.refresh(new_result)
        return new_result

    def get_all_results_for_job(self, job_id: str) -> List[Result]:
        return self.db.query(Result).filter(Result.job_id == job_id).all()

    def get_all_results(self) -> List[Result]:
        return self.db.query(Result).all()

    def get_result_by_token(self, token: str) -> Optional[Result]:
        return self.db.query(Result).filter(Result.report_token == token).first()
        
    def update_result_grade(self, job_id: str, student_id: str, question_id: str, grade: Optional[float], feedback: str, status: str):
        result = self.db.query(Result).filter_by(job_id=job_id, student_id=student_id, question_id=question_id).first()
        if result:
            result.grade = grade
            result.feedback = feedback
            result.status = status
            self.db.commit()

    def update_result_path(self, job_id: str, student_id: str, path: str, content_type: str):
        results_to_update = self.db.query(Result).filter_by(job_id=job_id, student_id=student_id).all()
        if results_to_update:
            for result in results_to_update:
                result.answer_sheet_path = path
                result.content_type = content_type
                result.status = 'matched'
            self.db.commit()

    def get_students_with_paths(self, job_id: str) -> List[Dict]:
        stmt = (
            select(Result.student_id, Result.answer_sheet_path, Result.content_type)
            .where(Result.job_id == job_id, Result.answer_sheet_path != None, Result.answer_sheet_path != '')
            .distinct()
        )
        results = self.db.execute(stmt).mappings().all()
        return [dict(row) for row in results]

    def get_student_result_path(self, job_id: str, student_id: str) -> Optional[str]:
        result = self.db.query(Result.answer_sheet_path).filter_by(
            job_id=job_id, 
            student_id=student_id
        ).first()
        return result[0] if result else None

    def update_result_status(self, job_id: str, student_id: str, question_id: str, status: str):
        result = self.db.query(Result).filter_by(
            job_id=job_id, 
            student_id=student_id, 
            question_id=question_id
        ).first()
        if result:
            result.status = status
            self.db.commit()

    # --- [THE FIX IS HERE: METHOD RENAMED AND REIMPLEMENTED] ---
    def get_assessments_for_chatbot(self, user_id: str) -> List[Dict]:
        """
        Returns a list of result dictionaries for the chatbot sandbox.
        V2 TODO: This is a simplified model. A real implementation would join
        results and assessments and filter by the user's classes.
        """
        all_results = self.db.query(Result).all()
        # Convert the list of SQLAlchemy Result objects into a list of dictionaries
        return [{c.name: getattr(obj, c.name) for c in obj.__table__.columns} for obj in all_results]
    # --- [END OF FIX] ---