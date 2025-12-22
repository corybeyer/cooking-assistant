"""
Cooking View - UI for cooking sessions.

This view handles all rendering for the cooking assistant.
It delegates business logic to the CookingController.
"""

import streamlit as st

from controllers.cooking_controller import CookingController
from views.components.chat import render_chat_messages
from views.components.audio import render_mic_button, render_audio_playback
from views.components.sidebar import render_cooking_sidebar


class CookingView:
    """View for cooking session UI."""

    def __init__(self):
        self.controller = CookingController()

    def render(self):
        """Main render method - displays appropriate UI based on state."""
        st.title("Cooking Assistant")

        if not self.controller.is_session_active():
            self._render_recipe_selection()
        else:
            self._render_cooking_session()

    def _render_recipe_selection(self):
        """Render recipe selection screen."""
        st.markdown("### Select a Recipe")

        recipes = self.controller.get_recipes()

        if not recipes:
            st.warning("No recipes found. Add some recipes to the database.")
            return

        recipe_options = {r.name: r.id for r in recipes}
        selected_name = st.selectbox(
            "Choose what to cook:",
            options=[""] + list(recipe_options.keys()),
            format_func=lambda x: "Select a recipe..." if x == "" else x
        )

        if selected_name:
            recipe = next(r for r in recipes if r.name == selected_name)
            st.markdown(f"""
            **{recipe.description or 'No description'}**

            Prep: {recipe.prep_time or '?'} min | Cook: {recipe.cook_time or '?'} min | Serves: {recipe.servings or '?'}
            """)

            if st.button("Start Cooking", type="primary", use_container_width=True):
                if self.controller.start_session(recipe_options[selected_name]):
                    st.rerun()
                else:
                    st.error("Failed to start cooking session.")

    def _render_cooking_session(self):
        """Render active cooking session."""
        # Sidebar
        render_cooking_sidebar(
            recipe_name=self.controller.get_recipe_name(),
            accents=self.controller.get_available_accents(),
            current_accent=self.controller.get_voice_accent(),
            on_accent_change=self.controller.set_voice_accent,
            on_text_submit=self.controller.send_message,
            on_end_session=self.controller.end_session,
        )

        # Main chat area
        self._render_chat_area()

    def _render_chat_area(self):
        """Render main chat area with messages and voice input."""
        st.markdown("### Chat")

        # Display chat messages
        render_chat_messages(self.controller.get_messages())

        # Play any pending audio
        pending_audio = self.controller.get_pending_audio()
        render_audio_playback(pending_audio)

        # Voice input button
        audio_bytes = render_mic_button(self.controller.get_audio_key())

        if audio_bytes:
            with st.spinner("Transcribing..."):
                success, error = self.controller.handle_voice_input(audio_bytes)

            if success:
                self.controller.increment_audio_key()
                st.rerun()
            elif error:
                st.warning(error)
