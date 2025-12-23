"""
Cooking View - UI for cooking sessions.

This view handles all rendering for the cooking assistant.
It delegates business logic to the CookingController.
"""

import streamlit as st

from controllers.cooking_controller import CookingController
from views.components.chat import render_chat_messages
from views.components.voice_panel import render_voice_panel
from views.components.sidebar import render_cooking_sidebar


class CookingView:
    """View for cooking session UI."""

    def __init__(self):
        self.controller = CookingController()

    def render(self):
        """Main render method - displays appropriate UI based on state."""
        st.title("Cooking Assistant")

        if self.controller.is_session_active():
            self._render_cooking_session()
        elif self.controller.is_discovery_mode():
            self._render_discovery_chat()
        else:
            self._render_recipe_selection()

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

    def _render_discovery_chat(self):
        """Render the chat-first discovery interface."""
        # Initialize discovery with greeting if needed
        self.controller.init_discovery()

        st.markdown("Let's find something to cook!")

        # Two-column layout: Chat on left, Voice Panel on right
        chat_col, voice_col = st.columns([3, 1])

        with chat_col:
            # Display discovery chat messages
            messages = self.controller.get_discovery_messages()
            render_chat_messages(messages)

        with voice_col:
            self._render_discovery_voice_panel()

    def _render_discovery_voice_panel(self):
        """Render voice control panel for discovery mode."""
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
                    success, error = self.controller.handle_discovery_voice_input(audio_bytes)

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
                key="discovery_text_input",
                placeholder="Type here...",
                label_visibility="collapsed"
            )

            if user_input:
                with st.spinner("Thinking..."):
                    self.controller.send_discovery_message(user_input)
                st.rerun()

            # Quick prompts for discovery
            st.markdown("---")
            st.markdown("**Quick prompts:**")

            if st.button("Something quick", use_container_width=True, key="qp_quick_disc"):
                self.controller.send_discovery_message("I want something quick and easy")
                st.rerun()

            if st.button("Comfort food", use_container_width=True, key="qp_comfort"):
                self.controller.send_discovery_message("I'm in the mood for comfort food")
                st.rerun()

            if st.button("Surprise me!", use_container_width=True, key="qp_surprise"):
                self.controller.send_discovery_message("Surprise me with a recommendation!")
                st.rerun()

    def _render_cooking_session(self):
        """Render active cooking session."""
        # Sidebar (without voice settings)
        render_cooking_sidebar(
            recipe_name=self.controller.get_recipe_name(),
            on_text_submit=self.controller.send_message,
            on_end_session=self.controller.end_session,
        )

        # Two-column layout: Chat on left, Voice Panel on right
        chat_col, voice_col = st.columns([3, 1])

        with chat_col:
            self._render_chat_area()

        with voice_col:
            self._render_voice_panel()

    def _render_chat_area(self):
        """Render main chat area with messages."""
        # Display chat messages in scrollable container (header is in component)
        render_chat_messages(self.controller.get_messages())

    def _render_voice_panel(self):
        """Render voice control panel."""
        # Header outside container to match chat layout
        st.markdown("### Voice Controls")

        # Wrap controls in container to match chat container height
        voice_container = st.container(height=450)
        with voice_container:
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
                key="cooking_text_input",
                placeholder="Type here...",
                label_visibility="collapsed"
            )

            if user_input:
                with st.spinner("Thinking..."):
                    self.controller.send_message(user_input)
                st.rerun()

            # Quick prompts (cooking-specific)
            st.markdown("---")
            st.markdown("**Quick prompts:**")

            if st.button("What's next?", use_container_width=True, key="qp_next"):
                self.controller.send_message("What's the next step?")
                st.rerun()

            if st.button("Can I substitute?", use_container_width=True, key="qp_substitute"):
                self.controller.send_message("What substitutions can I make?")
                st.rerun()

            if st.button("How long left?", use_container_width=True, key="qp_time"):
                self.controller.send_message("How much time is left?")
                st.rerun()
