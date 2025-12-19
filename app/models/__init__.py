"""
Models Package - The 'M' in MVC

This package contains all data models for the Cooking Assistant application:
- SQLAlchemy ORM models for database entities
- Pydantic schemas for request/response validation (DTOs)

The separation between ORM models and schemas follows the principle of
separating persistence concerns from API contracts.
"""

from app.models.entities import (
    Recipe,
    Ingredient,
    UnitOfMeasure,
    RecipeIngredient,
    Step
)

from app.models.schemas import (
    # Ingredient schemas
    IngredientInput,
    IngredientResponse,
    # Step schemas
    StepInput,
    StepResponse,
    # Recipe schemas
    RecipeCreate,
    RecipeSummary,
    RecipeDetail,
    # Cooking session schemas
    CookingSessionStart,
    CookingSessionResponse,
    CookingMessage,
    CookingResponse
)

__all__ = [
    # ORM Models
    "Recipe",
    "Ingredient",
    "UnitOfMeasure",
    "RecipeIngredient",
    "Step",
    # Schemas
    "IngredientInput",
    "IngredientResponse",
    "StepInput",
    "StepResponse",
    "RecipeCreate",
    "RecipeSummary",
    "RecipeDetail",
    "CookingSessionStart",
    "CookingSessionResponse",
    "CookingMessage",
    "CookingResponse",
]
