"""
Cooking Controller - manages cooking session flow and state.

This controller handles:
- Session state initialization and management
- Coordinating between services
- Rate limiting
- Voice preferences (persisted to database for authenticated users)
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional

from services.claude_service import ClaudeService
from services.recipe_service import RecipeService, RecipeSummary
from services.audio_service import AudioService
from config.database import SessionLocal
from config.auth import get_current_user
from models.repositories.user_preferences_repository import UserPreferencesRepository
from models.user_preferences import (
    UserPreferencesData,
    VOICE_OPTIONS,
    DEFAULT_VOICE_NAME,
    DEFAULT_VOICE_RATE,
    rate_to_slider_value,
    slider_value_to_rate,
)


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
        self._load_user_preferences()

    def _init_session_state(self):
        """Initialize session state if not already set."""
        if "cooking" not in st.session_state:
            st.session_state.cooking = {
                "active": False,
                "discovery_mode": True,  # Start in discovery mode
                "discovery_messages": [],
                "recipe_list": None,
                "recipe_id": None,
                "recipe_name": None,
                "recipe_context": None,
                "messages": [],
                "audio_key": 0,
                "pending_audio": None,
                "voice_name": DEFAULT_VOICE_NAME,
                "voice_rate": DEFAULT_VOICE_RATE,
                "preferences_loaded": False,
            }
        if "request_timestamps" not in st.session_state:
            st.session_state.request_timestamps = []

    def _load_user_preferences(self):
        """Load user preferences from database if authenticated."""
        # Only load once per session
        if st.session_state.cooking.get("preferences_loaded"):
            return

        user = get_current_user()
        if not user:
            st.session_state.cooking["preferences_loaded"] = True
            return

        try:
            db = SessionLocal()
            repo = UserPreferencesRepository(db)
            prefs = repo.get(user.user_id)

            st.session_state.cooking["voice_name"] = prefs.voice.name
            st.session_state.cooking["voice_rate"] = prefs.voice.rate
            st.session_state.cooking["preferences_loaded"] = True
        except Exception:
            # If loading fails, use defaults
            pass
        finally:
            db.close()

    def _save_voice_preferences(self):
        """Save voice preferences to database if authenticated."""
        user = get_current_user()
        if not user:
            return

        try:
            db = SessionLocal()
            repo = UserPreferencesRepository(db)
            repo.update_voice(
                user.user_id,
                st.session_state.cooking["voice_name"],
                st.session_state.cooking["voice_rate"]
            )
        except Exception:
            # Silently fail - preferences are non-critical
            pass
        finally:
            db.close()

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

    def is_discovery_mode(self) -> bool:
        """Check if we're in recipe discovery mode."""
        return st.session_state.cooking.get("discovery_mode", True)

    def get_discovery_messages(self) -> list[dict]:
        """Get the discovery chat message history."""
        return st.session_state.cooking.get("discovery_messages", [])

    def get_recipe_name(self) -> Optional[str]:
        """Get the current recipe name."""
        return st.session_state.cooking["recipe_name"]

    def get_messages(self) -> list[dict]:
        """Get the chat message history."""
        return st.session_state.cooking["messages"]

    def get_voice_name(self) -> str:
        """Get the current voice name (edge-tts voice ID)."""
        return st.session_state.cooking.get("voice_name", DEFAULT_VOICE_NAME)

    def set_voice_name(self, voice_name: str):
        """Set the voice name and save to database."""
        st.session_state.cooking["voice_name"] = voice_name
        self._save_voice_preferences()

    def get_voice_rate(self) -> str:
        """Get the current voice rate (e.g., '+20%')."""
        return st.session_state.cooking.get("voice_rate", DEFAULT_VOICE_RATE)

    def set_voice_rate(self, rate: str):
        """Set the voice rate and save to database."""
        st.session_state.cooking["voice_rate"] = rate
        self._save_voice_preferences()

    def get_speed_slider_value(self) -> int:
        """Get current speed as slider value (-2 to +4)."""
        return rate_to_slider_value(self.get_voice_rate())

    def set_speed_from_slider(self, slider_value: int):
        """Set voice rate from slider value."""
        self.set_voice_rate(slider_value_to_rate(slider_value))

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

    def get_available_voices(self) -> dict[str, str]:
        """Get available voices as {voice_id: display_name}."""
        return self.audio.get_available_voices()

    # Discovery mode
    def _get_recipe_list_for_claude(self) -> str:
        """Get formatted recipe list for Claude prompts."""
        if st.session_state.cooking.get("recipe_list"):
            return st.session_state.cooking["recipe_list"]

        recipes = self.recipes.get_all()
        lines = []
        for r in recipes:
            desc = f" - {r.description}" if r.description else ""
            time_info = f" (Prep: {r.prep_time or '?'}min, Cook: {r.cook_time or '?'}min)" if r.prep_time or r.cook_time else ""
            lines.append(f"- ID {r.id}: {r.name}{desc}{time_info}")

        recipe_list = "\n".join(lines) if lines else "No recipes available."
        st.session_state.cooking["recipe_list"] = recipe_list
        return recipe_list

    def init_discovery(self) -> bool:
        """
        Initialize discovery mode with a greeting from Claude.
        Returns True if greeting was generated.
        """
        if st.session_state.cooking.get("discovery_messages"):
            return True  # Already initialized

        recipe_list = self._get_recipe_list_for_claude()
        greeting = self.claude.get_discovery_greeting(recipe_list)

        st.session_state.cooking["discovery_messages"] = [
            {"role": "assistant", "content": greeting}
        ]
        return True

    def send_discovery_message(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Send a message in discovery mode.

        Returns (success, error_message)
        """
        if not self._check_rate_limit():
            return False, "Too many requests. Please wait a moment."

        state = st.session_state.cooking
        recipe_list = self._get_recipe_list_for_claude()

        # Get Claude response
        response_text, selected_recipe_id = self.claude.chat_discovery(
            text,
            recipe_list,
            state["discovery_messages"]
        )

        # Update message history
        state["discovery_messages"].append({"role": "user", "content": text})
        state["discovery_messages"].append({"role": "assistant", "content": response_text})

        # If Claude selected a recipe, start the cooking session
        if selected_recipe_id:
            self.start_session(selected_recipe_id)

        return True, None

    def handle_discovery_voice_input(self, audio_bytes: bytes) -> tuple[bool, Optional[str]]:
        """
        Process voice input in discovery mode.

        Returns (success, error_message)
        """
        text = self.audio.transcribe(audio_bytes)
        if not text:
            return False, "Could not understand audio. Please try again."

        return self.send_discovery_message(text)

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
            "discovery_mode": False,
            "discovery_messages": [],
            "recipe_list": None,
            "recipe_id": recipe_id,
            "recipe_name": recipe.Name,
            "recipe_context": context,
            "messages": [
                {"role": "user", "content": initial_msg},
                {"role": "assistant", "content": response}
            ],
            "audio_key": 0,
            "pending_audio": None,
            "voice_name": st.session_state.cooking.get("voice_name", DEFAULT_VOICE_NAME),
            "voice_rate": st.session_state.cooking.get("voice_rate", DEFAULT_VOICE_RATE),
            "preferences_loaded": True,  # Keep loaded state
        }

        return True

    def end_session(self):
        """End the current cooking session and return to discovery mode."""
        st.session_state.cooking = {
            "active": False,
            "discovery_mode": True,
            "discovery_messages": [],  # Reset discovery for fresh start
            "recipe_list": None,
            "recipe_id": None,
            "recipe_name": None,
            "recipe_context": None,
            "messages": [],
            "audio_key": 0,
            "pending_audio": None,
            "voice_name": st.session_state.cooking.get("voice_name", DEFAULT_VOICE_NAME),
            "voice_rate": st.session_state.cooking.get("voice_rate", DEFAULT_VOICE_RATE),
            "preferences_loaded": True,  # Keep loaded state
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

        # Generate TTS audio with voice preferences
        audio_bytes = self.audio.text_to_speech(
            response,
            voice=state.get("voice_name", DEFAULT_VOICE_NAME),
            rate=state.get("voice_rate", DEFAULT_VOICE_RATE)
        )
        if audio_bytes:
            state["pending_audio"] = audio_bytes

        return True, None
