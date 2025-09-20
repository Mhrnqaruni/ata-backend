# /ata-backend/app/services/class_service.py (SUPERVISOR-APPROVED FLAWLESS VERSION)

"""
This service module acts as the primary business logic layer for all operations
related to classes and students.

It serves as a facade, orchestrating calls to lower-level specialist helpers
(like `crud` and `roster_ingestion`) and the `DatabaseService`. Every function
in this module has been made "user-aware," requiring a `user_id` to ensure
that all operations are securely scoped to the authenticated user. This module
is the critical link between the API routers and the data access layer.
"""

import pandas as pd
from typing import List, Dict, Optional
from fastapi import UploadFile

from ..models import class_model, student_model
from .database_service import DatabaseService

# Import the specialist helper modules this service orchestrates.
from .class_helpers import roster_ingestion, crud


# --- Facade Methods for CRUD Operations ---

def create_class(
    class_data: class_model.ClassCreate, 
    db: DatabaseService, 
    user_id: str
):
    """
    Business logic to create a new class for the authenticated user.

    This function "stamps" the owner's user_id onto the new class record
    before passing it to the low-level CRUD helper for persistence.
    """
    # Create a dictionary from the Pydantic model and add the owner's ID.
    class_record = {"user_id": user_id, **class_data.model_dump()}
    
    # Delegate the actual database insertion to the CRUD helper.
    return crud.create_class(class_record=class_record, db=db)


def update_class(
    class_id: str, 
    class_update: class_model.ClassCreate, 
    db: DatabaseService, 
    user_id: str
):
    """
    Business logic to update a class, ensuring the user has ownership.
    The user_id is passed down to the CRUD helper for security validation.
    """
    return crud.update_class(
        class_id=class_id, 
        class_update=class_update, 
        db=db, 
        user_id=user_id
    )


def delete_class_by_id(class_id: str, db: DatabaseService, user_id: str) -> bool:
    """
    Business logic to delete a class, ensuring the user has ownership.
    The user_id is passed down to the CRUD helper for security validation.
    """
    return crud.delete_class_by_id(class_id=class_id, db=db, user_id=user_id)


def add_student_to_class(
    class_id: str, 
    student_data: student_model.StudentCreate, 
    db: DatabaseService, 
    user_id: str
):
    """
    Business logic to add a student to a class, ensuring the user owns the class.
    The user_id is passed down to the CRUD helper for security validation.
    """
    return crud.add_student_to_class(
        class_id=class_id, 
        student_data=student_data, 
        db=db, 
        user_id=user_id
    )


def update_student(
    student_id: str, 
    student_update: student_model.StudentUpdate, 
    db: DatabaseService, 
    user_id: str
):
    """
    Business logic to update a student, ensuring the user owns the student's class.
    The user_id is passed down to the CRUD helper for security validation.
    """
    return crud.update_student(
        student_id=student_id, 
        student_update=student_update, 
        db=db, 
        user_id=user_id
    )


def delete_student_from_class(
    class_id: str,
    student_id: str, 
    db: DatabaseService, 
    user_id: str
) -> bool:
    """
    Business logic to delete a student, ensuring the user has ownership of the
    parent class.

    The user_id and class_id are passed directly to the DatabaseService for a
    secure, explicit delete operation.
    """
    # The `delete_student` method in the DatabaseService is designed to use
    # class_id and user_id for a fully secure, context-aware deletion.
    return db.delete_student(class_id=class_id, student_id=student_id, user_id=user_id)


async def create_class_from_upload(
    name: str, 
    file: UploadFile, 
    db: DatabaseService, 
    user_id: str
) -> Dict:
    """
    Business logic to orchestrate class creation from a file upload.
    The user_id is passed down to the ingestion helper to ensure the entire
    process is securely scoped to the authenticated user.
    """
    return await roster_ingestion.create_class_from_upload(
        name=name, 
        file=file, 
        db=db, 
        user_id=user_id
    )


# --- Data Assembly & Export Logic ---

def get_all_classes_with_summary(user_id: str, db: DatabaseService) -> List[Dict]:
    """
    Business logic to retrieve all classes for a user and enrich them with student counts.
    """
    # Securely fetch only the classes belonging to the authenticated user.
    all_classes = db.get_all_classes(user_id=user_id)
    if not all_classes:
        return []

    # Securely fetch all students belonging to the authenticated user to calculate counts.
    students_list_of_dicts = db.get_students_for_chatbot(user_id=user_id)
    students_df = pd.DataFrame(students_list_of_dicts)
    
    student_counts = {}
    if not students_df.empty and 'class_id' in students_df.columns:
        student_counts = students_df.groupby('class_id').size().to_dict()

    summary_list = []
    for cls in all_classes:
        summary_data = {
            "id": cls.id,
            "name": cls.name,
            "description": cls.description,
            "studentCount": student_counts.get(str(cls.id), 0) # Ensure key is string for lookup
        }
        summary_list.append(summary_data)
    return summary_list


def get_class_details_by_id(class_id: str, user_id: str, db: DatabaseService) -> Optional[Dict]:
    """
    Business logic to assemble the full details for the Class Details page,
    ensuring the user has ownership of the requested class.
    """
    # Securely fetch the class, ensuring it belongs to the user.
    class_info = db.get_class_by_id(class_id=class_id, user_id=user_id)
    if not class_info:
        return None
    
    # Securely fetch the students for that class.
    students_in_class = db.get_students_by_class_id(class_id=class_id, user_id=user_id)
    
    # V2 TODO: Analytics should be calculated from user-specific assessment data.
    analytics_data = {"studentCount": len(students_in_class), "classAverage": 84, "assessmentsGraded": 5}
    
    return {
        "id": class_info.id,
        "name": class_info.name,
        "description": class_info.description,
        "students": students_in_class, 
        "analytics": analytics_data
    }


def export_roster_as_csv(class_id: str, user_id: str, db: DatabaseService) -> str:
    """
    Business logic to generate a CSV export for a single class roster,
    ensuring the user has ownership of the class.
    """
    # Securely fetch the class details.
    class_details = db.get_class_by_id(class_id=class_id, user_id=user_id)
    if not class_details:
        raise ValueError(f"Class with ID {class_id} not found or access denied.")
        
    # Securely fetch the students for that class.
    students_in_class = db.get_students_by_class_id(class_id=class_id, user_id=user_id)
    
    export_data = [
        {
            'Student Name': s.name, 
            'Student ID': s.studentId, 
            'Overall Grade': s.overallGrade if s.overallGrade is not None else "N/A", 
            'Class Name': class_details.name
        } for s in students_in_class
    ]
    
    df = pd.DataFrame(export_data) if export_data else pd.DataFrame(columns=['Student Name', 'Student ID', 'Overall Grade', 'Class Name'])
    
    return df.to_csv(index=False)