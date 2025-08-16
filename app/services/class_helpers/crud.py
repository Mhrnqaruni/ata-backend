# /app/services/class_helpers/crud.py (FINAL, CORRECTED VERSION)

import uuid
from typing import Dict, Optional

from ...models import class_model, student_model
from ..database_service import DatabaseService
from ...db.models.class_student_models import Class, Student # Import SQLAlchemy models

# --- CLASS-RELATED CORE BUSINESS LOGIC ---

def create_class(class_data: class_model.ClassCreate, db: DatabaseService) -> Class:
    """
    Creates a new class record in the database.
    Returns the newly created SQLAlchemy Class object.
    """
    new_id = f"cls_{uuid.uuid4().hex[:12]}"
    new_class_record = class_data.model_dump()
    new_class_record['id'] = new_id
    
    new_class_object = db.add_class(new_class_record)
    return new_class_object

def update_class(class_id: str, class_update: class_model.ClassCreate, db: DatabaseService) -> Optional[Class]:
    """Updates a class's details."""
    update_data = class_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    updated_class = db.update_class(class_id, update_data)
    return updated_class

def delete_class_by_id(class_id: str, db: DatabaseService) -> bool:
    """Deletes a class and all its associated students."""
    if not db.get_class_by_id(class_id):
        return False
    db.delete_students_by_class_id(class_id)
    db.delete_class(class_id)
    return True

# --- STUDENT-RELATED CORE BUSINESS LOGIC ---

def add_student_to_class_with_status(class_id: str, student_data: student_model.StudentCreate, db: DatabaseService) -> tuple[Student, bool]:
    """
    Adds a student to a class, checking for pre-existence based on studentId.
    This is the SPECIALIST function for batch processing (e.g., roster uploads).
    Returns a tuple: (SQLAlchemy_Student_object, was_created_boolean).
    """
    if not db.get_class_by_id(class_id):
        raise ValueError(f"Class with ID {class_id} not found")

    existing_student = db.get_student_by_student_id(student_data.studentId)
    if existing_student:
        print(f"INFO: Student with ID {student_data.studentId} already exists. Skipping creation.")
        return existing_student, False # Return existing student object, signal not created

    new_student_id = f"stu_{uuid.uuid4().hex[:12]}"
    new_student_record = student_data.model_dump()
    new_student_record['id'] = new_student_id
    new_student_record['class_id'] = class_id
    new_student_record['overallGrade'] = 0
    
    new_student_object = db.add_student(new_student_record)
    return new_student_object, True # Return new student object, signal created

def add_student_to_class(class_id: str, student_data: student_model.StudentCreate, db: DatabaseService) -> Student:
    """
    A simpler wrapper for the manual "Add Student" API endpoint.
    It checks for duplicates and returns only the final student object.
    """
    student_object, _ = add_student_to_class_with_status(class_id, student_data, db)
    return student_object

def update_student(student_id: str, student_update: student_model.StudentUpdate, db: DatabaseService) -> Optional[Student]:
    """Updates a student's details."""
    update_data = student_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    updated_student = db.update_student(student_id, update_data)
    return updated_student