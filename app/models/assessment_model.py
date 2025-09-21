# /ata-backend/app/models/assessment_model.py (DEFINITIVELY CORRECTED)

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Union, Any
from enum import Enum
import uuid

# --- Core Enumerations ---
class JobStatus(str, Enum):
    QUEUED = "Queued"; PROCESSING = "Processing"; SUMMARIZING = "Summarizing"
    PENDING_REVIEW = "Pending Review"; COMPLETED = "Completed"; FAILED = "Failed"
    
class ScoringMethod(str, Enum):
    PER_QUESTION = "per_question"; PER_SECTION = "per_section"; TOTAL_SCORE = "total_score"

class GradingMode(str, Enum):
    ANSWER_KEY_PROVIDED = "answer_key_provided"
    AI_AUTO_GRADE = "ai_auto_grade"
    LIBRARY = "library"

class ResultStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"  
    AI_GRADED = "ai_graded"
    PENDING_REVIEW = "pending_review"
    TEACHER_GRADED = "teacher_graded"
    FAILED = "failed"

class ConsensusType(str, Enum):
    FULL = "full"         # All 3 AI models agree
    MAJORITY = "majority" # 2 out of 3 AI models agree
    NONE = "none"         # All 3 AI models disagree

# --- API Contract Models ---

class QuestionConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: f"q_{uuid.uuid4().hex[:8]}")
    text: str = Field(..., min_length=1)
    rubric: str = Field(..., description="The specific grading rubric for this question. Can be an empty string.")
    maxScore: int = Field(default=10, gt=0)

class AssessmentConfig(BaseModel):
    # This model is for incoming data, so it doesn't strictly need from_attributes,
    # but adding it is harmless and good for consistency.
    model_config = ConfigDict(from_attributes=True)
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
    model_config = ConfigDict(from_attributes=True)
    maxScore: Optional[int] = Field(None, gt=0)
    answer: Optional[Union[str, Dict[str, Any]]] = Field(None, description="The correct answer, which can be a string or a structured object.")

class SectionConfigV2(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: f"sec_{uuid.uuid4().hex[:8]}")
    title: str = Field(default="Main Section")
    total_score: Optional[int] = Field(None, gt=0)
    questions: List[QuestionConfigV2] = Field(..., min_length=1)

class AssessmentConfigV2(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    assessmentName: str
    classId: str
    scoringMethod: ScoringMethod
    totalScore: Optional[int] = Field(None, gt=0)
    sections: List[SectionConfigV2] = Field(..., min_length=1)
    includeImprovementTips: bool = Field(default=False)
    gradingMode: GradingMode = Field(default=GradingMode.ANSWER_KEY_PROVIDED)
    librarySource: Optional[str] = Field(None)

class AssessmentJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    jobId: str; status: JobStatus; message: str

class StudentForGrading(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; name: str; answerSheetPath: str

class GradingResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    grade: Optional[float] = None; feedback: Optional[str] = None
    extractedAnswer: Optional[str] = None; status: str

# New models for multi-AI grading support
class AIModelResponse(BaseModel):
    """Response from a single AI model for a single question."""
    model_config = ConfigDict(from_attributes=True)
    model_id: str  # Identifier for which AI model (e.g., "gemini_1", "gemini_2", "gemini_3")
    grade: Optional[float] = None
    feedback: Optional[str] = None
    raw_response: Optional[str] = None  # Store the raw JSON response

class MultiAIGradingResult(BaseModel):
    """Extended grading result with multi-AI model responses and consensus data."""
    model_config = ConfigDict(from_attributes=True)
    grade: Optional[float] = None
    feedback: Optional[str] = None
    extractedAnswer: Optional[str] = None
    status: ResultStatus
    ai_responses: Optional[List[AIModelResponse]] = None
    consensus_achieved: Optional[ConsensusType] = None
    teacher_override: Optional[Dict] = None

class TeacherOverride(BaseModel):
    """Model for teacher manual grade/feedback override."""
    model_config = ConfigDict(from_attributes=True)
    grade: Optional[float] = None
    feedback: Optional[str] = None
    timestamp: Optional[str] = None
    
class PendingReviewRequest(BaseModel):
    """Request model for teacher review of pending questions."""  
    model_config = ConfigDict(from_attributes=True)
    grade: float
    feedback: str

class Analytics(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    classAverage: float; medianGrade: float
    gradeDistribution: Dict[str, int]; performanceByQuestion: Dict[str, float]

class AssessmentResultsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    jobId: str; assessmentName: str; status: JobStatus
    config: AssessmentConfigV2
    students: List[StudentForGrading]
    results: Dict[str, Dict[str, GradingResult]]
    analytics: Optional[Analytics] = None
    aiSummary: Optional[str] = None

class CategorizedResultsResponse(BaseModel):
    """Response model that separates AI-graded from pending review results."""
    model_config = ConfigDict(from_attributes=True)
    jobId: str
    assessmentName: str
    status: JobStatus
    config: AssessmentConfigV2
    ai_graded_students: List[Dict]  # Students with all questions AI-graded
    pending_review_students: List[Dict]  # Students with questions needing manual review
    analytics: Optional[Analytics] = None
    aiSummary: Optional[str] = None

class ReviewPageResponse(BaseModel):
    """Response model for the teacher review page."""
    model_config = ConfigDict(from_attributes=True)
    jobId: str
    assessmentName: str
    student: Dict
    questions: List[Dict]  # Question details with student answers and AI responses
    pending_questions: List[Dict]  # Questions that need manual review (at top)
    ai_graded_questions: List[Dict]  # Questions already graded by AI

class AssessmentJobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; assessmentName: str; className: str
    createdAt: str; status: JobStatus
    progress: Optional[Dict[str, int]] = None

class AssessmentJobListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    assessments: List[AssessmentJobSummary]

class AssessmentConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    assessmentName: str
    questions: List[QuestionConfig]
    includeImprovementTips: bool