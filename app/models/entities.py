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

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


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
