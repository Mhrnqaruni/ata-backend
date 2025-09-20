# /ata-backend/app/db/models/class_student_models.py (MODIFIED AND APPROVED)

"""
This module defines the SQLAlchemy ORM models for the `Class` and `Student`
entities, which represent a teacher's class roster and the individual students
within it.
"""

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
# --- [CRITICAL MODIFICATION] ---
# Import the UUID type from SQLAlchemy's PostgreSQL dialects. This is necessary
# to ensure the `user_id` foreign key column has the exact same data type as
# the `User.id` primary key it points to.
from sqlalchemy.dialects.postgresql import UUID

from ..base_class import Base

class Class(Base):
    """
    SQLAlchemy model representing a class or course.

    This model is now linked to a User, establishing the core ownership
    for all roster-related data. A user owns a class, and a class contains students.
    """
    __tablename__ = "classes"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    
    # --- [CRITICAL MODIFICATION 1/2: THE PHYSICAL LINK] ---
    # This column creates the foreign key relationship to the `users` table.
    # - UUID(as_uuid=True): Ensures type compatibility with the User.id primary key.
    # - ForeignKey("users.id"): The database-level constraint.
    # - nullable=False: Guarantees every class has an owner.
    # - index=True: Optimizes database lookups for a user's classes.
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # --- [CRITICAL MODIFICATION 2/2: THE LOGICAL LINK] ---
    # This SQLAlchemy relationship allows for easy, object-oriented access
    # to the owning User object from a Class instance (e.g., `my_class.owner`).
    # `back_populates="classes"` creates a two-way link with the `classes`
    # relationship defined in the `user_model.py` file.
    owner = relationship("User", back_populates="classes")

    # This relationship remains unchanged. When a Class is deleted, all its
    # child Student records are also deleted due to the cascade option.
    students = relationship("Student", back_populates="class_", cascade="all, delete-orphan")


# --- [NO MODIFICATIONS REQUIRED FOR STUDENT MODEL] ---
# The Student model does not need a direct link to the user. Its ownership is
# correctly inferred through its parent Class.
class Student(Base):
    """
    SQLAlchemy model representing a single student within a Class.
    """
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    studentId = Column(String, unique=True, index=True, nullable=False)
    
    overallGrade = Column(Integer, nullable=True) 
    performance_summary = Column(String, nullable=True)
    
    # This foreign key correctly links a Student to its parent Class.
    class_id = Column(String, ForeignKey("classes.id"), nullable=False)
    
    # This relationship correctly links a Student back to its parent Class object.
    class_ = relationship("Class", back_populates="students")