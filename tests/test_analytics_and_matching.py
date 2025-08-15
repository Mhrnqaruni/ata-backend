# /tests/test_analytics_and_matching.py (CORRECTED)

import pytest
from unittest.mock import MagicMock, AsyncMock, mock_open
import json

from app.services.assessment_helpers import analytics_and_matching
from app.models.assessment_model import AssessmentConfig, AssessmentConfigV2, QuestionConfig, SectionConfigV2

# --- Test Data Fixtures (Unchanged but confirmed correct) ---

@pytest.fixture
def mock_db_service():
    """Provides a mock of the DatabaseService for dependency injection."""
    return MagicMock()

@pytest.fixture
def v1_job_record():
    """Provides a mock database record for a V1 assessment job."""
    v1_config = AssessmentConfig(
        assessmentName="V1 History Test", classId="cls_v1",
        questions=[
            QuestionConfig(id="q1", text="Who was the first president?", rubric="Name the person.", maxScore=10),
            QuestionConfig(id="q2", text="What year was the declaration signed?", rubric="Provide the year.", maxScore=10)
        ]
    )
    return {"id": "job_v1_123", "status": "Completed", "config": v1_config.model_dump_json()}

@pytest.fixture
def mock_results_data():
    """Provides a list of mock result dictionaries for analytics testing."""
    return [
        {'student_id': 'stu_1', 'question_id': 'q_1', 'grade': '8'},
        {'student_id': 'stu_1', 'question_id': 'q_2', 'grade': '10'},
        {'student_id': 'stu_2', 'question_id': 'q_1', 'grade': '6'},
        {'student_id': 'stu_2', 'question_id': 'q_2', 'grade': '7'},
    ]

@pytest.fixture
def mock_v2_config_for_analytics():
    """Provides a valid V2 config object for analytics testing."""
    return AssessmentConfigV2.model_validate({
        "assessmentName": "Analytics Test", "classId": "cls_xyz", "scoringMethod": "per_question",
        "sections": [{"title": "Main Section", "questions": [
            {"id": "q_1", "text": "Q1", "rubric": "R1", "maxScore": 10},
            {"id": "q_2", "text": "Q2", "rubric": "R2", "maxScore": 10}
        ]}]
    })

# --- Unit Tests ---

def test_normalize_config_to_v2_from_v1_job(v1_job_record):
    """Tests that a V1 job config is correctly transformed into a V2 structure."""
    normalized_config = analytics_and_matching.normalize_config_to_v2(v1_job_record)
    assert isinstance(normalized_config, AssessmentConfigV2)
    assert len(normalized_config.sections) == 1
    assert normalized_config.sections[0].questions[0].text == "Who was the first president?"
    print("\n✅ SUCCESS: test_normalize_config_to_v2_from_v1_job passed.")

def test_calculate_analytics_success(mock_results_data, mock_v2_config_for_analytics):
    """Tests that the analytics calculations are correct."""
    analytics = analytics_and_matching.calculate_analytics(mock_results_data, mock_v2_config_for_analytics)
    assert analytics["classAverage"] == 77.5
    assert analytics["performanceByQuestion"]["q_1"] == 70.0
    print("\n✅ SUCCESS: test_calculate_analytics_success passed.")

# This test IS asynchronous, so we apply the marker directly to it.
@pytest.mark.asyncio
async def test_match_files_to_students(mocker, mock_db_service):
    """Tests that the file matching logic correctly calls the database on a match."""
    job_id = "job_match_test"
    mock_job_record = {
        "config": AssessmentConfig(assessmentName="Test", classId="cls_1", questions=[QuestionConfig(id='q1', text='t', rubric='r')]).model_dump_json(),
        "answer_sheet_paths": json.dumps([{"path": "/path/to/alex_paper.pdf", "contentType": "application/pdf"}])
    }
    mock_students = [{"id": "stu_alex_123", "name": "Alex Doe"}]
    
    # Configure our mock database to return the test data
    mock_db_service.get_assessment_job.return_value = mock_job_record
    mock_db_service.get_students_by_class_id.return_value = mock_students
    
    # Mock the external OCR service
    mocker.patch('app.services.ocr_service.extract_text_from_file', return_value="some text containing the name alex doe here")

    # --- [THE FIX IS HERE] ---
    # We must mock the built-in 'open' function to prevent a FileNotFoundError.
    # mock_open() simulates opening a file without actually touching the disk.
    mocker.patch("builtins.open", mock_open(read_data=b"fake file bytes"))
    # --- [END OF FIX] ---

    await analytics_and_matching.match_files_to_students(mock_db_service, job_id)

    # Assert that the database was correctly updated after the match was found
    mock_db_service.update_student_result_path.assert_called_once_with(
        job_id, "stu_alex_123", "/path/to/alex_paper.pdf", "application/pdf"
    )
    print("\n✅ SUCCESS: test_match_files_to_students passed.")