"""
Planning View - UI for meal planning conversations.

This view handles all rendering for the meal planning feature.
It delegates business logic to the PlanningController.
"""

import streamlit as st

from controllers.planning_controller import PlanningController
from views.components.chat import render_chat_messages
from views.components.sidebar import render_planning_sidebar


class PlanningView:
    """View for meal planning UI."""

    def __init__(self):
        self.controller = PlanningController()

    def render(self):
        """Main render method."""
        st.title("Meal Planner")
        st.markdown("Chat with me to plan your meals for the week!")

        # Sidebar with recipe selection and plan summary
        render_planning_sidebar(
            selected_recipes=self.controller.get_selected_recipe_details(),
            all_recipes=self.controller.get_all_recipes(),
            is_confirmed=self.controller.is_plan_confirmed(),
            shopping_list_id=self.controller.get_shopping_list_id(),
            on_remove_recipe=self.controller.remove_recipe_from_plan,
            on_add_recipe=self.controller.add_recipe_to_plan,
            on_confirm_plan=self.controller.confirm_plan,
            on_clear=self.controller.clear_conversation,
        )

        # Main chat area
        self._render_chat_area()

    def _render_chat_area(self):
        """Render main chat area."""
        messages = self.controller.get_messages()

        # Start conversation if empty
        if not messages:
            with st.spinner("Starting conversation..."):
                self.controller.start_conversation()
                st.rerun()

        # Display chat messages using component
        render_chat_messages(messages)

        # Chat input
        st.markdown("---")

        user_input = st.chat_input("Type your message...")

        if user_input:
            with st.spinner("Thinking..."):
                self.controller.send_message(user_input)
            st.rerun()

        # Quick prompts
        self._render_quick_prompts()

    def _render_quick_prompts(self):
        """Render quick prompt buttons."""
        st.markdown("**Quick prompts:**")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Healthy meals", use_container_width=True):
                self.controller.send_message("I want healthy, nutritious meals")
                st.rerun()

        with col2:
            if st.button("Quick & easy", use_container_width=True):
                self.controller.send_message("I need quick meals under 30 minutes")
                st.rerun()

        with col3:
            if st.button("Special occasion", use_container_width=True):
                self.controller.send_message("I'm planning for a special occasion")
                st.rerun()
