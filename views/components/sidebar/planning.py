"""
Meal planning sidebar component.
"""

import streamlit as st
from typing import Callable, Any


def render_planning_sidebar(
    selected_recipes: list[Any],
    all_recipes: list[Any],
    is_confirmed: bool,
    shopping_list_id: int | None,
    on_remove_recipe: Callable[[int], None],
    on_add_recipe: Callable[[int], None],
    on_confirm_plan: Callable[[str | None], int],
    on_clear: Callable[[], None],
):
    """
    Render the meal planning sidebar.

    Args:
        selected_recipes: List of selected recipe objects (need .id, .name)
        all_recipes: List of all available recipes
        is_confirmed: Whether the plan is confirmed
        shopping_list_id: ID of created shopping list (if confirmed)
        on_remove_recipe: Callback to remove a recipe by ID
        on_add_recipe: Callback to add a recipe by ID
        on_confirm_plan: Callback to confirm plan, returns shopping list ID
        on_clear: Callback to clear the conversation
    """
    with st.sidebar:
        st.markdown("### Your Plan")
        st.markdown("---")

        # Show selected recipes
        if selected_recipes:
            for recipe in selected_recipes:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"* {recipe.name}")
                with col2:
                    if st.button("x", key=f"remove_{recipe.id}", help="Remove"):
                        on_remove_recipe(recipe.id)
                        st.rerun()

            st.markdown("---")

            # Confirm plan button
            if not is_confirmed:
                plan_name = st.text_input(
                    "Plan name (optional):",
                    placeholder="e.g., Healthy Week"
                )

                if st.button("Confirm Plan & Create Shopping List",
                            type="primary",
                            use_container_width=True):
                    try:
                        on_confirm_plan(plan_name or None)
                        st.success("Shopping list created!")
                        st.info("Go to the Shopping List page to view and share it.")
                    except ValueError as e:
                        st.error(str(e))
            else:
                st.success("Plan confirmed!")
                st.info(f"Shopping list #{shopping_list_id} created")

                if st.button("Start New Plan", use_container_width=True):
                    on_clear()
                    st.rerun()
        else:
            st.markdown("*No recipes selected yet.*")
            st.markdown("Chat with me to get meal suggestions!")

        st.markdown("---")

        # Quick add section
        st.markdown("### Quick Add")
        if all_recipes:
            recipe_names = {r.name: r.id for r in all_recipes}
            selected_name = st.selectbox(
                "Add a recipe:",
                options=[""] + list(recipe_names.keys()),
                format_func=lambda x: "Select..." if x == "" else x,
                label_visibility="collapsed"
            )

            if selected_name:
                if st.button("Add to Plan", use_container_width=True):
                    on_add_recipe(recipe_names[selected_name])
                    st.rerun()

        st.markdown("---")

        # Clear conversation
        if st.button("Clear Conversation", use_container_width=True):
            on_clear()
            st.rerun()
