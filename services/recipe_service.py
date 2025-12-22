"""
Recipe Service - handles recipe data access and formatting.

This service is pure Python with no Streamlit dependencies.
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import joinedload

from config.database import SessionLocal
from models import Recipe, RecipeIngredient


@dataclass
class RecipeSummary:
    """Lightweight recipe data for lists and selection."""
    id: int
    name: str
    description: Optional[str]
    prep_time: Optional[int]
    cook_time: Optional[int]
    servings: Optional[int]
    cuisine: Optional[str]
    category: Optional[str]


class RecipeService:
    """Service for recipe data access and formatting."""

    def get_all(self) -> list[RecipeSummary]:
        """Get all recipes as summaries."""
        db = SessionLocal()
        try:
            recipes = db.query(Recipe).all()
            return [
                RecipeSummary(
                    id=r.RecipeId,
                    name=r.Name,
                    description=r.Description,
                    prep_time=r.PrepTime,
                    cook_time=r.CookTime,
                    servings=r.Servings,
                    cuisine=r.Cuisine,
                    category=r.Category,
                )
                for r in recipes
            ]
        finally:
            db.close()

    def get_by_id(self, recipe_id: int) -> Optional[Recipe]:
        """Get full recipe by ID with all relationships loaded."""
        db = SessionLocal()
        try:
            recipe = db.query(Recipe).options(
                joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient),
                joinedload(Recipe.ingredients).joinedload(RecipeIngredient.unit),
                joinedload(Recipe.steps)
            ).filter(Recipe.RecipeId == recipe_id).first()
            return recipe
        finally:
            db.close()

    def get_by_name(self, name: str) -> Optional[Recipe]:
        """Get full recipe by name."""
        db = SessionLocal()
        try:
            recipe = db.query(Recipe).options(
                joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient),
                joinedload(Recipe.ingredients).joinedload(RecipeIngredient.unit),
                joinedload(Recipe.steps)
            ).filter(Recipe.Name == name).first()
            return recipe
        finally:
            db.close()

    def format_for_claude(self, recipe: Recipe) -> str:
        """Format recipe as text for Claude's context."""
        if not recipe:
            return ""

        lines = [
            f"# {recipe.Name}",
            "",
            f"**Description:** {recipe.Description or 'No description'}",
            f"**Cuisine:** {recipe.Cuisine or 'Not specified'}",
            f"**Category:** {recipe.Category or 'Not specified'}",
            f"**Prep Time:** {recipe.PrepTime or '?'} minutes",
            f"**Cook Time:** {recipe.CookTime or '?'} minutes",
            f"**Servings:** {recipe.Servings or '?'}",
            "",
            "## Ingredients",
        ]

        for ri in sorted(recipe.ingredients, key=lambda x: x.OrderIndex):
            unit = ri.unit.UnitName if ri.unit else ""
            line = f"- {ri.Quantity or ''} {unit} {ri.ingredient.Name}".strip()
            lines.append(line)

        lines.extend(["", "## Steps"])

        for step in sorted(recipe.steps, key=lambda x: x.OrderIndex):
            lines.append(f"{step.OrderIndex}. {step.Description}")

        return "\n".join(lines)

    def format_recipe_list_for_claude(self, recipes: list[RecipeSummary]) -> str:
        """Format recipe list for meal planning context."""
        lines = []
        for r in recipes:
            time_info = []
            if r.prep_time:
                time_info.append(f"prep {r.prep_time}min")
            if r.cook_time:
                time_info.append(f"cook {r.cook_time}min")
            time_str = f" ({', '.join(time_info)})" if time_info else ""

            category_str = f" [{r.category}]" if r.category else ""
            cuisine_str = f" - {r.cuisine}" if r.cuisine else ""

            lines.append(f"- {r.name}{category_str}{cuisine_str}{time_str}")

        return "\n".join(lines)
