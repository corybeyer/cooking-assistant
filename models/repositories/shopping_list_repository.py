"""
Shopping List Repository - Data access for shopping list operations.

This repository handles all database operations related to shopping lists,
including CRUD operations and queries.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from models.entities import (
    ShoppingList,
    ShoppingListRecipe,
    ShoppingListItem,
    ShoppingListLink,
    Recipe,
    Ingredient,
)


class ShoppingListRepository:
    """Repository for shopping list database operations."""

    def __init__(self, db: Session):
        """Initialize with a database session."""
        self.db = db

    # ==========================================
    # Shopping List CRUD
    # ==========================================

    def create(self, user_id: str, name: Optional[str] = None) -> ShoppingList:
        """
        Create a new shopping list for a user.

        Args:
            user_id: The Entra ID object ID of the user
            name: Optional name for the list
        """
        shopping_list = ShoppingList(
            UserId=user_id,
            Name=name,
            Status='active'
        )
        self.db.add(shopping_list)
        self.db.commit()
        self.db.refresh(shopping_list)
        return shopping_list

    def get_by_id(self, shopping_list_id: int) -> Optional[ShoppingList]:
        """Get a shopping list by ID with all relationships loaded."""
        return self.db.query(ShoppingList).options(
            joinedload(ShoppingList.recipes).joinedload(ShoppingListRecipe.recipe),
            joinedload(ShoppingList.items).joinedload(ShoppingListItem.ingredient),
            joinedload(ShoppingList.links)
        ).filter(ShoppingList.ShoppingListId == shopping_list_id).first()

    def get_by_link_code(self, link_code: str) -> Optional[ShoppingList]:
        """Get a shopping list by its shareable link code."""
        link = self.db.query(ShoppingListLink).filter(
            ShoppingListLink.LinkCode == link_code,
            (ShoppingListLink.ExpiresDate.is_(None)) |
            (ShoppingListLink.ExpiresDate > datetime.now())
        ).first()

        if link:
            return self.get_by_id(link.ShoppingListId)
        return None

    def get_all_active(self, user_id: str) -> list[ShoppingList]:
        """
        Get all active shopping lists for a specific user.

        Args:
            user_id: The Entra ID object ID of the user
        """
        return self.db.query(ShoppingList).filter(
            ShoppingList.UserId == user_id,
            ShoppingList.Status == 'active'
        ).order_by(ShoppingList.CreatedDate.desc()).all()

    def update_status(self, shopping_list_id: int, status: str) -> bool:
        """Update the status of a shopping list."""
        result = self.db.query(ShoppingList).filter(
            ShoppingList.ShoppingListId == shopping_list_id
        ).update({"Status": status})
        self.db.commit()
        return result > 0

    def delete(self, shopping_list_id: int) -> bool:
        """Delete a shopping list (cascade deletes related records)."""
        result = self.db.query(ShoppingList).filter(
            ShoppingList.ShoppingListId == shopping_list_id
        ).delete()
        self.db.commit()
        return result > 0

    # ==========================================
    # Recipe Management
    # ==========================================

    def add_recipe(
        self,
        shopping_list_id: int,
        recipe_id: int,
        servings: Optional[int] = None,
        planned_date: Optional[datetime] = None,
        meal_type: Optional[str] = None
    ) -> ShoppingListRecipe:
        """Add a recipe to a shopping list."""
        shopping_list_recipe = ShoppingListRecipe(
            ShoppingListId=shopping_list_id,
            RecipeId=recipe_id,
            Servings=servings,
            PlannedDate=planned_date,
            MealType=meal_type
        )
        self.db.add(shopping_list_recipe)
        self.db.commit()
        self.db.refresh(shopping_list_recipe)
        return shopping_list_recipe

    def add_recipes(
        self,
        shopping_list_id: int,
        recipe_ids: list[int]
    ) -> list[ShoppingListRecipe]:
        """Add multiple recipes to a shopping list."""
        recipes = []
        for recipe_id in recipe_ids:
            slr = ShoppingListRecipe(
                ShoppingListId=shopping_list_id,
                RecipeId=recipe_id
            )
            self.db.add(slr)
            recipes.append(slr)
        self.db.commit()
        return recipes

    def remove_recipe(self, shopping_list_recipe_id: int) -> bool:
        """Remove a recipe from a shopping list."""
        result = self.db.query(ShoppingListRecipe).filter(
            ShoppingListRecipe.ShoppingListRecipeId == shopping_list_recipe_id
        ).delete()
        self.db.commit()
        return result > 0

    # ==========================================
    # Item Management
    # ==========================================

    def add_item(
        self,
        shopping_list_id: int,
        ingredient_id: int,
        aggregated_quantity: Optional[str] = None,
        category: Optional[str] = None,
        sort_order: Optional[int] = None
    ) -> ShoppingListItem:
        """Add an item to a shopping list."""
        item = ShoppingListItem(
            ShoppingListId=shopping_list_id,
            IngredientId=ingredient_id,
            AggregatedQuantity=aggregated_quantity,
            Category=category,
            SortOrder=sort_order,
            IsChecked=False
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_items(
        self,
        shopping_list_id: int,
        items: list[dict]
    ) -> list[ShoppingListItem]:
        """
        Add multiple items to a shopping list.

        Args:
            shopping_list_id: The shopping list ID
            items: List of dicts with keys: ingredient_id, quantity, category, sort_order
        """
        db_items = []
        for item in items:
            db_item = ShoppingListItem(
                ShoppingListId=shopping_list_id,
                IngredientId=item['ingredient_id'],
                AggregatedQuantity=item.get('quantity'),
                Category=item.get('category'),
                SortOrder=item.get('sort_order'),
                IsChecked=False
            )
            self.db.add(db_item)
            db_items.append(db_item)
        self.db.commit()
        return db_items

    def toggle_item(self, item_id: int) -> Optional[bool]:
        """Toggle the checked status of an item. Returns new status."""
        item = self.db.query(ShoppingListItem).filter(
            ShoppingListItem.ShoppingListItemId == item_id
        ).first()

        if item:
            item.IsChecked = not item.IsChecked
            self.db.commit()
            return item.IsChecked
        return None

    def set_item_checked(self, item_id: int, is_checked: bool) -> bool:
        """Set the checked status of an item."""
        result = self.db.query(ShoppingListItem).filter(
            ShoppingListItem.ShoppingListItemId == item_id
        ).update({"IsChecked": is_checked})
        self.db.commit()
        return result > 0

    def clear_items(self, shopping_list_id: int) -> int:
        """Remove all items from a shopping list. Returns count deleted."""
        result = self.db.query(ShoppingListItem).filter(
            ShoppingListItem.ShoppingListId == shopping_list_id
        ).delete()
        self.db.commit()
        return result

    # ==========================================
    # Link Management
    # ==========================================

    def create_link(
        self,
        shopping_list_id: int,
        expires_days: Optional[int] = 7
    ) -> ShoppingListLink:
        """Create a shareable link for a shopping list."""
        # Generate a unique short code
        code = secrets.token_urlsafe(6)  # ~8 characters

        # Ensure uniqueness
        while self.db.query(ShoppingListLink).filter(
            ShoppingListLink.LinkCode == code
        ).first():
            code = secrets.token_urlsafe(6)

        expires_date = None
        if expires_days:
            expires_date = datetime.now() + timedelta(days=expires_days)

        link = ShoppingListLink(
            ShoppingListId=shopping_list_id,
            LinkCode=code,
            ExpiresDate=expires_date
        )
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def get_link(self, shopping_list_id: int) -> Optional[ShoppingListLink]:
        """Get the active link for a shopping list."""
        return self.db.query(ShoppingListLink).filter(
            ShoppingListLink.ShoppingListId == shopping_list_id,
            (ShoppingListLink.ExpiresDate.is_(None)) |
            (ShoppingListLink.ExpiresDate > datetime.now())
        ).first()

    def delete_link(self, link_id: int) -> bool:
        """Delete a link."""
        result = self.db.query(ShoppingListLink).filter(
            ShoppingListLink.LinkId == link_id
        ).delete()
        self.db.commit()
        return result > 0

    # ==========================================
    # Convenience Methods
    # ==========================================

    def create_from_recipes(
        self,
        user_id: str,
        name: str,
        recipe_ids: list[int]
    ) -> ShoppingList:
        """
        Create a shopping list and add recipes in one operation.

        Args:
            user_id: The Entra ID object ID of the user
            name: Name for the shopping list
            recipe_ids: List of recipe IDs to add
        """
        shopping_list = self.create(user_id, name)
        self.add_recipes(shopping_list.ShoppingListId, recipe_ids)
        self.db.refresh(shopping_list)
        return shopping_list

    def is_owner(self, shopping_list_id: int, user_id: str) -> bool:
        """
        Check if a user owns a shopping list.

        Args:
            shopping_list_id: The shopping list ID
            user_id: The Entra ID object ID to check

        Returns:
            True if the user owns the list, False otherwise
        """
        result = self.db.query(ShoppingList).filter(
            ShoppingList.ShoppingListId == shopping_list_id,
            ShoppingList.UserId == user_id
        ).first()
        return result is not None

    def get_items_by_category(
        self,
        shopping_list_id: int
    ) -> dict[str, list[ShoppingListItem]]:
        """Get shopping list items grouped by category."""
        items = self.db.query(ShoppingListItem).options(
            joinedload(ShoppingListItem.ingredient)
        ).filter(
            ShoppingListItem.ShoppingListId == shopping_list_id
        ).order_by(
            ShoppingListItem.Category,
            ShoppingListItem.SortOrder
        ).all()

        grouped = {}
        for item in items:
            category = item.Category or "Other"
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(item)

        return grouped
