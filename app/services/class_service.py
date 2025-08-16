# /app/services/class_service.py (FINAL, CORRECTED, SQL-COMPATIBLE VERSION)

import pandas as pd
from typing import List, Dict, Optional
from fastapi import UploadFile

from ..models import class_model, student_model
from .database_service import DatabaseService

# Import all specialist functions from the new helper modules
from .class_helpers import roster_ingestion, crud

# --- FACADE METHODS ---
# This facade re-exports all the functions from the helper modules.
# NO CHANGES NEEDED IN THIS SECTION.
def create_class(class_data: class_model.ClassCreate, db: DatabaseService):
    return crud.create_class(class_data, db)

def update_class(class_id: str, class_update: class_model.ClassCreate, db: DatabaseService):
    return crud.update_class(class_id, class_update, db)

def delete_class_by_id(class_id: str, db: DatabaseService) -> bool:
    return crud.delete_class_by_id(class_id, db)

def add_student_to_class(class_id: str, student_data: student_model.StudentCreate, db: DatabaseService):
    return crud.add_student_to_class(class_id, student_data, db)

def update_student(student_id: str, student_update: student_model.StudentUpdate, db: DatabaseService):
    return crud.update_student(student_id, student_update, db)

def delete_student_from_class(class_id: str, student_id: str, db: DatabaseService) -> bool:
    return db.delete_student(student_id=student_id, class_id=class_id)

async def create_class_from_upload(name: str, file: UploadFile, db: DatabaseService):
    return await roster_ingestion.create_class_from_upload(name, file, db)

# --- DATA ASSEMBLY & EXPORT LOGIC (COMPLETELY REWRITTEN) ---

def get_all_classes_with_summary(user_id: str, db: DatabaseService) -> List[Dict]:
    """Business logic to retrieve all classes and enrich them with student counts."""
    all_classes = db.get_all_classes() # Returns a list of Class objects
    if not all_classes:
        return []

    students_df = db.get_students_as_dataframe(user_id=user_id)
    
    student_counts = {}
    if not students_df.empty:
        student_counts = students_df.groupby('class_id').size().to_dict()

    # --- [THE FIX IS HERE] ---
    summary_list = []
    for cls in all_classes:
        # Manually construct a dictionary for the response model
        summary_data = {
            "id": cls.id,
            "name": cls.name,
            "description": cls.description,
            "studentCount": student_counts.get(cls.id, 0)
        }
        summary_list.append(summary_data)
    return summary_list
    # --- [END OF FIX] ---

def get_class_details_by_id(class_id: str, db: DatabaseService) -> Optional[Dict]:
    """Business logic to assemble the full details for the Class Details page."""
    class_info = db.get_class_by_id(class_id) # This is now a Class object
    if not class_info:
        return None
    
    students_in_class = db.get_students_by_class_id(class_id) # List of Student objects
    
    # V2 TODO: Replace mock analytics with real data aggregation.
    analytics_data = {"studentCount": len(students_in_class), "classAverage": 84, "assessmentsGraded": 5}
    
    # --- [THE FIX IS HERE] ---
    # The ClassDetails Pydantic model (with from_attributes=True) will handle the conversion.
    # We just need to assemble the final dictionary with the correct keys.
    return {
        "id": class_info.id,
        "name": class_info.name,
        "description": class_info.description,
        "students": students_in_class, 
        "analytics": analytics_data
    }
    # --- [END OF FIX] ---

def export_roster_as_csv(class_id: str, db: DatabaseService) -> str:
    """Business logic to generate a CSV export for a single class roster."""
    class_details = db.get_class_by_id(class_id) # Class object
    if not class_details:
        raise ValueError(f"Class with ID {class_id} not found for export.")
        
    students_in_class = db.get_students_by_class_id(class_id) # List of Student objects
    
    # --- [THE FIX IS HERE] ---
    # Build the list of dictionaries using attribute access
    export_data = [
        {
            'Student Name': s.name, 
            'Student ID': s.studentId, 
            'Overall Grade': s.overallGrade if s.overallGrade is not None else "N/A", 
            'Class Name': class_details.name
        } for s in students_in_class
    ]
    # --- [END OF FIX] ---
    
    df = pd.DataFrame(export_data) if export_data else pd.DataFrame(columns=['Student Name', 'Student ID', 'Overall Grade', 'Class Name'])
    
    return df.to_csv(index=False)