# /app/models/tool_model.py

# --- Core Imports ---
from pydantic import BaseModel, Field, AliasChoices
from typing import Dict, Any, List, Optional
from enum import Enum

# --- Enumerations for Tool Settings ---
class QuestionDifficulty(str, Enum):
    VERY_EASY = "very easy"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    VERY_HARD = "very hard"

class SlideStyle(str, Enum):
    INFORMATIVE = "informative"
    ENGAGING = "engaging"
    PROFESSIONAL = "professional"

class ToolId(str, Enum):
    QUESTION_GENERATOR = "question-generator"
    SLIDE_GENERATOR = "slide-generator"
    RUBRIC_GENERATOR = "rubric-generator"
    LESSON_PLAN_GENERATOR = "lesson-plan-generator"

# --- Models for the Question Generator ---
class QuestionTypeConfig(BaseModel):
    type: str
    label: str
    count: int
    difficulty: QuestionDifficulty

class QuestionGeneratorSettings(BaseModel):
    grade_level: str
    source_text: Optional[str] = None
    selected_chapter_paths: Optional[List[str]] = None
    question_configs: List[QuestionTypeConfig]

# --- Models for the Slide Generator ---
class SlideGeneratorSettings(BaseModel):
    grade_level: str
    source_text: Optional[str] = None
    selected_chapter_paths: Optional[List[str]] = None
    num_slides: int
    slide_style: SlideStyle
    include_speaker_notes: bool

# --- Models for the Rubric Generator (UPGRADED) ---
class RubricGeneratorSettings(BaseModel):
    grade_level: str
    
    # --- [CRITICAL FIX] ---
    # The orchestrator provides a generic 'source_text'. We tell Pydantic
    # that 'source_text' is a valid ALIAS for our specific 'assignment_text' field.
    assignment_text: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('assignment_text', 'source_text')
    )
    assignment_chapter_paths: Optional[List[str]] = None
    
    guidance_text: Optional[str] = None
    guidance_chapter_paths: Optional[List[str]] = None

    criteria: List[str] = Field(..., min_length=2)
    levels: List[str] = Field(..., min_length=2)

# --- Universal Tool Models ---
class ToolGenerationRequest(BaseModel):
    tool_id: ToolId
    settings: Dict[str, Any]

class ToolGenerationResponse(BaseModel):
    generation_id: str
    tool_id: ToolId
    content: str