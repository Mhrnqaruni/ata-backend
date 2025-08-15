# /app/services/dashboard_service.py

# --- Core Imports ---
# Import the Pydantic model to ensure our output matches the data contract.
from ..models.dashboard_model import DashboardSummary
# Import the DatabaseService to interact with our data layer.
from .database_service import DatabaseService

# --- Core Public Function ---

def get_summary_data(db: DatabaseService) -> DashboardSummary:
    """
    Calculates the dashboard summary statistics by retrieving data from the
    database service and performing aggregations. This is the "thick" service
    layer that contains the business logic.

    Args:
        db: An instance of the DatabaseService, provided by dependency injection.
        
    Returns:
        A DashboardSummary Pydantic object containing the calculated counts.
    """
    try:
        # 1. DELEGATE DATA RETRIEVAL: Get all raw data from the data access layer.
        all_classes = db.get_all_classes()
        all_students = db.get_all_students()

        # 2. PERFORM BUSINESS LOGIC: Calculate the required statistics.
        class_count = len(all_classes)
        student_count = len(all_students)

        # 3. CONSTRUCT & VALIDATE: Return the data structured according to our
        #    Pydantic model. This ensures the data sent to the router is always
        #    in the correct, contracted shape.
        return DashboardSummary(
            classCount=class_count,
            studentCount=student_count
        )
    except Exception as e:
        # In a real app, we would add structured logging here.
        print(f"ERROR calculating summary data: {e}")
        # Re-raise the exception to be handled as a 500 error in the router layer.
        raise