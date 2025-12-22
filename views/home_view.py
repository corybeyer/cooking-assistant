"""
Home View - Landing page for the Cooking Assistant.

Displays navigation options and feature descriptions.
"""

import streamlit as st


class HomeView:
    """View for the home/landing page."""

    def render(self) -> None:
        """Render the home page."""
        st.title("Cooking Assistant")
        st.markdown("Your AI-powered kitchen companion")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            self._render_cook_card()

        with col2:
            self._render_plan_card()

        st.markdown("---")
        st.markdown("*Use the sidebar to navigate between pages.*")

    def _render_cook_card(self) -> None:
        """Render the Cook a Recipe card."""
        st.markdown("### Cook a Recipe")
        st.markdown("""
        Get voice-guided, step-by-step cooking help.

        - Select a recipe from your collection
        - Ask questions while you cook
        - Get substitution suggestions
        - Hands-free voice control
        """)
        if st.button("Start Cooking →", type="primary", use_container_width=True):
            st.switch_page("pages/1_🍳_Cook.py")

    def _render_plan_card(self) -> None:
        """Render the Plan Meals card."""
        st.markdown("### Plan Meals")
        st.markdown("""
        Plan your meals for the week with AI help.

        - Chat about dietary preferences
        - Get recipe suggestions
        - Build a meal plan
        - Generate a shopping list
        """)
        if st.button("Plan Meals →", type="primary", use_container_width=True):
            st.switch_page("pages/2_📋_Plan_Meals.py")
