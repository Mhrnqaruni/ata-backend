# /app/models/student_model.py (FINAL, HARDENED, AND PERFECTED)

# --- Core Imports ---
from pydantic import BaseModel, Field
from typing import Optional

# --- Model Definitions ---

class StudentBase(BaseModel):
    """
    The base model for a Student. Contains fields common to create and read operations.
    """
    name: str = Field(..., min_length=2, description="The full name of the student.")
    studentId: str = Field(..., description="The official, user-provided ID number for the student.")

class StudentCreate(StudentBase):
    """The model used for creating a new student. Inherits all fields from the base."""
    pass

class StudentUpdate(BaseModel):
    """
    The model for updating a student. All fields are optional to allow for
    partial updates (e.g., changing only the name). This is a superior pattern
    for PATCH/PUT requests.
    """
    name: Optional[str] = Field(default=None, min_length=2)
    studentId: Optional[str] = Field(default=None)
    overallGrade: Optional[int] = Field(default=None)
    
    # --- [THE FINAL REFINEMENT IS HERE] ---
    # The missing performance_summary field has been added to make the update
    # model complete and consistent with the full Student model.
    performance_summary: Optional[str] = Field(default=None)
    # --- [END OF FINAL REFINEMENT] ---

class Student(StudentBase):
    """
    The full representation of a Student resource, as it is stored in the
    database and returned by the API.
    """
    id: str = Field(..., description="The unique, server-generated identifier for the student.")
    class_id: str = Field(..., description="The ID of the class this student belongs to.")

    # --- [THE CORE FIX & ENHANCEMENT] ---
    # The field is now a non-optional 'int' with a default value of 0.
    # This creates a strong contract, guaranteeing that a student object
    # from our API will always have an integer grade.
    overallGrade: int = Field(
        default=0,
        description="The student's current overall grade. Defaults to 0 for new students."
    )
    # ------------------------------------

    performance_summary: Optional[str] = Field(
        default=None,
        description="An AI-generated summary of the student's performance (V2 feature)."
    )

# NOTE: The circular import resolution logic (model_rebuild) is correctly
# handled in `class_model.py` and must NOT be present in this file.