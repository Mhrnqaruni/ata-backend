# /ata-backend/app/db/models/assessment_models.py (MODIFIED AND APPROVED)

"""
This module defines the SQLAlchemy ORM models for the `Assessment` and `Result`
entities, which represent grading jobs and their individual outcomes, respectively.
"""

from sqlalchemy import Column, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# --- [CRITICAL MODIFICATION] ---
# Import the UUID type from SQLAlchemy's PostgreSQL dialects. This is necessary
# to ensure the `user_id` foreign key column has the exact same data type as
# the `User.id` primary key it points to.
from sqlalchemy.dialects.postgresql import UUID

from ..base_class import Base

class Assessment(Base):
    """
    SQLAlchemy model representing a top-level assessment (grading job).

    This model is now linked to a User, establishing the core ownership
    for the entire assessment feature.
    """
    id = Column(String, primary_key=True, index=True)
    status = Column(String, index=True, nullable=False)
    config = Column(JSON, nullable=False)
    answer_sheet_paths = Column(JSON, nullable=True)
    ai_summary = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # --- [CRITICAL MODIFICATION 1/2: THE PHYSICAL LINK] ---
    # This column creates the foreign key relationship to the `users` table.
    # - UUID(as_uuid=True): Ensures type compatibility with the User.id primary key.
    # - ForeignKey("users.id"): The database-level constraint.
    # - nullable=False: Guarantees every assessment has an owner.
    # - index=True: Optimizes database lookups for a user's assessments.
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # --- [CRITICAL MODIFICATION 2/2: THE LOGICAL LINK] ---
    # This SQLAlchemy relationship allows for easy, object-oriented access
    # to the owning User object from an Assessment instance (e.g., `my_assessment.owner`).
    # `back_populates="assessments"` creates a two-way link with the `assessments`
    # relationship defined in the `user_model.py` file.
    owner = relationship("User", back_populates="assessments")

    # This relationship remains unchanged. When an Assessment is deleted, all its
    # child Result records are also deleted due to the cascade option.
    results = relationship("Result", back_populates="assessment", cascade="all, delete-orphan")


# --- [NO MODIFICATIONS REQUIRED FOR RESULT MODEL] ---
# The Result model does not need a direct link to the user. Its ownership is
# inferred through its parent Assessment. This is a cleaner and more robust
# data model, as it avoids redundant data.
class Result(Base):
    """
    SQLAlchemy model representing the grade and feedback for a single question
    for a single student within an Assessment.
    
    Now supports multi-model AI grading with consensus tracking.
    """
    id = Column(String, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("assessments.id"), nullable=False)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    question_id = Column(String, nullable=False)
    
    # Final consensus grade and feedback
    grade = Column(Float, nullable=True)
    feedback = Column(String, nullable=True)
    extractedAnswer = Column(String, nullable=True)
    status = Column(String, nullable=False, default='pending')
    report_token = Column(String, unique=True, index=True, nullable=True)
    answer_sheet_path = Column(String, nullable=True)
    content_type = Column(String, nullable=True)
    
    # New fields for multi-model AI grading
    ai_responses = Column(JSON, nullable=True)  # Array of all 3 AI responses
    consensus_achieved = Column(String, nullable=True)  # "full", "majority", or "none"
    teacher_override = Column(JSON, nullable=True)  # Teacher's manual grade/feedback if any
    
    # Relationships remain unchanged.
    assessment = relationship("Assessment", back_populates="results")
    student = relationship("Student")