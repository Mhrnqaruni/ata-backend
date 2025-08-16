# /ata-backend/app/services/database_helpers/class_student_repository_sql.py

from typing import List, Dict, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models.class_student_models import Class, Student

class ClassStudentRepositorySQL:
    def __init__(self, db_session: Session):
        self.db = db_session

    # --- Class Methods ---
    def get_all_classes(self) -> List[Class]:
        return self.db.query(Class).all()

    def get_class_by_id(self, class_id: str) -> Optional[Class]:
        return self.db.query(Class).filter(Class.id == class_id).first()

    def add_class(self, record: Dict):
        new_class = Class(**record)
        self.db.add(new_class)
        self.db.commit()
        self.db.refresh(new_class)
        return new_class

    def update_class(self, class_id: str, data: Dict) -> Optional[Class]:
        db_class = self.get_class_by_id(class_id)
        if db_class:
            for key, value in data.items():
                setattr(db_class, key, value)
            self.db.commit()
            self.db.refresh(db_class)
        return db_class

    def delete_class(self, class_id: str) -> bool:
        db_class = self.get_class_by_id(class_id)
        if db_class:
            self.db.delete(db_class)
            self.db.commit()
            return True
        return False

    # --- Student Methods ---
    def get_all_students(self) -> List[Student]:
        return self.db.query(Student).all()

    def get_students_by_class_id(self, class_id: str) -> List[Student]:
        return self.db.query(Student).filter(Student.class_id == class_id).all()

    def add_student(self, record: Dict):
        # Ensure overallGrade is an integer or None, defaulting to None if not present
        record['overallGrade'] = int(record.get('overallGrade')) if record.get('overallGrade') is not None else None
        new_student = Student(**record)
        self.db.add(new_student)
        self.db.commit()
        self.db.refresh(new_student)
        return new_student

    def update_student(self, student_id: str, data: Dict) -> Optional[Student]:
        db_student = self.db.query(Student).filter(Student.id == student_id).first()
        if db_student:
            for key, value in data.items():
                # Handle potential type conversion for grade
                if key == 'overallGrade' and value is not None:
                    value = int(value)
                setattr(db_student, key, value)
            self.db.commit()
            self.db.refresh(db_student)
        return db_student

    def delete_student(self, student_id: str, class_id: str) -> bool:
        # The scoped delete is more robust with a database query
        db_student = self.db.query(Student).filter(Student.id == student_id, Student.class_id == class_id).first()
        if db_student:
            self.db.delete(db_student)
            self.db.commit()
            return True
        return False

    def delete_students_by_class_id(self, class_id: str) -> int:
        num_deleted = self.db.query(Student).filter(Student.class_id == class_id).delete()
        self.db.commit()
        return num_deleted

    # --- DataFrame Methods for Chatbot ---
    def get_classes_as_dataframe(self, user_id: str) -> pd.DataFrame:
        # V2 TODO: Filter by user_id when added to the Class model
        query = self.db.query(Class)
        return pd.read_sql(query.statement, self.db.bind)

    def get_students_as_dataframe(self, user_id: str) -> pd.DataFrame:
        # V2 TODO: Filter by user_id when added to the Student model
        query = self.db.query(Student)
        return pd.read_sql(query.statement, self.db.bind)
    

        # In class_student_repository_sql.py
    def get_student_by_student_id(self, student_id: str) -> Optional[Student]:
        return self.db.query(Student).filter(Student.studentId == student_id).first()
