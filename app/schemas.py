from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# Ingredient Schemas
# ============================================

class IngredientInput(BaseModel):
    """Ingredient input when creating a recipe."""
    name: str = Field(..., max_length=100)
    quantity: str = Field(..., max_length=50)
    unit: str | None = Field(None, max_length=50)


class IngredientResponse(BaseModel):
    """Ingredient in API responses."""
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
    """Step input when creating a recipe."""
    description: str


class StepResponse(BaseModel):
    """Step in API responses."""
    step_id: int
    order_index: int
    description: str

    class Config:
        from_attributes = True


# ============================================
# Recipe Schemas
# ============================================

class RecipeCreate(BaseModel):
    """Request body for creating a recipe."""
    name: str = Field(..., max_length=200)
    description: str | None = None
    source_type: str | None = Field(None, max_length=100)
    source_url: str | None = Field(None, max_length=500)
    cuisine: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=100)
    prep_time: int | None = Field(None, ge=0)
    cook_time: int | None = Field(None, ge=0)
    servings: int | None = Field(None, ge=1)
    ingredients: list[IngredientInput]
    steps: list[StepInput]


class RecipeSummary(BaseModel):
    """Recipe summary for list views."""
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
    """Full recipe with ingredients and steps."""
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
# Cooking Session Schemas (for Claude integration)
# ============================================

class CookingSessionStart(BaseModel):
    """Request to start a cooking session."""
    recipe_id: int


class CookingSessionResponse(BaseModel):
    """Response when starting a cooking session."""
    session_id: str
    recipe_name: str
    total_ingredients: int
    total_steps: int


class CookingMessage(BaseModel):
    """Message to the cooking assistant."""
    text: str | None = None
    # audio: str | None = None  # Base64 encoded, for later


class CookingResponse(BaseModel):
    """Response from the cooking assistant."""
    text: str
    # audio_url: str | None = None  # For later
