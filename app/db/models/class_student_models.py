# /ata-backend/app/db/models/class_student_models.py

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from ..base_class import Base

class Class(Base):
    __tablename__ = "classes"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    
    # This creates the relationship: a Class can have many Students.
    students = relationship("Student", back_populates="class_")

class Student(Base):
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    studentId = Column(String, unique=True, index=True, nullable=False)
    
    # The default for overallGrade is now a proper number (or NULL), not "N/A".
    overallGrade = Column(Integer, nullable=True) 
    performance_summary = Column(String, nullable=True)
    
    # This defines the foreign key relationship.
    class_id = Column(String, ForeignKey("classes.id"))
    class_ = relationship("Class", back_populates="students")