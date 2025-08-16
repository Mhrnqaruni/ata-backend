# /ata-backend/app/db/base.py (FINAL, COMPLETE VERSION)

# This file acts as a central registry for all our SQLAlchemy models.
# By importing them all here, we ensure that the Base class knows about them
# when Alembic runs its auto-generation scan.

# Import the Base class that all models inherit from.
from .base_class import Base

# Import all of our model classes from their respective files.
from .models.class_student_models import Class, Student
from .models.assessment_models import Assessment, Result
from .models.chat_models import ChatSession, ChatMessage
from .models.generation_models import Generation