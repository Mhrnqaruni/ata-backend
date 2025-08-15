# /app/models/dashboard_model.py

# --- Core Imports ---
# Import the necessary components from Pydantic for data modeling.
from pydantic import BaseModel, Field

# --- Model Definition ---

class DashboardSummary(BaseModel):
    """
    Defines the data contract for the response of the dashboard summary endpoint.
    This model specifies the exact shape of the data that will be sent to the
    Home Page to populate its "Quick Info Cards".
    """

    classCount: int = Field(
        ...,  # This field is required.
        description="The total number of active classes for the user.",
        # The 'example' is used by FastAPI to generate richer API documentation.
        example=4
    )
    
    studentCount: int = Field(
        ...,  # This field is required.
        description="The total number of students enrolled across all of the user's classes.",
        example=112
    )