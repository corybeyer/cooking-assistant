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
        """Render main chat area with messages only."""
        # Display chat messages using component
        render_chat_messages(self.controller.get_messages())

    def _render_voice_panel(self):
        """Render voice control panel with all input methods."""
        # Header outside container to match chat layout
        st.markdown("### Voice Controls")

        # Wrap all controls in container to match chat container height
        voice_container = st.container(height=450)
        with voice_container:
            # Voice input
            audio_bytes = render_voice_panel(
                audio_key=self.controller.get_audio_key(),
                pending_audio=self.controller.get_pending_audio(),
                voices=self.controller.get_available_voices(),
                current_voice=self.controller.get_voice_name(),
                current_speed=self.controller.get_speed_slider_value(),
                on_voice_change=self.controller.set_voice_name,
                on_speed_change=self.controller.set_speed_from_slider,
            )

            if audio_bytes:
                with st.spinner("Transcribing..."):
                    success, error = self.controller.handle_voice_input(audio_bytes)

                if success:
                    self.controller.increment_audio_key()
                    st.rerun()
                elif error:
                    st.warning(error)

            # Text input as alternative
            st.markdown("---")
            st.markdown("**Or type:**")
            user_input = st.text_input(
                "Type your message",
                key="planning_text_input",
                placeholder="Type here...",
                label_visibility="collapsed"
            )

            if user_input:
                with st.spinner("Thinking..."):
                    self.controller.send_message(user_input)
                st.rerun()

            # Quick prompts (stacked vertically for narrow column)
            st.markdown("---")
            st.markdown("**Quick prompts:**")

            if st.button("Healthy meals", use_container_width=True, key="qp_healthy"):
                self.controller.send_message("I want healthy, nutritious meals")
                st.rerun()

            if st.button("Quick & easy", use_container_width=True, key="qp_quick"):
                self.controller.send_message("I need quick meals under 30 minutes")
                st.rerun()

            if st.button("Special occasion", use_container_width=True, key="qp_special"):
                self.controller.send_message("I'm planning for a special occasion")
                st.rerun()
