# Frontend Integration Examples for Multi-Model AI Grading

## 1. Display Categorized Results

```javascript
// Fetch categorized results instead of regular results
async function fetchCategorizedResults(jobId) {
  const response = await fetch(`/api/assessments/${jobId}/results/categorized`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await response.json();
  
  return {
    aiGradedStudents: data.ai_graded_students,
    pendingReviewStudents: data.pending_review_students,
    analytics: data.analytics
  };
}

// Display in UI with two sections
function renderResultsPage(data) {
  return (
    <div className="results-page">
      <section className="ai-graded-section">
        <h2>✅ AI-Graded Students ({data.aiGradedStudents.length})</h2>
        <p>These students are fully processed and ready for report generation.</p>
        <StudentList students={data.aiGradedStudents} />
      </section>
      
      <section className="pending-review-section">
        <h2>⚠️ Pending Review ({data.pendingReviewStudents.length})</h2>
        <p>These students have questions that need manual teacher review.</p>
        <StudentList 
          students={data.pendingReviewStudents} 
          showReviewButton={true} 
        />
      </section>
    </div>
  );
}
```

## 2. Teacher Review Page

```javascript
// Fetch review data for a specific student
async function fetchStudentReviewData(jobId, studentId) {
  const response = await fetch(`/api/assessments/${jobId}/review/${studentId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await response.json();
}

// Render teacher review interface
function ReviewPage({ jobId, studentId }) {
  const [reviewData, setReviewData] = useState(null);
  
  useEffect(() => {
    fetchStudentReviewData(jobId, studentId).then(setReviewData);
  }, [jobId, studentId]);
  
  if (!reviewData) return <LoadingSpinner />;
  
  return (
    <div className="review-page">
      <h1>Review: {reviewData.student.name}</h1>
      
      {/* Pending questions at the top */}
      {reviewData.pending_questions.length > 0 && (
        <section className="pending-questions">
          <h2>🔴 Pending Manual Review ({reviewData.pending_questions.length})</h2>
          <p>These questions need your manual grading:</p>
          {reviewData.pending_questions.map(q => (
            <PendingQuestionCard 
              key={q.question.id}
              question={q.question}
              studentAnswer={q.student_answer}
              onSubmit={(grade, feedback) => submitPendingReview(jobId, studentId, q.question.id, grade, feedback)}
            />
          ))}
        </section>
      )}
      
      {/* AI-graded questions (editable) */}
      <section className="ai-graded-questions">
        <h2>🤖 AI-Graded Questions (Editable)</h2>
        {reviewData.ai_graded_questions.map(q => (
          <AIGradedQuestionCard 
            key={q.question.id}
            question={q.question}
            result={q.result}
            onOverride={(grade, feedback) => saveTeacherOverride(jobId, studentId, q.question.id, grade, feedback)}
          />
        ))}
      </section>
    </div>
  );
}
```

## 3. Submit Pending Review

```javascript
// Submit teacher's manual grade for pending question
async function submitPendingReview(jobId, studentId, questionId, grade, feedback) {
  const response = await fetch(`/api/assessments/${jobId}/review/${studentId}/${questionId}/pending`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ grade, feedback })
  });
  
  if (response.ok) {
    // Show success message and update UI
    showSuccessMessage('Review submitted successfully!');
    // Refresh the review data or update state
  }
}

// Pending question component
function PendingQuestionCard({ question, studentAnswer, onSubmit }) {
  const [grade, setGrade] = useState('');
  const [feedback, setFeedback] = useState('');
  
  return (
    <div className="pending-question-card">
      <div className="question-content">
        <h3>Question: {question.text}</h3>
        <p><strong>Max Score:</strong> {question.maxScore}</p>
        <p><strong>Student Answer:</strong> {studentAnswer}</p>
      </div>
      
      <div className="grading-form">
        <label>
          Grade (out of {question.maxScore}):
          <input 
            type="number" 
            min="0" 
            max={question.maxScore} 
            step="0.5"
            value={grade}
            onChange={(e) => setGrade(e.target.value)}
          />
        </label>
        
        <label>
          Feedback:
          <textarea 
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Provide detailed feedback..."
          />
        </label>
        
        <button 
          onClick={() => onSubmit(parseFloat(grade), feedback)}
          disabled={!grade || !feedback}
        >
          Submit Review
        </button>
      </div>
    </div>
  );
}
```

## 4. Override AI Grade

```javascript
// Save teacher override for AI-graded question  
async function saveTeacherOverride(jobId, studentId, questionId, grade, feedback) {
  const response = await fetch(`/api/assessments/${jobId}/review/${studentId}/${questionId}/override`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ 
      grade, 
      feedback,
      timestamp: new Date().toISOString()
    })
  });
  
  if (response.ok) {
    showSuccessMessage('Override saved successfully!');
  }
}

// AI-graded question component (editable)
function AIGradedQuestionCard({ question, result, onOverride }) {
  const [isEditing, setIsEditing] = useState(false);
  const [grade, setGrade] = useState(result.grade);
  const [feedback, setFeedback] = useState(result.feedback);
  
  return (
    <div className="ai-graded-question-card">
      <div className="question-content">
        <h3>Question: {question.text}</h3>
        <p><strong>Student Answer:</strong> {result.extractedAnswer}</p>
      </div>
      
      <div className="ai-grading-info">
        <div className="consensus-badge">
          {result.consensus_achieved === 'full' && <span className="badge full">✅ Full AI Consensus</span>}
          {result.consensus_achieved === 'majority' && <span className="badge majority">🤖 Majority AI Consensus</span>}
        </div>
        
        {/* Show AI model responses */}
        {result.ai_responses && (
          <details className="ai-responses">
            <summary>View AI Model Responses</summary>
            {result.ai_responses.map(resp => (
              <div key={resp.model_id} className="ai-response">
                <strong>{resp.model_id}:</strong> Grade: {resp.grade}, Feedback: {resp.feedback}
              </div>
            ))}
          </details>
        )}
      </div>
      
      <div className="current-grade">
        {isEditing ? (
          <div className="edit-form">
            <label>
              Grade: 
              <input 
                type="number" 
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
              />
            </label>
            <label>
              Feedback:
              <textarea 
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
              />
            </label>
            <button onClick={() => {
              onOverride(parseFloat(grade), feedback);
              setIsEditing(false);
            }}>
              Save Override
            </button>
            <button onClick={() => setIsEditing(false)}>Cancel</button>
          </div>
        ) : (
          <div className="display-grade">
            <p><strong>Grade:</strong> {result.grade}/{question.maxScore}</p>
            <p><strong>Feedback:</strong> {result.feedback}</p>
            <button onClick={() => setIsEditing(true)}>Edit Grade</button>
          </div>
        )}
      </div>
    </div>
  );
}
```

## 5. Navigation & Workflow

```javascript
// Results page navigation
function StudentResultCard({ student, isPendingReview, jobId }) {
  const navigate = useNavigate();
  
  return (
    <div className={`student-card ${isPendingReview ? 'pending' : 'complete'}`}>
      <h3>{student.name}</h3>
      <div className="actions">
        {isPendingReview ? (
          <button 
            className="review-button"
            onClick={() => navigate(`/review/${jobId}/${student.id}`)}
          >
            Review Required
          </button>
        ) : (
          <>
            <button 
              className="view-button"
              onClick={() => navigate(`/review/${jobId}/${student.id}`)}
            >
              View/Edit Grades
            </button>
            <button 
              className="report-button"
              onClick={() => downloadReport(jobId, student.id)}
            >
              Download Report
            </button>
          </>
        )}
      </div>
    </div>
  );
}
```

## CSS Styling Examples

```css
/* Status badges */
.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.badge.full {
  background: #d4edda;
  color: #155724;
}

.badge.majority {
  background: #fff3cd;
  color: #856404;
}

/* Section styling */
.pending-review-section {
  border-left: 4px solid #ffc107;
  padding-left: 16px;
  margin-top: 20px;
}

.ai-graded-section {
  border-left: 4px solid #28a745;
  padding-left: 16px;
}

/* Cards */
.pending-question-card {
  border: 2px solid #ffc107;
  padding: 16px;
  margin: 12px 0;
  border-radius: 8px;
}

.ai-graded-question-card {
  border: 1px solid #dee2e6;
  padding: 16px;
  margin: 12px 0;
  border-radius: 8px;
}

.student-card.pending {
  border-left: 4px solid #ffc107;
}

.student-card.complete {
  border-left: 4px solid #28a745;
}
```