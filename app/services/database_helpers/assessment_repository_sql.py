# /ata-backend/app/services/database_helpers/assessment_repository_sql.py

from typing import List, Dict, Optional
import pandas as pd
from sqlalchemy.orm import Session
from app.db.models.assessment_models import Assessment, Result

class AssessmentRepositorySQL:
    def __init__(self, db_session: Session):
        self.db = db_session

    # --- Assessment Job Methods ---
    def add_job(self, record: Dict):
        new_job = Assessment(**record)
        self.db.add(new_job)
        self.db.commit()
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

    # --- Assessment Result Methods ---
    def add_result(self, record: Dict):
        new_result = Result(**record)
        self.db.add(new_result)
        self.db.commit()

    def get_all_results_for_job(self, job_id: str) -> List[Result]:
        return self.db.query(Result).filter(Result.job_id == job_id).all()

    def get_result_by_token(self, token: str) -> Optional[Result]:
        return self.db.query(Result).filter(Result.report_token == token).first()
        
    def update_result_grade(self, job_id: str, student_id: str, question_id: str, grade: Optional[float], feedback: str, status: str):
        result = self.db.query(Result).filter_by(job_id=job_id, student_id=student_id, question_id=question_id).first()
        if result:
            result.grade = grade
            result.feedback = feedback
            result.status = status
            self.db.commit()

    def get_all_results(self) -> List[Result]:
        return self.db.query(Result).all()

    # ... other result update methods would follow the same pattern ...

    def get_assessments_as_dataframe(self, user_id: str) -> pd.DataFrame:
        query = self.db.query(Result) # Simplified for V1 as per original logic
        return pd.read_sql(query.statement, self.db.bind)