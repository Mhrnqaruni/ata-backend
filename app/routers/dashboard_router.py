# /app/routers/dashboard_router.py

# --- Core FastAPI Imports ---
from fastapi import APIRouter, Depends

# --- Service and Model Imports ---
# Import the business logic service that this router will use.
from ..services import dashboard_service
# Import the database service dependency provider.
from ..services.database_service import DatabaseService, get_db_service
# Import the Pydantic model to define the response shape (the API contract).
from ..models.dashboard_model import DashboardSummary

# --- APIRouter Instance ---
# Create a router instance. All endpoints defined in this file will be
# attached to this router.
router = APIRouter()

# --- Endpoint Definition ---
@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get Dashboard Summary",
    description="Retrieves high-level statistics for the main Home Page dashboard view."
)
def get_dashboard_summary(
    # This is FastAPI's Dependency Injection system in action.
    # It tells FastAPI to call the `get_db_service` function and provide its
    # result (the singleton db_service_instance) as the 'db' argument.
    db: DatabaseService = Depends(get_db_service)
):
    """
    This is the "thin" router layer. Its only job is to:
    1. Receive the incoming HTTP request.
    2. Use dependency injection to get necessary services.
    3. Delegate the actual work to the "thick" business logic service.
    4. Return the result, which FastAPI will validate against the response_model.
    """
    # Delegate immediately to the service layer to get the summary data.
    return dashboard_service.get_summary_data(db=db)