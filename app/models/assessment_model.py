# /app/models/assessment_model.py (FINAL, WITH FLEXIBLE RUBRIC VALIDATION)

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Union, Any
from enum import Enum
import uuid

# --- [Core Enumerations - Unchanged] ---
class JobStatus(str, Enum):
    QUEUED = "Queued"; PROCESSING = "Processing"; SUMMARIZING = "Summarizing"
    PENDING_REVIEW = "Pending Review"; COMPLETED = "Completed"; FAILED = "Failed"
    
class ScoringMethod(str, Enum):
    PER_QUESTION = "per_question"; PER_SECTION = "per_section"; TOTAL_SCORE = "total_score"

class GradingMode(str, Enum):
    ANSWER_KEY_PROVIDED = "answer_key_provided"
    AI_AUTO_GRADE = "ai_auto_grade"
    LIBRARY = "library"

# --- [V1 & V2 API Contract Models - THE FIX IS HERE] ---

class QuestionConfig(BaseModel):
    """The V1 model for a single question and its rubric."""
    id: str = Field(default_factory=lambda: f"q_{uuid.uuid4().hex[:8]}")
    text: str = Field(..., min_length=1)
    
    # --- [THE FIX] ---
    # The 'min_length=1' constraint has been removed.
    # This allows the rubric field to be an empty string (""), which is a valid
    # real-world scenario for simple questions. The field is still required,
    # so the AI must provide the key, but its value can now be empty.
    rubric: str = Field(..., description="The specific grading rubric for this question. Can be an empty string.")
    # --- [END OF FIX] ---
    
    maxScore: int = Field(default=10, gt=0)


class AssessmentConfig(BaseModel):
    assessmentName: str
    classId: str
    questions: List[QuestionConfig] = Field(..., min_length=1)
    includeImprovementTips: bool = Field(default=False)

    @field_validator('questions')
    @classmethod
    def questions_must_not_be_empty(cls, v):
        if not v: raise ValueError('Assessment must have at least one question.')
        return v

class QuestionConfigV2(QuestionConfig):
    """A V2 Question model that is now more flexible to handle AI output."""
    # This model inherits the now-fixed QuestionConfig, so it gets the fix automatically.
    
    # We also make maxScore optional, as the previous error log showed the AI
    # sometimes returns null for this. The teacher can set a default in the review UI.
    maxScore: Optional[int] = Field(None, gt=0)
    
    answer: Optional[Union[str, Dict[str, Any]]] = Field(None, description="The correct answer, which can be a string or a structured object.")


class SectionConfigV2(BaseModel):
    # ... (This model is unchanged)
    id: str = Field(default_factory=lambda: f"sec_{uuid.uuid4().hex[:8]}")
    title: str = Field(default="Main Section")
    total_score: Optional[int] = Field(None, gt=0)
    questions: List[QuestionConfigV2] = Field(..., min_length=1)

class AssessmentConfigV2(BaseModel):
    # ... (This model is unchanged)
    assessmentName: str
    classId: str
    scoringMethod: ScoringMethod
    totalScore: Optional[int] = Field(None, gt=0)
    sections: List[SectionConfigV2] = Field(..., min_length=1)
    includeImprovementTips: bool = Field(default=False)
    gradingMode: GradingMode = Field(default=GradingMode.ANSWER_KEY_PROVIDED)
    librarySource: Optional[str] = Field(None)


# --- [Shared & Legacy Models - Unchanged] ---
class AssessmentJobResponse(BaseModel):
    jobId: str; status: JobStatus; message: str

class StudentForGrading(BaseModel):
    id: str; name: str; answerSheetPath: str

class GradingResult(BaseModel):
    grade: Optional[float] = None; feedback: Optional[str] = None
    extractedAnswer: Optional[str] = None; status: str

class Analytics(BaseModel):
    classAverage: float; medianGrade: float
    gradeDistribution: Dict[str, int]; performanceByQuestion: Dict[str, float]

class AssessmentResultsResponse(BaseModel):
    jobId: str; assessmentName: str; status: JobStatus
    config: AssessmentConfigV2
    students: List[StudentForGrading]
    results: Dict[str, Dict[str, GradingResult]]
    analytics: Optional[Analytics] = None
    aiSummary: Optional[str] = None

class AssessmentJobSummary(BaseModel):
    id: str; assessmentName: str; className: str
    createdAt: str; status: JobStatus
    progress: Optional[Dict[str, int]] = None

class AssessmentJobListResponse(BaseModel):
    assessments: List[AssessmentJobSummary]

class AssessmentConfigResponse(BaseModel):
    assessmentName: str
    questions: List[QuestionConfig]
    includeImprovementTips: bool