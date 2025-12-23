"""
Planning Controller - manages meal planning session flow and state.

This controller handles:
- Planning conversation with Claude
- Recipe selection and confirmation
- Creating shopping lists from confirmed plans (owned by authenticated user)
- Voice input/output for hands-free planning
- Voice preferences (persisted to database for authenticated users)

Multi-user support:
- Shopping lists created from plans are owned by the authenticated user
"""

import streamlit as st
from typing import Optional
from datetime import datetime

from services.claude_service import ClaudeService
from services.recipe_service import RecipeService, RecipeSummary
from services.shopping_list_service import ShoppingListService
from services.audio_service import AudioService
from config.database import SessionLocal
from config.auth import get_current_user, require_auth
from models.repositories.user_preferences_repository import UserPreferencesRepository
from models.user_preferences import (
    VOICE_OPTIONS,
    DEFAULT_VOICE_NAME,
    DEFAULT_VOICE_RATE,
    rate_to_slider_value,
    slider_value_to_rate,
)


class PlanningController:
    """Controller for meal planning session management."""

    def __init__(self):
        self.claude = ClaudeService()
        self.recipes = RecipeService()
        self.audio = AudioService()
        self._init_session_state()
        self._load_user_preferences()

    def _init_session_state(self):
        """Initialize session state if not already set."""
        if "planning" not in st.session_state:
            st.session_state.planning = {
                "messages": [],
                "selected_recipes": [],  # List of recipe IDs confirmed for the plan
                "plan_confirmed": False,
                "shopping_list_id": None,
                "audio_key": 0,
                "pending_audio": None,
                "voice_name": DEFAULT_VOICE_NAME,
                "voice_rate": DEFAULT_VOICE_RATE,
                "preferences_loaded": False,
            }

    def _load_user_preferences(self):
        """Load user preferences from database if authenticated."""
        # Only load once per session
        if st.session_state.planning.get("preferences_loaded"):
            return

        user = get_current_user()
        if not user:
            st.session_state.planning["preferences_loaded"] = True
            return

        try:
            db = SessionLocal()
            repo = UserPreferencesRepository(db)
            prefs = repo.get(user.user_id)

            st.session_state.planning["voice_name"] = prefs.voice.name
            st.session_state.planning["voice_rate"] = prefs.voice.rate
            st.session_state.planning["preferences_loaded"] = True
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
                st.session_state.planning["voice_name"],
                st.session_state.planning["voice_rate"]
            )
        except Exception:
            # Silently fail - preferences are non-critical
            pass
        finally:
            db.close()

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
    # Voice State Accessors
    # ==========================================

    def get_voice_name(self) -> str:
        """Get the current voice name (edge-tts voice ID)."""
        return st.session_state.planning.get("voice_name", DEFAULT_VOICE_NAME)

    def set_voice_name(self, voice_name: str):
        """Set the voice name and save to database."""
        st.session_state.planning["voice_name"] = voice_name
        self._save_voice_preferences()

    def get_voice_rate(self) -> str:
        """Get the current voice rate (e.g., '+20%')."""
        return st.session_state.planning.get("voice_rate", DEFAULT_VOICE_RATE)

    def set_voice_rate(self, rate: str):
        """Set the voice rate and save to database."""
        st.session_state.planning["voice_rate"] = rate
        self._save_voice_preferences()

    def get_speed_slider_value(self) -> int:
        """Get current speed as slider value (-2 to +4)."""
        return rate_to_slider_value(self.get_voice_rate())

    def set_speed_from_slider(self, slider_value: int):
        """Set voice rate from slider value."""
        self.set_voice_rate(slider_value_to_rate(slider_value))

    def get_pending_audio(self) -> Optional[bytes]:
        """Get pending audio for playback and clear it."""
        audio = st.session_state.planning.get("pending_audio")
        st.session_state.planning["pending_audio"] = None
        return audio

    def get_audio_key(self) -> int:
        """Get current audio input key for widget uniqueness."""
        return st.session_state.planning.get("audio_key", 0)

    def increment_audio_key(self):
        """Increment audio key to reset widget."""
        st.session_state.planning["audio_key"] = self.get_audio_key() + 1

    def get_available_voices(self) -> dict[str, str]:
        """Get available voices as {voice_id: display_name}."""
        return self.audio.get_available_voices()

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

    def send_message(self, user_message: str, with_voice: bool = False) -> str:
        """
        Send a message to Claude for meal planning.

        Args:
            user_message: The user's message
            with_voice: If True, generate TTS audio for the response

        Returns Claude's response.
        """
        recipe_list = self.get_recipe_context_for_claude()
        history = st.session_state.planning["messages"]

        # Get Claude's response with potential tool calls
        response, recipe_ids_to_add = self.claude.chat_planning(user_message, recipe_list, history)

        # Add any recipes Claude suggested to the plan
        for recipe_id in recipe_ids_to_add:
            self.add_recipe_to_plan(recipe_id)

        # Update message history
        st.session_state.planning["messages"].append({
            "role": "user",
            "content": user_message
        })
        st.session_state.planning["messages"].append({
            "role": "assistant",
            "content": response
        })

        # Generate TTS audio if voice mode
        if with_voice and response:
            audio_bytes = self.audio.text_to_speech(
                response,
                voice=self.get_voice_name(),
                rate=self.get_voice_rate()
            )
            if audio_bytes:
                st.session_state.planning["pending_audio"] = audio_bytes

        return response

    def handle_voice_input(self, audio_bytes: bytes) -> tuple[bool, Optional[str]]:
        """
        Process voice input.

        Returns (success, error_message)
        """
        text = self.audio.transcribe(audio_bytes)
        if not text:
            return False, "Could not understand audio. Please try again."

        self.send_message(text, with_voice=True)
        return True, None

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
            "audio_key": 0,
            "pending_audio": None,
            "voice_name": st.session_state.planning.get("voice_name", DEFAULT_VOICE_NAME),
            "voice_rate": st.session_state.planning.get("voice_rate", DEFAULT_VOICE_RATE),
            "preferences_loaded": True,  # Keep loaded state
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

        Requires authentication - the shopping list will be owned by the current user.

        Args:
            plan_name: Optional name for the plan
            use_smart_aggregation: If True, use Claude for intelligent quantity aggregation

        Returns the shopping list ID.

        Raises:
            ValueError: If no recipes selected or user not authenticated
        """
        # Require authentication to create shopping lists
        user = require_auth()

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
                user_id=user.user_id,
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
