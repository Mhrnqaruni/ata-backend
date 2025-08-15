# /app/services/database_service.py

from typing import List, Dict, Optional
import pandas as pd

from .database_helpers.base_repository import BaseRepository
from .database_helpers.class_student_repository import ClassStudentRepository
from .database_helpers.assessment_repository import AssessmentRepository
from .database_helpers.chat_repository import ChatRepository

DATA_DIR = "app/data"
GENERATIONS_DB_PATH = f"{DATA_DIR}/generations.csv"

class DatabaseService:
    def __init__(self):
        self.class_student_repo = ClassStudentRepository()
        self.assessment_repo = AssessmentRepository()
        self.chat_repo = ChatRepository()
        self.generation_repo = BaseRepository(
            GENERATIONS_DB_PATH,
            columns=['id', 'title', 'tool_id', 'created_at', 'settings_snapshot', 'generated_content'],
            dtypes={'id': str, 'tool_id': str, 'title': str}
        )

    # --- CLASS & STUDENT METHODS (DELEGATED) ---
    def get_all_classes(self) -> List[Dict]:
        return self.class_student_repo.get_all_classes()
    def get_class_by_id(self, class_id: str) -> Optional[Dict]:
        return self.class_student_repo.get_class_by_id(class_id)
    def add_class(self, class_record: Dict):
        self.class_student_repo.add_class(class_record)
    def update_class(self, class_id: str, class_update_data: Dict) -> Optional[Dict]:
        return self.class_student_repo.update_class(class_id, class_update_data)
    def delete_class(self, class_id: str) -> bool:
        return self.class_student_repo.delete_class(class_id)
    def get_all_students(self) -> List[Dict]:
        return self.class_student_repo.get_all_students()
    def get_students_by_class_id(self, class_id: str) -> List[Dict]:
        return self.class_student_repo.get_students_by_class_id(class_id)
    def add_student(self, student_record: Dict):
        self.class_student_repo.add_student(student_record)
    def update_student(self, student_id: str, student_update_data: Dict) -> Optional[Dict]:
        return self.class_student_repo.update_student(student_id, student_update_data)
    def delete_student(self, student_id: str, class_id: str) -> bool:
        return self.class_student_repo.delete_student(student_id=student_id, class_id=class_id)
    def delete_students_by_class_id(self, class_id: str) -> int:
        return self.class_student_repo.delete_students_by_class_id(class_id)
        
    # --- [THE FIX IS HERE] ---
    def get_classes_as_dataframe(self, user_id: str) -> pd.DataFrame:
        return self.class_student_repo.get_classes_as_dataframe(user_id=user_id)
    def get_students_as_dataframe(self, user_id: str) -> pd.DataFrame:
        return self.class_student_repo.get_students_as_dataframe(user_id=user_id)
    def get_assessments_as_dataframe(self, user_id: str) -> pd.DataFrame:
        return self.assessment_repo.get_assessments_as_dataframe(user_id=user_id)
    # --- [END OF FIX] ---

    # --- GENERATION HISTORY METHODS (DELEGATED) ---
    def get_all_generations(self) -> List[Dict]:
        return self.generation_repo._clean_df_for_export(self.generation_repo.df)
    def add_generation_record(self, history_record: Dict):
        self.generation_repo._add_record(history_record)
    
    # --- CHAT HISTORY METHODS (DELEGATED) ---
    def create_chat_session(self, session_record: Dict):
        self.chat_repo.create_session(session_record)
    def get_chat_sessions_by_user_id(self, user_id: str) -> List[Dict]:
        return self.chat_repo.get_sessions_by_user_id(user_id)
    def get_chat_session_by_id(self, session_id: str) -> Optional[Dict]:
        return self.chat_repo.get_session_by_id(session_id)
    def add_chat_message(self, message_record: Dict):
        self.chat_repo.add_message(message_record)
    def get_messages_by_session_id(self, session_id: str) -> List[Dict]:
        return self.chat_repo.get_messages_by_session_id(session_id)

    # --- ASSESSMENT JOB METHODS (DELEGATED) ---
    def add_assessment_job(self, job_record: Dict):
        self.assessment_repo.add_job(job_record)
    def get_assessment_job(self, job_id: str) -> Optional[Dict]:
        return self.assessment_repo.get_job(job_id)
    def get_all_assessment_jobs(self) -> List[Dict]:
        return self.assessment_repo.get_all_jobs()
    def update_job_status(self, job_id: str, status: str):
        self.assessment_repo.update_job_status(job_id, status)
    def update_job_with_summary(self, job_id: str, summary: str):
        self.assessment_repo.update_job_summary(job_id, summary)
    def delete_assessment_job(self, job_id: str) -> bool:
        return self.assessment_repo.delete_job(job_id)
    def delete_results_by_job_id(self, job_id: str) -> int:
        return self.assessment_repo.delete_results_by_job_id(job_id)

    # --- ASSESSMENT RESULT METHODS (DELEGATED) ---
    def save_student_grade_result(self, result_record: Dict):
        self.assessment_repo.add_result(result_record)
    def get_all_results_for_job(self, job_id: str) -> List[Dict]:
        return self.assessment_repo.get_all_results_for_job(job_id)
    def get_all_results(self) -> List[Dict]:
        return self.assessment_repo.get_all_results()
    def get_student_result_path(self, job_id: str, student_id: str) -> Optional[str]:
        return self.assessment_repo.get_student_result_path(job_id, student_id)
    def get_students_with_paths(self, job_id: str) -> List[Dict]:
        return self.assessment_repo.get_students_with_paths(job_id)
    def get_result_by_token(self, token: str) -> Optional[Dict]:
        return self.assessment_repo.get_result_by_token(token)
    def update_student_result_path(self, job_id: str, student_id: str, path: str, content_type: str):
        self.assessment_repo.update_result_path(job_id, student_id, path, content_type)
    def update_result_status(self, job_id: str, student_id: str, question_id: str, status: str):
        self.assessment_repo.update_result_status(job_id, student_id, question_id, status)
    def update_student_result_with_grade(self, job_id: str, student_id: str, question_id: str, grade: Optional[float], feedback: str, status: str):
        self.assessment_repo.update_result_grade(job_id, student_id, question_id, grade, feedback, status)
    def update_result_with_isolated_answer(self, job_id: str, student_id: str, question_id: str, extracted_answer: str):
        self.assessment_repo.update_result_with_isolated_answer(job_id, student_id, question_id, extracted_answer)

    def delete_chat_session(self, session_id: str) -> bool:
        """Deletes a single chat session record."""
        return self.chat_repo.delete_session_by_id(session_id)

    def delete_chat_messages_by_session_id(self, session_id: str) -> int:
        """Deletes all messages for a given session."""
        return self.chat_repo.delete_messages_by_session_id(session_id)

# --- SINGLETON INSTANCE & DEPENDENCY PROVIDER ---
db_service_instance = DatabaseService()

def get_db_service():
    yield db_service_instance




