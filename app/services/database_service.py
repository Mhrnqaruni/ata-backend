# /ata-backend/app/services/database_service.py (FINAL MIGRATED VERSION, WITH DELETE METHOD)

import os
from typing import List, Dict, Optional, Generator
import pandas as pd
from sqlalchemy.orm import Session
from fastapi import Depends

# --- Core Database Setup ---
from app.db.database import get_db

# --- Repository Imports ---
# Import both the new SQL repositories and the old CSV repositories
from .database_helpers.class_student_repository_sql import ClassStudentRepositorySQL
from .database_helpers.assessment_repository_sql import AssessmentRepositorySQL
from .database_helpers.chat_repository_sql import ChatRepositorySQL
from .database_helpers.generation_repository_sql import GenerationRepositorySQL

from .database_helpers.class_student_repository import ClassStudentRepository as ClassStudentRepositoryCSV
from .database_helpers.assessment_repository import AssessmentRepository as AssessmentRepositoryCSV
from .database_helpers.chat_repository import ChatRepository as ChatRepositoryCSV
from .database_helpers.base_repository import BaseRepository

DATA_DIR = "app/data"
GENERATIONS_DB_PATH = f"{DATA_DIR}/generations.csv"

# Determine which data source to use based on an environment variable
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"


class DatabaseService:
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initializes the DatabaseService.
        If USE_POSTGRES is true, it requires a db_session.
        Otherwise, it falls back to the CSV-based repositories.
        """
        if USE_POSTGRES:
            if not db_session:
                raise ValueError("A database session is required when USE_POSTGRES is true.")
            # --- Initialize ALL SQL Repositories ---
            self.class_student_repo = ClassStudentRepositorySQL(db_session)
            self.assessment_repo = AssessmentRepositorySQL(db_session)
            self.chat_repo = ChatRepositorySQL(db_session)
            self.generation_repo = GenerationRepositorySQL(db_session)
        else:
            # --- Initialize CSV Repositories (Fallback for local dev) ---
            self.class_student_repo = ClassStudentRepositoryCSV()
            self.assessment_repo = AssessmentRepositoryCSV()
            self.chat_repo = ChatRepositoryCSV()
            self.generation_repo = BaseRepository(
                GENERATIONS_DB_PATH,
                columns=['id', 'title', 'tool_id', 'created_at', 'settings_snapshot', 'generated_content'],
                dtypes={'id': str, 'tool_id': str, 'title': str}
            )

    # --- CLASS & STUDENT METHODS (DELEGATED) ---
    def get_all_classes(self) -> List[Dict]: return self.class_student_repo.get_all_classes()
    def get_class_by_id(self, class_id: str) -> Optional[Dict]: return self.class_student_repo.get_class_by_id(class_id)
    def add_class(self, class_record: Dict): return self.class_student_repo.add_class(class_record)
    def update_class(self, class_id: str, class_update_data: Dict) -> Optional[Dict]: return self.class_student_repo.update_class(class_id, class_update_data)
    def delete_class(self, class_id: str) -> bool: return self.class_student_repo.delete_class(class_id)
    def get_all_students(self) -> List[Dict]: return self.class_student_repo.get_all_students()
    def get_students_by_class_id(self, class_id: str) -> List[Dict]: return self.class_student_repo.get_students_by_class_id(class_id)
    def add_student(self, student_record: Dict): return self.class_student_repo.add_student(student_record)
    def update_student(self, student_id: str, student_update_data: Dict) -> Optional[Dict]: return self.class_student_repo.update_student(student_id, student_update_data)
    def delete_student(self, student_id: str, class_id: str) -> bool: return self.class_student_repo.delete_student(student_id=student_id, class_id=class_id)
    def delete_students_by_class_id(self, class_id: str) -> int: return self.class_student_repo.delete_students_by_class_id(class_id)
    def get_classes_as_dataframe(self, user_id: str) -> pd.DataFrame: return self.class_student_repo.get_classes_as_dataframe(user_id=user_id)
    def get_students_as_dataframe(self, user_id: str) -> pd.DataFrame: return self.class_student_repo.get_students_as_dataframe(user_id=user_id)
    def get_assessments_as_dataframe(self, user_id: str) -> pd.DataFrame: return self.assessment_repo.get_assessments_as_dataframe(user_id=user_id)

    # --- GENERATION HISTORY METHODS (DELEGATED) ---
    def get_all_generations(self) -> List[Dict]: return self.generation_repo.get_all_generations()
    def add_generation_record(self, history_record: Dict): return self.generation_repo.add_generation_record(history_record)
    
    # --- [THIS IS THE NEWLY ADDED METHOD] ---
    def delete_generation_record(self, generation_id: str) -> bool:
        return self.generation_repo.delete_generation_record(generation_id)
    # --- [END OF NEW METHOD] ---
    
    # --- CHAT HISTORY METHODS (DELEGATED) ---
    def create_chat_session(self, session_record: Dict): return self.chat_repo.create_session(session_record)
    def get_chat_sessions_by_user_id(self, user_id: str) -> List[Dict]: return self.chat_repo.get_sessions_by_user_id(user_id)
    def get_chat_session_by_id(self, session_id: str) -> Optional[Dict]: return self.chat_repo.get_session_by_id(session_id)
    def add_chat_message(self, message_record: Dict): return self.chat_repo.add_message(message_record)
    def get_messages_by_session_id(self, session_id: str) -> List[Dict]: return self.chat_repo.get_messages_by_session_id(session_id)
    def delete_chat_session(self, session_id: str) -> bool: return self.chat_repo.delete_session_by_id(session_id)
    def delete_chat_messages_by_session_id(self, session_id: str) -> int:
        # This method is no longer needed as cascade delete handles it in SQL
        pass

    # --- ASSESSMENT JOB & RESULT METHODS (DELEGATED) ---
    def add_assessment_job(self, job_record: Dict): return self.assessment_repo.add_job(job_record)
    def get_assessment_job(self, job_id: str) -> Optional[Dict]: return self.assessment_repo.get_job(job_id)
    def get_all_assessment_jobs(self) -> List[Dict]: return self.assessment_repo.get_all_jobs()
    def update_job_status(self, job_id: str, status: str): self.assessment_repo.update_job_status(job_id, status)
    def update_job_with_summary(self, job_id: str, summary: str): self.assessment_repo.update_job_summary(job_id, summary)
    def delete_assessment_job(self, job_id: str) -> bool: return self.assessment_repo.delete_job(job_id)
    def save_student_grade_result(self, result_record: Dict): return self.assessment_repo.add_result(result_record)
    def get_all_results_for_job(self, job_id: str) -> List[Dict]: return self.assessment_repo.get_all_results_for_job(job_id)
    def get_result_by_token(self, token: str) -> Optional[Dict]: return self.assessment_repo.get_result_by_token(token)
    def update_student_result_with_grade(self, job_id: str, student_id: str, question_id: str, grade: Optional[float], feedback: str, status: str):
        self.assessment_repo.update_result_grade(job_id, student_id, question_id, grade, feedback, status)
    def get_student_by_student_id(self, student_id: str) -> Optional[Dict]: return self.class_student_repo.get_student_by_student_id(student_id)
    # ... other assessment methods can be added here if needed ...
    def get_all_results(self) -> List[Dict]: return self.assessment_repo.get_all_results()
    def update_student_result_path(self, job_id: str, student_id: str, path: str, content_type: str): return self.assessment_repo.update_result_path(job_id, student_id, path, content_type)
    # In /ata-backend/app/services/database_service.py
    def get_students_with_paths(self, job_id: str) -> List[Dict]:return self.assessment_repo.get_students_with_paths(job_id)


# --- NEW DEPENDENCY PROVIDER ---
# This replaces the old get_db_service function.
def get_db_service(db: Session = Depends(get_db)) -> Generator[DatabaseService, None, None]:
    """
    FastAPI dependency that provides a DatabaseService instance.
    It intelligently decides whether to use PostgreSQL or CSVs.
    """
    yield DatabaseService(db_session=db if USE_POSTGRES else None)