from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
