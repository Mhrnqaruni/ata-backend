# /ata-backend/app/db/models/assessment_models.py

from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base_class import Base

class Assessment(Base):
    id = Column(String, primary_key=True, index=True)
    status = Column(String, index=True, nullable=False)
    config = Column(JSON, nullable=False)
    answer_sheet_paths = Column(JSON, nullable=True)
    ai_summary = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to Results
    results = relationship("Result", back_populates="assessment", cascade="all, delete-orphan")

class Result(Base):
    id = Column(String, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("assessments.id"), nullable=False)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    question_id = Column(String, nullable=False)
    
    grade = Column(Float, nullable=True) # Using Float for grades
    feedback = Column(String, nullable=True)
    extractedAnswer = Column(String, nullable=True)
    status = Column(String, nullable=False, default='pending')
    report_token = Column(String, unique=True, index=True, nullable=True)
    answer_sheet_path = Column(String, nullable=True)
    content_type = Column(String, nullable=True)
    
    # Relationships
    assessment = relationship("Assessment", back_populates="results")
    student = relationship("Student") # A simple one-way relationship is fine here