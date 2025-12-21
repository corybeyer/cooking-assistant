"""
Planning Controller - manages meal planning session flow and state.

This controller handles:
- Planning conversation with Claude
- Recipe selection and confirmation
- Creating shopping lists from confirmed plans
"""

import streamlit as st
from typing import Optional
from datetime import datetime

from services.claude_service import ClaudeService
from services.recipe_service import RecipeService, RecipeSummary
from services.shopping_list_service import ShoppingListService
from app.database import SessionLocal


class PlanningController:
    """Controller for meal planning session management."""

    def __init__(self):
        self.claude = ClaudeService()
        self.recipes = RecipeService()
        self._init_session_state()

    def _init_session_state(self):
        """Initialize session state if not already set."""
        if "planning" not in st.session_state:
            st.session_state.planning = {
                "messages": [],
                "selected_recipes": [],  # List of recipe IDs confirmed for the plan
                "plan_confirmed": False,
                "shopping_list_id": None,
            }

    # ==========================================
    # Session State Accessors
    # ==========================================

    def get_messages(self) -> list[dict]:
        """Get the chat message history."""
        return st.session_state.planning["messages"]

    def get_selected_recipes(self) -> list[int]:
        """Get the list of selected recipe IDs."""
        return st.session_state.planning["selected_recipes"]

    def is_plan_confirmed(self) -> bool:
        """Check if a plan has been confirmed."""
        return st.session_state.planning["plan_confirmed"]

    def get_shopping_list_id(self) -> Optional[int]:
        """Get the created shopping list ID."""
        return st.session_state.planning["shopping_list_id"]

    # ==========================================
    # Recipe Data
    # ==========================================

    def get_all_recipes(self) -> list[RecipeSummary]:
        """Get all available recipes."""
        return self.recipes.get_all()

    def get_recipe_context_for_claude(self) -> str:
        """Get formatted recipe list for Claude's context."""
        recipes = self.get_all_recipes()
        return self.recipes.format_recipe_list_for_claude(recipes)

    # ==========================================
    # Chat Operations
    # ==========================================

    def send_message(self, user_message: str) -> str:
        """
        Send a message to Claude for meal planning.

        Returns Claude's response.
        """
        recipe_list = self.get_recipe_context_for_claude()
        history = st.session_state.planning["messages"]

        # Get Claude's response
        response = self.claude.chat_planning(user_message, recipe_list, history)

        # Update message history
        st.session_state.planning["messages"].append({
            "role": "user",
            "content": user_message
        })
        st.session_state.planning["messages"].append({
            "role": "assistant",
            "content": response
        })

        return response

    def start_conversation(self) -> str:
        """Start a new planning conversation with an initial prompt."""
        initial_message = "I'd like to plan some meals."
        return self.send_message(initial_message)

    def clear_conversation(self):
        """Clear the conversation and start fresh."""
        st.session_state.planning = {
            "messages": [],
            "selected_recipes": [],
            "plan_confirmed": False,
            "shopping_list_id": None,
        }

    # ==========================================
    # Plan Management
    # ==========================================

    def add_recipe_to_plan(self, recipe_id: int):
        """Add a recipe to the current plan."""
        if recipe_id not in st.session_state.planning["selected_recipes"]:
            st.session_state.planning["selected_recipes"].append(recipe_id)

    def remove_recipe_from_plan(self, recipe_id: int):
        """Remove a recipe from the current plan."""
        if recipe_id in st.session_state.planning["selected_recipes"]:
            st.session_state.planning["selected_recipes"].remove(recipe_id)

    def set_selected_recipes(self, recipe_ids: list[int]):
        """Set the selected recipes for the plan."""
        st.session_state.planning["selected_recipes"] = recipe_ids

    def confirm_plan(
        self,
        plan_name: Optional[str] = None,
        use_smart_aggregation: bool = False
    ) -> int:
        """
        Confirm the current plan and create a shopping list with aggregated ingredients.

        Args:
            plan_name: Optional name for the plan
            use_smart_aggregation: If True, use Claude for intelligent quantity aggregation

        Returns the shopping list ID.
        """
        recipe_ids = st.session_state.planning["selected_recipes"]

        if not recipe_ids:
            raise ValueError("No recipes selected for the plan")

        # Generate a default name if not provided
        if not plan_name:
            plan_name = f"Meal Plan - {datetime.now().strftime('%b %d, %Y')}"

        # Create shopping list with aggregated ingredients
        db = SessionLocal()
        try:
            service = ShoppingListService(db)
            shopping_list = service.create_shopping_list_from_recipes(
                name=plan_name,
                recipe_ids=recipe_ids,
                use_claude=use_smart_aggregation
            )
            shopping_list_id = shopping_list.ShoppingListId

            st.session_state.planning["plan_confirmed"] = True
            st.session_state.planning["shopping_list_id"] = shopping_list_id

            return shopping_list_id
        finally:
            db.close()

    def get_selected_recipe_details(self) -> list[RecipeSummary]:
        """Get details for all selected recipes."""
        all_recipes = self.get_all_recipes()
        selected_ids = self.get_selected_recipes()

        return [r for r in all_recipes if r.id in selected_ids]
