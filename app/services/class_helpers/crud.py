# /app/services/class_helpers/crud.py (CORRECTED)

import uuid
from typing import List, Dict, Optional

from ...models import class_model, student_model
from ..database_service import DatabaseService
from ...db.models.class_student_models import Class # Import the SQLAlchemy model

# --- CLASS-RELATED CORE BUSINESS LOGIC (UNCHANGED) ---
def get_student_by_student_id(student_id: str, db: DatabaseService) -> Optional[Dict]:
    """Checks if a student exists based on their user-provided studentId."""
    # This requires a new method in our repository and facade. We'll add it.
    return db.get_student_by_student_id(student_id)


def create_class(class_data: class_model.ClassCreate, db: DatabaseService) -> Class:
    """
    Creates a new class record in the database.
    This corrected version returns the SQLAlchemy Class object.
    """
    new_id = f"cls_{uuid.uuid4().hex[:12]}"
    new_class_record = class_data.model_dump()
    new_class_record['id'] = new_id
    
    # --- [THE FIX IS HERE] ---
    # db.add_class now returns the newly created SQLAlchemy object.
    # We capture and return this object instead of the old dictionary.
    new_class_object = db.add_class(new_class_record)
    return new_class_object
    # --- [END OF FIX] ---


def update_class(class_id: str, class_update: class_model.ClassCreate, db: DatabaseService) -> Optional[Dict]:
    update_data = class_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    updated_class = db.update_class(class_id, update_data)
    return updated_class

def delete_class_by_id(class_id: str, db: DatabaseService) -> bool:
    if not db.get_class_by_id(class_id): return False
    db.delete_students_by_class_id(class_id)
    db.delete_class(class_id)
    return True

# --- STUDENT-RELATED CORE BUSINESS LOGIC ---

def add_student_to_class(class_id: str, student_data: student_model.StudentCreate, db: DatabaseService) -> Dict:
    """Business logic to add a new student to a class."""
    if not db.get_class_by_id(class_id):
        raise ValueError(f"Class with ID {class_id} not found")

    # --- [THE FIX IS HERE] ---
    # Check if a student with this ID already exists anywhere in the system.
    existing_student = get_student_by_student_id(student_data.studentId, db)
    if existing_student:
        # For V1, we will log a warning and skip this student.
        # We return the existing student's data so the caller knows what happened.
        print(f"WARNING: Student with ID {student_data.studentId} already exists. Skipping creation.")
        return existing_student
    # --- [END OF FIX] ---

    new_student_id = f"stu_{uuid.uuid4().hex[:12]}"
    new_student_record = student_data.model_dump()
    new_student_record['id'] = new_student_id
    new_student_record['class_id'] = class_id
    new_student_record['overallGrade'] = 0
    
    new_student_object = db.add_student(new_student_record)
    # Convert the SQLAlchemy object to a dictionary before returning
    return {c.name: getattr(new_student_object, c.name) for c in new_student_object.__table__.columns}


def update_student(student_id: str, student_update: student_model.StudentUpdate, db: DatabaseService) -> Optional[Dict]:
    """Business logic to update a student's details."""
    update_data = student_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    updated_student = db.update_student(student_id, update_data)
    return updated_student