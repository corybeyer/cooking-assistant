"""
Cooking Assistant API - Application Entry Point

This is the main FastAPI application that serves as the entry point
for the Cooking Assistant API. It follows the MVC (Model-View-Controller)
architectural pattern.

Architecture Overview:
=====================
- Models (app/models/): Data structures and database entities
  - entities.py: SQLAlchemy ORM models for database tables
  - schemas.py: Pydantic schemas for API request/response validation

- Views (app/views/): User interface templates
  - templates/: HTML templates for the web UI
  - Served at /app endpoint for the voice-enabled cooking interface

- Controllers (app/controllers/): Request handlers
  - recipes.py: CRUD operations for recipe management
  - cooking.py: Cooking session management with Claude AI

- Services (app/services/): Business logic layer
  - claude.py: Claude AI integration for conversational cooking guidance
  - speech.py: Azure Speech integration (placeholder)

Why This Architecture?
=====================
1. Separation of Concerns: Each layer has a single responsibility
2. Testability: Components can be tested in isolation
3. Maintainability: Changes in one layer don't affect others
4. Scalability: Easy to add new features or replace components

Request Flow:
============
1. Request arrives at a Controller endpoint
2. Controller validates input using Pydantic Schemas (Models)
3. Controller calls Services for business logic
4. Services interact with database via ORM Entities (Models)
5. Response is serialized using Pydantic Schemas (Models)
6. For web UI, Views render the response in HTML
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Import controllers (the 'C' in MVC)
from app.controllers import recipes_router, cooking_router

# Create FastAPI application
app = FastAPI(
    title="Cooking Assistant API",
    description="""
    Voice-controlled cooking assistant powered by Claude AI.

    ## Features
    - Recipe management (CRUD operations)
    - Interactive cooking sessions with AI guidance
    - Real-time streaming responses
    - Voice input/output support via web interface

    ## Architecture
    This API follows the MVC pattern:
    - **Models**: SQLAlchemy entities + Pydantic schemas
    - **Views**: HTML templates for web UI
    - **Controllers**: FastAPI routers handling requests
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware configuration
# Allows the web frontend to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register controllers (routers)
# Each controller handles a specific resource/feature area
app.include_router(recipes_router)   # /recipes endpoints
app.include_router(cooking_router)   # /cooking endpoints


# ============================================
# Health Check Endpoints
# ============================================

@app.get("/", tags=["health"])
def root():
    """
    Basic health check endpoint.

    Returns a simple status indicating the API is running.
    Used by load balancers and monitoring systems.
    """
    return {
        "status": "healthy",
        "service": "Cooking Assistant API",
        "version": "1.0.0"
    }


@app.get("/health", tags=["health"])
def health_check():
    """
    Detailed health check endpoint.

    Provides status of dependent services.
    Useful for debugging and monitoring dashboards.
    """
    return {
        "status": "healthy",
        "database": "not_checked",  # TODO: Add database ping
        "claude": "not_checked"     # TODO: Add Claude API check
    }


# ============================================
# View Serving (Static Files & Templates)
# ============================================

# Define paths to view assets
# Views are stored in app/views/templates for MVC organization
views_path = os.path.join(os.path.dirname(__file__), "views", "templates")

# Also support legacy static folder for backward compatibility
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# Mount static files if directory exists
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/app", tags=["views"])
def serve_app():
    """
    Serve the voice-enabled cooking assistant web UI.

    This endpoint returns the main HTML template that provides:
    - Recipe selection interface
    - Voice input/output controls
    - Chat interface with streaming support
    - Session management

    The template uses client-side JavaScript to interact with
    the API endpoints for a dynamic, responsive experience.
    """
    # Try MVC views path first
    index_path = os.path.join(views_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)

    # Fall back to static folder
    static_index = os.path.join(static_path, "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)

    return {"error": "UI not available"}
