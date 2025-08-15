# /app/services/class_service.py (THE NEW, CORRECTED FACADE)

import pandas as pd
from typing import List, Dict, Optional
from fastapi import UploadFile

from ..models import class_model, student_model
from .database_service import DatabaseService

# Import all specialist functions from the new helper modules
from .class_helpers import roster_ingestion, crud

# --- FACADE METHODS ---
# This facade re-exports all the functions from the helper modules to maintain a single,
# stable entry point for the router.

# --- Re-exported from class_helpers.crud ---
def create_class(class_data: class_model.ClassCreate, db: DatabaseService) -> Dict:
    return crud.create_class(class_data, db)

def update_class(class_id: str, class_update: class_model.ClassCreate, db: DatabaseService) -> Optional[Dict]:
    return crud.update_class(class_id, class_update, db)

def delete_class_by_id(class_id: str, db: DatabaseService) -> bool:
    return crud.delete_class_by_id(class_id, db)

def add_student_to_class(class_id: str, student_data: student_model.StudentCreate, db: DatabaseService) -> Dict:
    return crud.add_student_to_class(class_id, student_data, db)

def update_student(student_id: str, student_update: student_model.StudentUpdate, db: DatabaseService) -> Optional[Dict]:
    return crud.update_student(student_id, student_update, db)

def delete_student_from_class(class_id: str, student_id: str, db: DatabaseService) -> bool:
    return db.delete_student(student_id=student_id, class_id=class_id)

# --- Re-exported from class_helpers.roster_ingestion ---
async def create_class_from_upload(name: str, file: UploadFile, db: DatabaseService) -> Dict:
    return await roster_ingestion.create_class_from_upload(name, file, db)

# --- Logic that remains in the main service (Data Assembly & Export) ---

# --- [THE FIX IS HERE] ---
def get_all_classes_with_summary(user_id: str, db: DatabaseService) -> List[Dict]:
    """Business logic to retrieve all classes and enrich them with student counts."""
    # The user_id is now accepted as a parameter.
    all_classes = db.get_all_classes() # This method doesn't need user_id yet for V1.
    
    # The user_id is now correctly passed to the database service call.
    students_df = db.get_students_as_dataframe(user_id=user_id)
    # --- [END OF FIX] ---

    if not all_classes: return []
    
    if students_df.empty:
        for cls in all_classes: cls['studentCount'] = 0
        return all_classes
        
    student_counts = students_df.groupby('class_id').size().to_dict()
    for cls in all_classes:
        cls['studentCount'] = student_counts.get(cls.get('id'), 0)
        
    return all_classes

def get_class_details_by_id(class_id: str, db: DatabaseService) -> Optional[Dict]:
    """Business logic to assemble the full details for the Class Details page."""
    class_info = db.get_class_by_id(class_id)
    if not class_info: return None
    
    students_in_class = db.get_students_by_class_id(class_id)
    for student in students_in_class:
        if 'overallGrade' not in student or pd.isna(student['overallGrade']):
            student['overallGrade'] = "N/A"
            
    # V2 TODO: Replace mock analytics with real data aggregation.
    analytics_data = {"studentCount": len(students_in_class), "classAverage": 84, "assessmentsGraded": 5}
    
    return {**class_info, "students": students_in_class, "analytics": analytics_data}

def export_roster_as_csv(class_id: str, db: DatabaseService) -> str:
    """Business logic to generate a CSV export for a single class roster."""
    class_details = db.get_class_by_id(class_id)
    if not class_details:
        raise ValueError(f"Class with ID {class_id} not found for export.")
        
    students_in_class = db.get_students_by_class_id(class_id)
    
    export_data = [
        {
            'Student Name': s.get('name'), 
            'Student ID': s.get('studentId'), 
            'Overall Grade': s.get('overallGrade', 'N/A'), 
            'Class Name': class_details.get('name')
        } for s in students_in_class
    ]
    
    df = pd.DataFrame(export_data) if export_data else pd.DataFrame(columns=['Student Name', 'Student ID', 'Overall Grade', 'Class Name'])
    
    return df.to_csv(index=False)