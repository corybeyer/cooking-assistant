"""
Cooking Controller - manages cooking session flow and state.

This controller handles:
- Session state initialization and management
- Coordinating between services
- Rate limiting
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional

from services.claude_service import ClaudeService
from services.recipe_service import RecipeService, RecipeSummary
from services.audio_service import AudioService


# Rate limit configuration
RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60


class CookingController:
    """Controller for cooking session management."""

    def __init__(self):
        self.claude = ClaudeService()
        self.recipes = RecipeService()
        self.audio = AudioService()
        self._init_session_state()

    def _init_session_state(self):
        """Initialize session state if not already set."""
        if "cooking" not in st.session_state:
            st.session_state.cooking = {
                "active": False,
                "recipe_id": None,
                "recipe_name": None,
                "recipe_context": None,
                "messages": [],
                "audio_key": 0,
                "pending_audio": None,
                "voice_accent": "American 🇺🇸",
            }
        if "request_timestamps" not in st.session_state:
            st.session_state.request_timestamps = []

    def _check_rate_limit(self) -> bool:
        """Check if user has exceeded rate limit. Returns True if allowed."""
        now = datetime.now()
        window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)

        # Remove timestamps outside the window
        st.session_state.request_timestamps = [
            ts for ts in st.session_state.request_timestamps if ts > window_start
        ]

        # Check if under limit
        if len(st.session_state.request_timestamps) >= RATE_LIMIT_MAX_REQUESTS:
            return False

        # Record this request
        st.session_state.request_timestamps.append(now)
        return True

    # Session state accessors
    def is_session_active(self) -> bool:
        """Check if a cooking session is active."""
        return st.session_state.cooking["active"]

    def get_recipe_name(self) -> Optional[str]:
        """Get the current recipe name."""
        return st.session_state.cooking["recipe_name"]

    def get_messages(self) -> list[dict]:
        """Get the chat message history."""
        return st.session_state.cooking["messages"]

    def get_voice_accent(self) -> str:
        """Get the current voice accent."""
        return st.session_state.cooking["voice_accent"]

    def set_voice_accent(self, accent: str):
        """Set the voice accent."""
        st.session_state.cooking["voice_accent"] = accent

    def get_pending_audio(self) -> Optional[bytes]:
        """Get pending audio for playback and clear it."""
        audio = st.session_state.cooking["pending_audio"]
        st.session_state.cooking["pending_audio"] = None
        return audio

    def get_audio_key(self) -> int:
        """Get current audio input key for widget uniqueness."""
        return st.session_state.cooking["audio_key"]

    def increment_audio_key(self):
        """Increment audio key to reset widget."""
        st.session_state.cooking["audio_key"] += 1

    # Recipe operations
    def get_recipes(self) -> list[RecipeSummary]:
        """Get all available recipes."""
        return self.recipes.get_all()

    def get_available_accents(self) -> list[str]:
        """Get available voice accents."""
        return self.audio.get_available_accents()

    # Session lifecycle
    def start_session(self, recipe_id: int) -> bool:
        """
        Start a cooking session for the given recipe.

        Returns True if session started successfully.
        """
        recipe = self.recipes.get_by_id(recipe_id)
        if not recipe:
            return False

        context = self.recipes.format_for_claude(recipe)

        # Get initial response from Claude
        initial_msg = "Let's gather ingredients first. What do I need for this recipe?"
        response = self.claude.chat_cooking(initial_msg, context, [])

        st.session_state.cooking = {
            "active": True,
            "recipe_id": recipe_id,
            "recipe_name": recipe.Name,
            "recipe_context": context,
            "messages": [
                {"role": "user", "content": initial_msg},
                {"role": "assistant", "content": response}
            ],
            "audio_key": 0,
            "pending_audio": None,
            "voice_accent": st.session_state.cooking.get("voice_accent", "American 🇺🇸"),
        }

        return True

    def end_session(self):
        """End the current cooking session."""
        st.session_state.cooking = {
            "active": False,
            "recipe_id": None,
            "recipe_name": None,
            "recipe_context": None,
            "messages": [],
            "audio_key": 0,
            "pending_audio": None,
            "voice_accent": st.session_state.cooking.get("voice_accent", "American 🇺🇸"),
        }

    # Message handling
    def handle_voice_input(self, audio_bytes: bytes) -> tuple[bool, Optional[str]]:
        """
        Process voice input.

        Returns (success, error_message)
        """
        text = self.audio.transcribe(audio_bytes)
        if not text:
            return False, "Could not understand audio. Please try again."

        return self.send_message(text)

    def send_message(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Send a message to Claude.

        Returns (success, error_message)
        """
        if not self._check_rate_limit():
            return False, "Too many requests. Please wait a moment."

        state = st.session_state.cooking

        # Get Claude response
        response = self.claude.chat_cooking(
            text,
            state["recipe_context"],
            state["messages"]
        )

        # Update message history
        state["messages"].append({"role": "user", "content": text})
        state["messages"].append({"role": "assistant", "content": response})

        # Generate TTS audio
        audio_bytes = self.audio.text_to_speech(response, state["voice_accent"])
        if audio_bytes:
            state["pending_audio"] = audio_bytes

        return True, None
