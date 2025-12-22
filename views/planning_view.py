"""
Planning View - UI for meal planning conversations.

This view handles all rendering for the meal planning feature.
It delegates business logic to the PlanningController.
"""

import streamlit as st

from controllers.planning_controller import PlanningController
from views.components.chat import render_chat_messages
from views.components.voice_panel import render_voice_panel
from views.components.sidebar import render_planning_sidebar


class PlanningView:
    """View for meal planning UI."""

    def __init__(self):
        self.controller = PlanningController()

    def render(self):
        """Main render method."""
        st.title("Meal Planner")
        st.markdown("Chat with me to plan your meals for the week!")

        # Sidebar with recipe selection and plan summary (no voice settings)
        self._render_sidebar()

        # Start conversation if empty
        messages = self.controller.get_messages()
        if not messages:
            with st.spinner("Starting conversation..."):
                self.controller.start_conversation()
                st.rerun()

        # Two-column layout: Chat on left, Voice Panel on right
        chat_col, voice_col = st.columns([3, 1])

        with chat_col:
            self._render_chat_area()

        with voice_col:
            self._render_voice_panel()

    def _render_sidebar(self):
        """Render sidebar without voice settings."""
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

    def _render_chat_area(self):
        """Render main chat area with messages."""
        # Display chat messages using component
        render_chat_messages(self.controller.get_messages())

        # Text input as alternative
        st.markdown("---")
        user_input = st.chat_input("Or type your message...")

        if user_input:
            with st.spinner("Thinking..."):
                self.controller.send_message(user_input)
            st.rerun()

        # Quick prompts
        self._render_quick_prompts()

    def _render_voice_panel(self):
        """Render voice control panel."""
        audio_bytes = render_voice_panel(
            audio_key=self.controller.get_audio_key(),
            pending_audio=self.controller.get_pending_audio(),
            accents=self.controller.get_available_accents(),
            current_accent=self.controller.get_voice_accent(),
            on_accent_change=self.controller.set_voice_accent,
        )

        if audio_bytes:
            with st.spinner("Transcribing..."):
                success, error = self.controller.handle_voice_input(audio_bytes)

            if success:
                self.controller.increment_audio_key()
                st.rerun()
            elif error:
                st.warning(error)

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
