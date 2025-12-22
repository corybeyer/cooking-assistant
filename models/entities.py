"""
SQLAlchemy ORM Entity Models

These models represent the database tables and define the relationships
between entities. They map directly to Azure SQL Server tables.

Database Design Rationale:
- Normalized structure to avoid data duplication (ingredients, units)
- Cascade deletes to maintain referential integrity
- OrderIndex fields to preserve ordering of steps and ingredients

Table Relationships:
    Recipe (1) ──────┬──> (*) RecipeIngredient ──> (1) Ingredient
                     │                          └──> (1) UnitOfMeasure
                     └──> (*) Step
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Date, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from config.database import Base


class Recipe(Base):
    """
    Recipe metadata and the central entity in the domain model.

    A recipe is the main unit of content in the cooking assistant.
    It contains metadata about the dish and has relationships to
    ingredients (through RecipeIngredient) and preparation steps.
    """
    __tablename__ = "Recipes"

    RecipeId = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(200), nullable=False)
    Description = Column(Text, nullable=True)
    SourceType = Column(String(100), nullable=True)  # e.g., "web", "book", "family"
    SourceURL = Column(String(500), nullable=True)
    Cuisine = Column(String(100), nullable=True)      # e.g., "Italian", "Mexican"
    Category = Column(String(100), nullable=True)     # e.g., "Dinner", "Dessert"
    PrepTime = Column(Integer, nullable=True)         # Minutes
    CookTime = Column(Integer, nullable=True)         # Minutes
    Servings = Column(Integer, nullable=True)
    CreatedDate = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships with cascade delete for data integrity
    ingredients = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan"
    )
    steps = relationship(
        "Step",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="Step.OrderIndex"
    )


class Ingredient(Base):
    """
    Normalized ingredient names.

    Ingredients are stored separately to enable:
    - Deduplication across recipes
    - Future features like "recipes with ingredient X"
    - Consistent naming and potential autocomplete
    """
    __tablename__ = "Ingredients"

    IngredientId = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(100), nullable=False, unique=True)


class UnitOfMeasure(Base):
    """
    Normalized units of measurement.

    Stored separately for consistency across recipes.
    Examples: "cup", "tablespoon", "gram", "piece"
    """
    __tablename__ = "UnitsOfMeasure"

    UnitId = Column(Integer, primary_key=True, autoincrement=True)
    UnitName = Column(String(50), nullable=False, unique=True)


class RecipeIngredient(Base):
    """
    Junction table linking recipes to ingredients with quantities.

    This many-to-many relationship table also stores:
    - The quantity needed (as string to handle "1/2", "2-3", etc.)
    - The unit of measure (optional, for items like "2 eggs")
    - The order in which ingredients should be listed
    """
    __tablename__ = "RecipeIngredients"

    RecipeIngredientId = Column(Integer, primary_key=True, autoincrement=True)
    RecipeId = Column(
        Integer,
        ForeignKey("Recipes.RecipeId", ondelete="CASCADE"),
        nullable=False
    )
    IngredientId = Column(
        Integer,
        ForeignKey("Ingredients.IngredientId"),
        nullable=False
    )
    UnitId = Column(
        Integer,
        ForeignKey("UnitsOfMeasure.UnitId"),
        nullable=True
    )
    Quantity = Column(String(50), nullable=True)  # String for flexibility
    OrderIndex = Column(Integer, nullable=False)

    # Relationships for eager loading
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient")
    unit = relationship("UnitOfMeasure")


class Step(Base):
    """
    Recipe preparation steps.

    Steps are ordered instructions for preparing the recipe.
    The OrderIndex ensures steps are presented in the correct sequence.
    """
    __tablename__ = "Steps"

    StepId = Column(Integer, primary_key=True, autoincrement=True)
    RecipeId = Column(
        Integer,
        ForeignKey("Recipes.RecipeId", ondelete="CASCADE"),
        nullable=False
    )
    Description = Column(Text, nullable=False)
    OrderIndex = Column(Integer, nullable=False)

    # Relationship
    recipe = relationship("Recipe", back_populates="steps")


# ============================================
# Shopping List Models
# ============================================

class ShoppingList(Base):
    """
    Shopping list for meal planning.

    A shopping list aggregates ingredients from multiple recipes
    and can be shared via a unique link code.
    """
    __tablename__ = "ShoppingLists"

    ShoppingListId = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(200), nullable=True)
    CreatedDate = Column(DateTime, nullable=False, server_default=func.now())
    Status = Column(String(50), nullable=False, default='active')  # active, completed, archived

    # Relationships
    recipes = relationship(
        "ShoppingListRecipe",
        back_populates="shopping_list",
        cascade="all, delete-orphan"
    )
    items = relationship(
        "ShoppingListItem",
        back_populates="shopping_list",
        cascade="all, delete-orphan"
    )
    links = relationship(
        "ShoppingListLink",
        back_populates="shopping_list",
        cascade="all, delete-orphan"
    )


class ShoppingListRecipe(Base):
    """
    Links a shopping list to recipes with optional planning details.

    Tracks which recipes are included in a meal plan, with optional
    serving adjustments and scheduling information.
    """
    __tablename__ = "ShoppingListRecipes"

    ShoppingListRecipeId = Column(Integer, primary_key=True, autoincrement=True)
    ShoppingListId = Column(
        Integer,
        ForeignKey("ShoppingLists.ShoppingListId", ondelete="CASCADE"),
        nullable=False
    )
    RecipeId = Column(
        Integer,
        ForeignKey("Recipes.RecipeId"),
        nullable=False
    )
    Servings = Column(Integer, nullable=True)  # NULL = use recipe default
    PlannedDate = Column(Date, nullable=True)
    MealType = Column(String(50), nullable=True)  # breakfast, lunch, dinner, snack

    # Relationships
    shopping_list = relationship("ShoppingList", back_populates="recipes")
    recipe = relationship("Recipe")


class ShoppingListItem(Base):
    """
    Aggregated ingredient in a shopping list.

    Represents a single item to buy, with quantity aggregated
    across all recipes in the shopping list.
    """
    __tablename__ = "ShoppingListItems"

    ShoppingListItemId = Column(Integer, primary_key=True, autoincrement=True)
    ShoppingListId = Column(
        Integer,
        ForeignKey("ShoppingLists.ShoppingListId", ondelete="CASCADE"),
        nullable=False
    )
    IngredientId = Column(
        Integer,
        ForeignKey("Ingredients.IngredientId"),
        nullable=False
    )
    AggregatedQuantity = Column(String(100), nullable=True)  # "3 medium" or "2 lbs"
    Category = Column(String(50), nullable=True)  # produce, meat, dairy, pantry
    IsChecked = Column(Boolean, nullable=False, default=False)
    SortOrder = Column(Integer, nullable=True)

    # Relationships
    shopping_list = relationship("ShoppingList", back_populates="items")
    ingredient = relationship("Ingredient")


class ShoppingListLink(Base):
    """
    Shareable link for a shopping list.

    Provides a short, unique code that can be shared via SMS
    to access the shopping list on mobile devices.
    """
    __tablename__ = "ShoppingListLinks"

    LinkId = Column(Integer, primary_key=True, autoincrement=True)
    ShoppingListId = Column(
        Integer,
        ForeignKey("ShoppingLists.ShoppingListId", ondelete="CASCADE"),
        nullable=False
    )
    LinkCode = Column(String(20), nullable=False, unique=True)
    CreatedDate = Column(DateTime, nullable=False, server_default=func.now())
    ExpiresDate = Column(DateTime, nullable=True)

    # Relationship
    shopping_list = relationship("ShoppingList", back_populates="links")


class GroceryPrice(Base):
    """
    Cached price data from grocery store APIs.

    Stores price snapshots to avoid excessive API calls
    and enable price comparison across stores.
    """
    __tablename__ = "GroceryPrices"

    GroceryPriceId = Column(Integer, primary_key=True, autoincrement=True)
    IngredientId = Column(
        Integer,
        ForeignKey("Ingredients.IngredientId"),
        nullable=False
    )
    StoreName = Column(String(100), nullable=False)  # Kroger, Walmart, H-E-B
    ProductName = Column(String(300), nullable=True)  # Actual product matched
    ProductId = Column(String(100), nullable=True)  # Store's product ID
    Price = Column(Numeric(10, 2), nullable=True)
    Unit = Column(String(50), nullable=True)  # per lb, each, per oz
    LastUpdated = Column(DateTime, nullable=False, server_default=func.now())

    # Relationship
    ingredient = relationship("Ingredient")
