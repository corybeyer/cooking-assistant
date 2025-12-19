from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.routers import recipes_router, cooking_router

app = FastAPI(
    title="Cooking Assistant API",
    description="Voice-controlled cooking assistant powered by Claude",
    version="0.1.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(recipes_router)
app.include_router(cooking_router)


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Cooking Assistant API",
        "version": "0.1.0"
    }


@app.get("/health")
def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "not_checked",  # TODO: add DB ping
        "claude": "not_checked"     # TODO: add Claude API check
    }


# Serve static files
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/app")
def serve_app():
    """Serve the voice-enabled cooking assistant UI."""
    index_path = os.path.join(static_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "UI not available"}
