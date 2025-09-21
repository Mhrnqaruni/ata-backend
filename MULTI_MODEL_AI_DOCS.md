# Multi-Model AI Grading System Documentation

## Overview

This implementation upgrades the assessment system from using a single Gemini AI model to using **3 concurrent Gemini AI models** with **consensus-based evaluation** and comprehensive **teacher review functionality**.

## System Architecture

### 1. Multi-Model AI Grading Pipeline

Instead of calling one AI model:
```python
# OLD: Single model call
ai_response = await gemini_service.generate_multimodal_response(prompt, images)
```

The system now calls 3 models concurrently:
```python
# NEW: 3 concurrent model calls
multi_ai_responses = await generate_multi_model_responses(prompt, images)
```

### 2. Consensus Evaluation

For each question, the system evaluates consensus among the 3 AI models:

- **Full Consensus**: All 3 models give the same grade → Status: `ai_graded`
- **Majority Consensus**: 2 out of 3 models agree → Status: `ai_graded`  
- **No Consensus**: All 3 models give different grades → Status: `pending_review`

### 3. Result Categorization

Students are now categorized into two groups:

1. **AI-Graded Students**: All questions have consensus (ai_graded)
2. **Pending Review Students**: At least one question needs manual review (pending_review)

## Database Schema Changes

### New Fields in Result Model

```python
class Result(Base):
    # ... existing fields ...
    
    # New fields for multi-model AI grading
    ai_responses = Column(JSON, nullable=True)      # All 3 AI responses
    consensus_achieved = Column(String, nullable=True)  # "full", "majority", or "none"
    teacher_override = Column(JSON, nullable=True)  # Teacher's manual changes
```

### Migration

```sql
-- Added in migration: add_multi_model_ai_grading_fields.py
ALTER TABLE results ADD COLUMN ai_responses JSON;
ALTER TABLE results ADD COLUMN consensus_achieved VARCHAR;  
ALTER TABLE results ADD COLUMN teacher_override JSON;
```

## New API Endpoints

### 1. Categorized Results
```http
GET /assessments/{job_id}/results/categorized
```
Returns results separated into AI-graded vs pending review students.

**Response:**
```json
{
  "jobId": "job_123",
  "assessmentName": "Math Quiz", 
  "ai_graded_students": [...],
  "pending_review_students": [...],
  "analytics": {...}
}
```

### 2. Teacher Review Page
```http
GET /assessments/{job_id}/review/{student_id}
```
Returns data for teacher review interface.

**Response:**
```json
{
  "jobId": "job_123",
  "student": {"id": "student_456", "name": "John Doe"},
  "pending_questions": [...],      // Questions needing manual review (shown at top)
  "ai_graded_questions": [...]     // Questions already graded by AI (editable)
}
```

### 3. Submit Pending Review
```http
PATCH /assessments/{job_id}/review/{student_id}/{question_id}/pending
```
Teacher submits manual grade/feedback for pending questions.

**Request Body:**
```json
{
  "grade": 8.5,
  "feedback": "Good work, but missed key concept X"
}
```

### 4. Override AI Grade
```http
PATCH /assessments/{job_id}/review/{student_id}/{question_id}/override
```
Teacher overrides an AI-graded question.

**Request Body:**
```json
{
  "grade": 7.0,
  "feedback": "Adjusted for partial credit",
  "timestamp": "2024-09-21T10:30:00Z"
}
```

### 5. Regenerate Reports
```http
POST /assessments/{job_id}/regenerate-reports
```
Regenerates student reports after teacher makes changes.

## How It Works: Step-by-Step

### 1. Assessment Processing

1. **File Upload**: Teacher uploads question file, answer key, and student answer sheets
2. **Multi-Model Grading**: System calls 3 Gemini models concurrently for each student
3. **Consensus Evaluation**: For each question, system evaluates if AI models agree
4. **Result Storage**: Saves all AI responses + consensus status to database

### 2. Results Review

1. **Categorized Display**: Results page shows two sections:
   - **AI-Graded Students**: Fully processed, ready for reports
   - **Pending Review Students**: Need teacher attention

### 3. Teacher Review Workflow

1. **Review Page**: Teacher clicks on pending student to see review interface
2. **Pending Questions**: Questions with no AI consensus shown at top
3. **Manual Grading**: Teacher provides grade/feedback for pending questions
4. **AI Grade Review**: Teacher can also edit any AI-graded questions
5. **Save Changes**: Changes saved to database with teacher override tracking

### 4. Report Generation

1. **Updated Reports**: System generates reports using final grades (AI + teacher overrides)
2. **Audit Trail**: AI responses and teacher changes are preserved for transparency

## Code Structure

### Core Files

```
app/
├── services/
│   ├── multi_model_ai.py          # Concurrent AI model calls
│   ├── ai_consensus.py            # Consensus evaluation logic  
│   ├── assessment_service.py      # Enhanced with review methods
│   └── assessment_helpers/
│       └── grading_pipeline.py    # Updated for multi-model
├── models/
│   └── assessment_model.py        # New response models & enums
├── routers/
│   └── assessments_router.py      # New teacher review endpoints  
└── db/models/
    └── assessment_models.py       # Enhanced Result model
```

### Key Classes & Methods

**Multi-Model AI:**
```python
async def generate_multi_model_responses(prompt: str, images: List[Image.Image]) -> List[Dict]
```

**Consensus Evaluation:**
```python
def evaluate_consensus(ai_responses: List[Dict], question_id: str) -> Tuple[float, str, ConsensusType, List[AIModelResponse]]
```

**Service Methods:**
```python
def get_categorized_job_results(job_id: str, user_id: str) -> Dict
def get_student_review_data(job_id: str, student_id: str, user_id: str) -> Dict
def submit_teacher_review(job_id: str, student_id: str, question_id: str, grade: float, feedback: str, user_id: str)
```

## Benefits

1. **Higher Accuracy**: 3 AI models reduce single-model bias and errors
2. **Quality Assurance**: Questions with no consensus flagged for human review
3. **Transparency**: All AI responses stored for audit and analysis
4. **Teacher Control**: Full override capability with change tracking
5. **Efficiency**: Concurrent processing maintains performance
6. **Backward Compatibility**: Existing single-model methods preserved

## Performance Considerations

- **Concurrent Execution**: 3 AI calls run in parallel, not sequentially
- **Graceful Degradation**: If 1-2 models fail, system still works with remaining responses
- **Database Optimization**: Indexed queries for user-scoped data access
- **Minimal UI Changes**: Existing interfaces enhanced, not replaced

## Security

- All endpoints require user authentication
- User-scoped database queries prevent data leakage  
- Teacher overrides tracked with timestamps
- Original AI responses preserved for audit trail