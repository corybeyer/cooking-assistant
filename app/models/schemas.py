"""
Pydantic Schemas (Data Transfer Objects)

These schemas define the structure of data flowing in and out of the API.
They serve multiple purposes:
- Request validation: Ensure incoming data meets requirements
- Response serialization: Control what data is exposed to clients
- Documentation: Generate OpenAPI/Swagger docs automatically

Naming Convention:
- *Input: Data received from clients (create/update operations)
- *Response: Data returned to clients
- *Create: Specific input for creating new resources
- *Summary: Condensed view for list endpoints
- *Detail: Full view for single-resource endpoints

Why separate from ORM models?
- API contracts shouldn't be tightly coupled to database schema
- Different views of the same data (summary vs detail)
- Validation logic belongs at the API boundary
- Enables versioning API without changing database
"""

from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# Ingredient Schemas
# ============================================

class IngredientInput(BaseModel):
    """
    Ingredient data when creating a recipe.

    Used in the RecipeCreate schema as part of the ingredients list.
    The unit is optional because some ingredients don't need units
    (e.g., "2 eggs", "1 lemon").
    """
    name: str = Field(..., max_length=100, description="Name of the ingredient")
    quantity: str = Field(..., max_length=50, description="Amount needed (e.g., '2', '1/2')")
    unit: str | None = Field(None, max_length=50, description="Unit of measure (e.g., 'cup', 'tbsp')")


class IngredientResponse(BaseModel):
    """
    Ingredient data in API responses.

    Includes the order_index so clients can display ingredients
    in the intended order.
    """
    order_index: int
    name: str
    quantity: str | None
    unit: str | None

    class Config:
        from_attributes = True


# ============================================
# Step Schemas
# ============================================

class StepInput(BaseModel):
    """
    Step data when creating a recipe.

    The order is determined by position in the list, so only
    the description is needed.
    """
    description: str = Field(..., description="The step instruction text")


class StepResponse(BaseModel):
    """
    Step data in API responses.

    Includes step_id for potential future features (marking steps
    complete, adding notes to steps, etc.).
    """
    step_id: int
    order_index: int
    description: str

    class Config:
        from_attributes = True


# ============================================
# Recipe Schemas
# ============================================

class RecipeCreate(BaseModel):
    """
    Request body for creating a new recipe.

    All metadata fields are optional except name, ingredients, and steps.
    This allows quick recipe entry while supporting rich metadata
    when available.
    """
    name: str = Field(..., max_length=200, description="Recipe title")
    description: str | None = Field(None, description="Brief description of the dish")
    source_type: str | None = Field(None, max_length=100, description="Where recipe came from")
    source_url: str | None = Field(None, max_length=500, description="URL if from web")
    cuisine: str | None = Field(None, max_length=100, description="Cuisine type")
    category: str | None = Field(None, max_length=100, description="Meal category")
    prep_time: int | None = Field(None, ge=0, description="Prep time in minutes")
    cook_time: int | None = Field(None, ge=0, description="Cook time in minutes")
    servings: int | None = Field(None, ge=1, description="Number of servings")
    ingredients: list[IngredientInput] = Field(..., description="List of ingredients")
    steps: list[StepInput] = Field(..., description="Ordered preparation steps")


class RecipeSummary(BaseModel):
    """
    Condensed recipe view for list endpoints.

    Optimized for browsing and selection - includes key metadata
    without the full ingredients and steps lists.
    """
    recipe_id: int
    name: str
    description: str | None
    cuisine: str | None
    category: str | None
    prep_time: int | None
    cook_time: int | None
    servings: int | None
    created_date: datetime

    class Config:
        from_attributes = True


class RecipeDetail(BaseModel):
    """
    Complete recipe with all ingredients and steps.

    Used when viewing a single recipe - provides everything
    needed to cook the dish.
    """
    recipe_id: int
    name: str
    description: str | None
    source_type: str | None
    source_url: str | None
    cuisine: str | None
    category: str | None
    prep_time: int | None
    cook_time: int | None
    servings: int | None
    created_date: datetime
    ingredients: list[IngredientResponse]
    steps: list[StepResponse]

    class Config:
        from_attributes = True


# ============================================
# Cooking Session Schemas
# ============================================

class CookingSessionStart(BaseModel):
    """
    Request to start a cooking session.

    A cooking session creates a conversational context with Claude
    that has the recipe loaded, enabling hands-free guidance.
    """
    recipe_id: int = Field(..., description="ID of the recipe to cook")


class CookingSessionResponse(BaseModel):
    """
    Response when a cooking session is created.

    Provides the session_id needed for subsequent messages and
    summary info about the recipe being cooked.
    """
    session_id: str
    recipe_name: str
    total_ingredients: int
    total_steps: int


class CookingMessage(BaseModel):
    """
    Message to the cooking assistant.

    Currently text-only; audio field reserved for future
    Azure Speech integration.
    """
    text: str | None = Field(None, description="Text message to the assistant")
    # audio: str | None = None  # Base64 encoded, for future use


class CookingResponse(BaseModel):
    """
    Response from the cooking assistant.

    For non-streaming responses. Streaming responses use
    Server-Sent Events instead.
    """
    text: str
    # audio_url: str | None = None  # For future TTS integration
