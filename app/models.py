from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Recipe(Base):
    """Recipe metadata."""
    __tablename__ = "Recipes"

    RecipeId = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(200), nullable=False)
    Description = Column(Text, nullable=True)
    SourceType = Column(String(100), nullable=True)
    SourceURL = Column(String(500), nullable=True)
    Cuisine = Column(String(100), nullable=True)
    Category = Column(String(100), nullable=True)
    PrepTime = Column(Integer, nullable=True)
    CookTime = Column(Integer, nullable=True)
    Servings = Column(Integer, nullable=True)
    CreatedDate = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    steps = relationship("Step", back_populates="recipe", cascade="all, delete-orphan", order_by="Step.OrderIndex")


class Ingredient(Base):
    """Normalized ingredient names."""
    __tablename__ = "Ingredients"

    IngredientId = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(100), nullable=False, unique=True)


class UnitOfMeasure(Base):
    """Normalized units of measure."""
    __tablename__ = "UnitsOfMeasure"

    UnitId = Column(Integer, primary_key=True, autoincrement=True)
    UnitName = Column(String(50), nullable=False, unique=True)


class RecipeIngredient(Base):
    """Links recipes to ingredients with quantities."""
    __tablename__ = "RecipeIngredients"

    RecipeIngredientId = Column(Integer, primary_key=True, autoincrement=True)
    RecipeId = Column(Integer, ForeignKey("Recipes.RecipeId", ondelete="CASCADE"), nullable=False)
    IngredientId = Column(Integer, ForeignKey("Ingredients.IngredientId"), nullable=False)
    UnitId = Column(Integer, ForeignKey("UnitsOfMeasure.UnitId"), nullable=True)
    Quantity = Column(String(50), nullable=True)
    OrderIndex = Column(Integer, nullable=False)

    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient")
    unit = relationship("UnitOfMeasure")


class Step(Base):
    """Recipe preparation steps."""
    __tablename__ = "Steps"

    StepId = Column(Integer, primary_key=True, autoincrement=True)
    RecipeId = Column(Integer, ForeignKey("Recipes.RecipeId", ondelete="CASCADE"), nullable=False)
    Description = Column(Text, nullable=False)
    OrderIndex = Column(Integer, nullable=False)

    # Relationships
    recipe = relationship("Recipe", back_populates="steps")
