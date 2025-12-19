"""
Controllers Package - The 'C' in MVC

Controllers handle HTTP requests and coordinate between:
- Models (data access and validation)
- Services (business logic)
- Views (response formatting)

Each controller is a FastAPI APIRouter that defines endpoints
for a specific resource or feature area.

Why Controllers vs Routers?
The term "controller" emphasizes the role of these modules in the
MVC pattern - they control the flow of data and coordinate actions.
FastAPI calls them "routers" but the responsibility is the same.
"""

from app.controllers.recipes import router as recipes_router
from app.controllers.cooking import router as cooking_router

__all__ = ["recipes_router", "cooking_router"]
