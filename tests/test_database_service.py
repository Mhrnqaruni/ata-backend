# /tests/test_database_service.py (CORRECTED WITH PROPER PATCH TARGETS)

import pytest
from unittest.mock import patch

# We import the CLASS itself, not the shared singleton instance.
from app.services.database_service import DatabaseService

@pytest.fixture
def db_service(tmp_path):
    """
    Creates a NEW, CLEAN DatabaseService instance for EACH test function,
    with its file I/O redirected to a temporary directory.
    """
    # The temporary directory setup is correct.
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir()

    # --- [THE DEFINITIVE FIX IS HERE] ---
    # We must patch the path constants WHERE THEY ARE USED by the repositories.
    # The patch targets are now the specific path variables in each module.
    with patch('app.services.database_helpers.class_student_repository.CLASSES_DB_PATH', str(test_data_dir / "classes.csv")), \
         patch('app.services.database_helpers.class_student_repository.STUDENTS_DB_PATH', str(test_data_dir / "students.csv")), \
         patch('app.services.database_helpers.assessment_repository.ASSESSMENTS_DB_PATH', str(test_data_dir / "assessments.csv")), \
         patch('app.services.database_helpers.assessment_repository.RESULTS_DB_PATH', str(test_data_dir / "results.csv")), \
         patch('app.services.database_service.GENERATIONS_DB_PATH', str(test_data_dir / "generations.csv")):
        
        # Now, when we create a fresh service instance, each of its repositories
        # will be initialized using these temporarily patched paths.
        service = DatabaseService()
        yield service
    # --- [END OF DEFINITIVE FIX] ---


def test_add_and_get_class(db_service):
    """
    Tests that a class can be added and then retrieved successfully.
    """
    class_record = {"id": "cls_test_123", "name": "Test History Class", "description": "A class for testing."}
    db_service.add_class(class_record)
    retrieved_class = db_service.get_class_by_id("cls_test_123")
    assert retrieved_class is not None
    assert retrieved_class["name"] == "Test History Class"

def test_get_non_existent_class(db_service):
    """Tests that getting a non-existent class returns None from an empty database."""
    retrieved_class = db_service.get_class_by_id("cls_no_exist")
    assert retrieved_class is None

def test_get_all_classes(db_service):
    """
    Tests that get_all_classes correctly returns ONLY the classes added in this test.
    """
    # Arrange: This test now starts with a completely empty, temporary directory.
    class1 = {"id": "cls_1", "name": "Class 1", "description": "Desc 1"}
    class2 = {"id": "cls_2", "name": "Class 2", "description": "Desc 2"}
    db_service.add_class(class1)
    db_service.add_class(class2)

    # Act
    all_classes = db_service.get_all_classes()

    # Assert
    assert isinstance(all_classes, list)
    # The assertion will now pass because the list will contain exactly 2 items.
    assert len(all_classes) == 2
    assert all_classes[0]['name'] == 'Class 1'
    assert all_classes[1]['name'] == 'Class 2'