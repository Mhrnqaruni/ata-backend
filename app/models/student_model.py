# /ata-backend/app/models/student_model.py (CORRECTED WITH Pydantic V2 CONFIG)

# --- Core Imports ---
from pydantic import BaseModel, Field, ConfigDict
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
    partial updates.
    """
    # --- [THE FIX IS HERE] ---
    model_config = ConfigDict(from_attributes=True)
    # --- [END OF FIX] ---

    name: Optional[str] = Field(default=None, min_length=2)
    studentId: Optional[str] = Field(default=None)
    overallGrade: Optional[int] = Field(default=None)
    performance_summary: Optional[str] = Field(default=None)

class Student(StudentBase):
    """
    The full representation of a Student resource, as it is stored in the
    database and returned by the API.
    """
    # --- [THE FIX IS HERE] ---
    model_config = ConfigDict(from_attributes=True)
    # --- [END OF FIX] ---

    id: str = Field(..., description="The unique, server-generated identifier for the student.")
    class_id: str = Field(..., description="The ID of the class this student belongs to.")
    overallGrade: int = Field(
        default=0,
        description="The student's current overall grade. Defaults to 0 for new students."
    )
    performance_summary: Optional[str] = Field(
        default=None,
        description="An AI-generated summary of the student's performance (V2 feature)."
    )