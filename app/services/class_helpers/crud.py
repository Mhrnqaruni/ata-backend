# /app/services/class_helpers/crud.py (CORRECTED)

import uuid
from typing import List, Dict, Optional

from ...models import class_model, student_model
from ..database_service import DatabaseService

# --- CLASS-RELATED CORE BUSINESS LOGIC (UNCHANGED) ---

def create_class(class_data: class_model.ClassCreate, db: DatabaseService) -> Dict:
    new_id = f"cls_{uuid.uuid4().hex[:12]}"
    new_class_record = class_data.model_dump()
    new_class_record['id'] = new_id
    db.add_class(new_class_record)
    return new_class_record

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
    new_student_id = f"stu_{uuid.uuid4().hex[:12]}"
    new_student_record = student_data.model_dump()
    new_student_record['id'] = new_student_id
    new_student_record['class_id'] = class_id
    new_student_record['overallGrade'] = 0

    # --- [THE DIAGNOSTIC STEP IS HERE] ---
    # Add this print statement to see the exact record before it's saved.
    print(f"DEBUG: Saving student record: {new_student_record}")
    # --- [END OF DIAGNOSTIC STEP] ---

    db.add_student(new_student_record)
    return new_student_record


def update_student(student_id: str, student_update: student_model.StudentUpdate, db: DatabaseService) -> Optional[Dict]:
    """Business logic to update a student's details."""
    update_data = student_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    updated_student = db.update_student(student_id, update_data)
    return updated_student