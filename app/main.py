# /app/main.py

# --- Core FastAPI Imports ---
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# --- Application-specific Router Imports ---
from .routers import (
    classes_router, 
    assessments_router, 
    tools_router, 
    chatbot_router, 
    dashboard_router, 
    library_router,
    history_router,
    public_router  # <<< ADDITION 1: Import the new public_router
)

# --- Service Imports for Startup Logic ---
from .services import library_service

# --- Application Lifecycle Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs ONCE when the application starts up.
    library_service.initialize_library_cache()
    yield
    # This code runs ONCE when the application shuts down.

# --- FastAPI Application Instance Creation ---
app = FastAPI(
    title="ATA Backend API",
    description="The intelligent engine for the AI Teaching Assistant platform.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Middleware Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Router Inclusion ---
# Authenticated API routes under the /api prefix
app.include_router(dashboard_router.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(classes_router.router, prefix="/api/classes", tags=["Classes"])
app.include_router(assessments_router.router, prefix="/api/assessments", tags=["Assessments"])
app.include_router(tools_router.router, prefix="/api/tools", tags=["AI Tools"])
app.include_router(chatbot_router.router, prefix="/api/chatbot", tags=["Chatbot"])
app.include_router(library_router.router, prefix="/api/library", tags=["Library"])
app.include_router(history_router.router, prefix="/api/history", tags=["History"])

# --- ADDITION 2: Unauthenticated, public-facing routes under the /public prefix ---
app.include_router(public_router.router, prefix="/public", tags=["Public"])

# --- Root / Health Check Endpoint ---
@app.get("/", tags=["Health Check"])
async def read_root():
    """A simple health check endpoint to confirm the API is online."""
    return {"status": "ATA Backend is running!", "version": app.version}