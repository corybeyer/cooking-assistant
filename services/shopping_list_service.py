"""
Shopping List Service - handles ingredient aggregation and list generation.

This service aggregates ingredients across multiple recipes into a
consolidated shopping list, handling:
- Duplicate ingredient consolidation
- Quantity aggregation
- Category assignment
- Smart aggregation via Claude for complex cases
"""

from dataclasses import dataclass
from typing import Optional
from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from models import (
    Recipe,
    RecipeIngredient,
    Ingredient,
    ShoppingList,
    ShoppingListItem,
)
from models.repositories import ShoppingListRepository
from services.claude_service import ClaudeService


@dataclass
class AggregatedIngredient:
    """Represents an aggregated ingredient for the shopping list."""
    ingredient_id: int
    ingredient_name: str
    quantities: list[str]  # Original quantities from each recipe
    aggregated_quantity: str  # Combined quantity string
    category: str
    sort_order: int


# Ingredient category mappings
INGREDIENT_CATEGORIES = {
    # Produce
    "onion": "Produce", "garlic": "Produce", "tomato": "Produce",
    "potato": "Produce", "carrot": "Produce", "celery": "Produce",
    "lettuce": "Produce", "spinach": "Produce", "kale": "Produce",
    "pepper": "Produce", "cucumber": "Produce", "broccoli": "Produce",
    "mushroom": "Produce", "zucchini": "Produce", "squash": "Produce",
    "lemon": "Produce", "lime": "Produce", "apple": "Produce",
    "banana": "Produce", "orange": "Produce", "avocado": "Produce",
    "herbs": "Produce", "cilantro": "Produce", "parsley": "Produce",
    "basil": "Produce", "thyme": "Produce", "rosemary": "Produce",
    "ginger": "Produce", "scallion": "Produce", "green onion": "Produce",

    # Meat & Seafood
    "chicken": "Meat & Seafood", "beef": "Meat & Seafood",
    "pork": "Meat & Seafood", "sausage": "Meat & Seafood",
    "bacon": "Meat & Seafood", "ham": "Meat & Seafood",
    "turkey": "Meat & Seafood", "lamb": "Meat & Seafood",
    "fish": "Meat & Seafood", "salmon": "Meat & Seafood",
    "shrimp": "Meat & Seafood", "tuna": "Meat & Seafood",
    "crab": "Meat & Seafood", "lobster": "Meat & Seafood",

    # Dairy & Eggs
    "milk": "Dairy & Eggs", "cream": "Dairy & Eggs",
    "butter": "Dairy & Eggs", "cheese": "Dairy & Eggs",
    "yogurt": "Dairy & Eggs", "egg": "Dairy & Eggs",
    "sour cream": "Dairy & Eggs", "cottage cheese": "Dairy & Eggs",

    # Bakery & Bread
    "bread": "Bakery", "tortilla": "Bakery", "bun": "Bakery",
    "roll": "Bakery", "pita": "Bakery", "naan": "Bakery",

    # Grains & Pasta
    "rice": "Grains & Pasta", "pasta": "Grains & Pasta",
    "noodle": "Grains & Pasta", "quinoa": "Grains & Pasta",
    "oat": "Grains & Pasta", "barley": "Grains & Pasta",
    "lentil": "Grains & Pasta", "bean": "Grains & Pasta",

    # Canned & Jarred
    "tomato sauce": "Canned & Jarred", "tomato paste": "Canned & Jarred",
    "broth": "Canned & Jarred", "stock": "Canned & Jarred",
    "coconut milk": "Canned & Jarred", "beans": "Canned & Jarred",

    # Pantry Staples
    "flour": "Pantry", "sugar": "Pantry", "salt": "Pantry",
    "pepper": "Pantry", "oil": "Pantry", "olive oil": "Pantry",
    "vegetable oil": "Pantry", "vinegar": "Pantry",
    "soy sauce": "Pantry", "honey": "Pantry", "maple syrup": "Pantry",
    "vanilla": "Pantry", "baking powder": "Pantry",
    "baking soda": "Pantry", "cornstarch": "Pantry",

    # Spices
    "cumin": "Spices", "paprika": "Spices", "oregano": "Spices",
    "cinnamon": "Spices", "nutmeg": "Spices", "cayenne": "Spices",
    "chili powder": "Spices", "curry": "Spices", "turmeric": "Spices",
}

# Category sort order for shopping flow
CATEGORY_ORDER = {
    "Produce": 1,
    "Meat & Seafood": 2,
    "Dairy & Eggs": 3,
    "Bakery": 4,
    "Deli": 5,
    "Grains & Pasta": 6,
    "Canned & Jarred": 7,
    "Frozen": 8,
    "Pantry": 9,
    "Spices": 10,
    "Other": 99,
}


class ShoppingListService:
    """Service for shopping list generation and ingredient aggregation."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ShoppingListRepository(db)
        self.claude = ClaudeService()

    def categorize_ingredient(self, ingredient_name: str) -> str:
        """Determine the store category for an ingredient."""
        name_lower = ingredient_name.lower()

        # Check for exact or partial matches
        for keyword, category in INGREDIENT_CATEGORIES.items():
            if keyword in name_lower:
                return category

        return "Other"

    def aggregate_quantities(self, quantities: list[str]) -> str:
        """
        Combine multiple quantities into a single string.

        Simple aggregation - just combines with +
        For smarter aggregation, use aggregate_with_claude()
        """
        # Filter out empty quantities
        valid = [q.strip() for q in quantities if q and q.strip()]

        if not valid:
            return ""

        if len(valid) == 1:
            return valid[0]

        # Try to sum numeric quantities with same units
        # For now, just concatenate
        return " + ".join(valid)

    def get_recipe_ingredients(self, recipe_ids: list[int]) -> list[dict]:
        """Get all ingredients from multiple recipes."""
        ingredients = []

        recipes = self.db.query(Recipe).options(
            joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient),
            joinedload(Recipe.ingredients).joinedload(RecipeIngredient.unit),
        ).filter(Recipe.RecipeId.in_(recipe_ids)).all()

        for recipe in recipes:
            for ri in recipe.ingredients:
                unit_name = ri.unit.UnitName if ri.unit else ""
                quantity_str = f"{ri.Quantity or ''} {unit_name}".strip()

                ingredients.append({
                    "recipe_id": recipe.RecipeId,
                    "recipe_name": recipe.Name,
                    "ingredient_id": ri.IngredientId,
                    "ingredient_name": ri.ingredient.Name,
                    "quantity": quantity_str,
                    "unit": unit_name,
                    "raw_quantity": ri.Quantity,
                })

        return ingredients

    def aggregate_ingredients(
        self,
        recipe_ids: list[int],
        use_claude: bool = False
    ) -> list[AggregatedIngredient]:
        """
        Aggregate ingredients across multiple recipes.

        Args:
            recipe_ids: List of recipe IDs to aggregate
            use_claude: If True, use Claude for smart quantity aggregation

        Returns:
            List of AggregatedIngredient objects
        """
        raw_ingredients = self.get_recipe_ingredients(recipe_ids)

        # Group by ingredient
        grouped = defaultdict(list)
        for ing in raw_ingredients:
            grouped[ing["ingredient_id"]].append(ing)

        aggregated = []
        sort_order = 0

        for ingredient_id, items in grouped.items():
            ingredient_name = items[0]["ingredient_name"]
            quantities = [item["quantity"] for item in items]

            # Aggregate quantities
            if use_claude and len(quantities) > 1:
                agg_quantity = self._aggregate_with_claude(ingredient_name, quantities)
            else:
                agg_quantity = self.aggregate_quantities(quantities)

            # Determine category
            category = self.categorize_ingredient(ingredient_name)
            category_order = CATEGORY_ORDER.get(category, 99)

            aggregated.append(AggregatedIngredient(
                ingredient_id=ingredient_id,
                ingredient_name=ingredient_name,
                quantities=quantities,
                aggregated_quantity=agg_quantity,
                category=category,
                sort_order=category_order * 1000 + sort_order,
            ))
            sort_order += 1

        # Sort by category, then by order within category
        aggregated.sort(key=lambda x: x.sort_order)

        return aggregated

    def _aggregate_with_claude(
        self,
        ingredient_name: str,
        quantities: list[str]
    ) -> str:
        """Use Claude to intelligently aggregate quantities."""
        prompt = f"""Combine these quantities for "{ingredient_name}" into a single shopping list quantity:
{chr(10).join(f'- {q}' for q in quantities)}

Rules:
- If units are compatible, add them (e.g., "1 cup + 2 cups" = "3 cups")
- If units differ, list separately (e.g., "1 cup + 2 tablespoons")
- Round up for shopping convenience
- Handle vague quantities like "to taste" by noting them
- Keep response brief - just the quantity, no explanation

Response:"""

        try:
            response = self.claude.client.messages.create(
                model="claude-3-haiku-20240307",  # Use fast model for this
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception:
            # Fallback to simple aggregation
            return self.aggregate_quantities(quantities)

    def generate_shopping_list(
        self,
        shopping_list_id: int,
        use_claude: bool = False
    ) -> list[ShoppingListItem]:
        """
        Generate aggregated items for an existing shopping list.

        Takes the recipes linked to the shopping list and creates
        aggregated ShoppingListItem records.
        """
        # Get the shopping list with its recipes
        shopping_list = self.repo.get_by_id(shopping_list_id)
        if not shopping_list:
            raise ValueError(f"Shopping list {shopping_list_id} not found")

        recipe_ids = [slr.RecipeId for slr in shopping_list.recipes]
        if not recipe_ids:
            return []

        # Clear existing items
        self.repo.clear_items(shopping_list_id)

        # Aggregate ingredients
        aggregated = self.aggregate_ingredients(recipe_ids, use_claude=use_claude)

        # Create items in database
        items_data = [
            {
                "ingredient_id": agg.ingredient_id,
                "quantity": agg.aggregated_quantity,
                "category": agg.category,
                "sort_order": agg.sort_order,
            }
            for agg in aggregated
        ]

        items = self.repo.add_items(shopping_list_id, items_data)
        return items

    def create_shopping_list_from_recipes(
        self,
        name: str,
        recipe_ids: list[int],
        use_claude: bool = False
    ) -> ShoppingList:
        """
        Create a complete shopping list from recipes in one operation.

        Creates the shopping list, links recipes, and generates aggregated items.
        """
        # Create the list and link recipes
        shopping_list = self.repo.create_from_recipes(name, recipe_ids)

        # Generate aggregated items
        self.generate_shopping_list(shopping_list.ShoppingListId, use_claude=use_claude)

        # Refresh to get all relationships
        self.db.refresh(shopping_list)
        return shopping_list
