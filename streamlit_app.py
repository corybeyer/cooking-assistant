"""
Cooking Assistant - Streamlit App

A voice-enabled cooking assistant that guides you through recipes
using Claude AI. Features:
- Voice input via st.audio_input + Google Speech Recognition (free, no API key)
- Text-to-speech responses
- Ingredient prep phase before cooking
- Step-by-step cooking guidance
"""

import streamlit as st
import anthropic
import speech_recognition as sr
from gtts import gTTS
import tempfile
import os
from io import BytesIO

from sqlalchemy.orm import joinedload

import logging
from datetime import datetime, timedelta

from app.config import get_settings
from app.database import SessionLocal
from app.models import Recipe, RecipeIngredient

# Configure logging (server-side only, not exposed to users)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Cooking Assistant",
    page_icon="🍳",
    layout="wide"
)

settings = get_settings()


# ============================================
# Authentication
# ============================================

def check_password() -> bool:
    """Simple password authentication gate."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("🍳 Cooking Assistant")
    st.markdown("### Please sign in to continue")

    password = st.text_input("Password", type="password", key="password_input")

    if st.button("Sign In", type="primary"):
        if password == settings.app_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
            logger.warning("Failed login attempt")

    return False


# ============================================
# Rate Limiting
# ============================================

# Rate limit: max requests per time window
RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60


def check_rate_limit() -> bool:
    """Check if user has exceeded rate limit. Returns True if allowed."""
    now = datetime.now()

    if "request_timestamps" not in st.session_state:
        st.session_state.request_timestamps = []

    # Remove timestamps outside the window
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    st.session_state.request_timestamps = [
        ts for ts in st.session_state.request_timestamps if ts > window_start
    ]

    # Check if under limit
    if len(st.session_state.request_timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        return False

    # Record this request
    st.session_state.request_timestamps.append(now)
    return True

# Initialize API clients
anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
recognizer = sr.Recognizer()


# ============================================
# Database Functions
# ============================================

@st.cache_data(ttl=300)
def load_recipes():
    """Load all recipes from database."""
    db = SessionLocal()
    try:
        recipes = db.query(Recipe).all()
        return [
            {
                "id": r.RecipeId,
                "name": r.Name,
                "description": r.Description,
                "prep_time": r.PrepTime,
                "cook_time": r.CookTime,
                "servings": r.Servings,
            }
            for r in recipes
        ]
    finally:
        db.close()


def get_recipe_context(recipe_id: int) -> tuple[str, str]:
    """Get full recipe details formatted for Claude."""
    db = SessionLocal()
    try:
        recipe = db.query(Recipe).options(
            joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient),
            joinedload(Recipe.ingredients).joinedload(RecipeIngredient.unit),
            joinedload(Recipe.steps)
        ).filter(Recipe.RecipeId == recipe_id).first()
        if not recipe:
            return None, None

        lines = [
            f"# {recipe.Name}",
            "",
            f"**Description:** {recipe.Description or 'No description'}",
            f"**Cuisine:** {recipe.Cuisine or 'Not specified'}",
            f"**Category:** {recipe.Category or 'Not specified'}",
            f"**Prep Time:** {recipe.PrepTime or '?'} minutes",
            f"**Cook Time:** {recipe.CookTime or '?'} minutes",
            f"**Servings:** {recipe.Servings or '?'}",
            "",
            "## Ingredients",
        ]

        for ri in sorted(recipe.ingredients, key=lambda x: x.OrderIndex):
            unit = ri.unit.UnitName if ri.unit else ""
            line = f"- {ri.Quantity or ''} {unit} {ri.ingredient.Name}".strip()
            lines.append(line)

        lines.extend(["", "## Steps"])

        for step in sorted(recipe.steps, key=lambda x: x.OrderIndex):
            lines.append(f"{step.OrderIndex}. {step.Description}")

        return recipe.Name, "\n".join(lines)
    finally:
        db.close()


# ============================================
# Audio Functions
# ============================================

def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe audio using Google Speech Recognition (free, no API key needed)."""
    temp_path = None
    try:
        # Save audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        # Use speech_recognition to transcribe
        with sr.AudioFile(temp_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except sr.UnknownValueError:
        st.warning("Could not understand audio. Please try again.")
        return ""
    except sr.RequestError as e:
        logger.error(f"Speech recognition service error: {e}")
        st.error("Speech recognition service is unavailable. Please try again later.")
        return ""
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        st.error("An error occurred processing audio. Please try again.")
        return ""
    finally:
        # Always clean up temp file to prevent disk space exhaustion
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def text_to_speech(text: str) -> bytes | None:
    """Convert text to speech and return audio bytes."""
    try:
        tts = gTTS(text=text, lang='en', tld='co.uk')  # British accent
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.read()
    except Exception as e:
        logger.error(f"TTS error: {e}")
        st.error("Text-to-speech is unavailable. Please try again later.")
        return None


# ============================================
# Claude Chat
# ============================================

SYSTEM_PROMPT = """You are a friendly, helpful cooking assistant guiding someone through a recipe.
You have the complete recipe loaded and are helping them cook it step by step.

Your personality:
- Warm and encouraging, like a friend who loves cooking
- Patient with questions and mistakes
- Concise - they're cooking with messy hands, keep responses brief
- Practical - offer substitutions, timing tips, and troubleshooting

COOKING PHASES:
1. PREP PHASE (start here): Help them gather and prepare all ingredients first.
   - When asked about ingredients, list them clearly
   - Mention any prep work (chopping, measuring, bringing to room temp)
   - Ask if they have everything or need substitutions
   - Only move to cooking when they say "ready", "let's start", "I have everything", etc.

2. COOKING PHASE: Guide through steps one at a time.
   - Give one step at a time, wait for "next" or "what's next"
   - Answer questions about techniques or timing
   - Help with troubleshooting ("is it done yet?", "it looks wrong")

Keep responses SHORT (1-3 sentences) unless they ask for detail.

Here is the recipe you're helping with:

{recipe_context}
"""


def chat_with_claude(user_message: str, recipe_context: str, history: list) -> str:
    """Send message to Claude and get response."""
    messages = history + [{"role": "user", "content": user_message}]

    response = anthropic_client.messages.create(
        model=settings.claude_model,
        max_tokens=500,
        system=SYSTEM_PROMPT.format(recipe_context=recipe_context),
        messages=messages
    )

    return response.content[0].text


# ============================================
# Session State
# ============================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "recipe_id" not in st.session_state:
    st.session_state.recipe_id = None

if "recipe_name" not in st.session_state:
    st.session_state.recipe_name = None

if "recipe_context" not in st.session_state:
    st.session_state.recipe_context = None

if "cooking_started" not in st.session_state:
    st.session_state.cooking_started = False

if "audio_key" not in st.session_state:
    st.session_state.audio_key = 0

if "pending_audio" not in st.session_state:
    st.session_state.pending_audio = None


def start_cooking(recipe_id: int):
    """Start a cooking session for the selected recipe."""
    name, context = get_recipe_context(recipe_id)
    if name:
        st.session_state.recipe_id = recipe_id
        st.session_state.recipe_name = name
        st.session_state.recipe_context = context
        st.session_state.cooking_started = True
        st.session_state.messages = []

        # Send initial message
        initial_msg = "Let's gather ingredients first. What do I need for this recipe?"
        response = chat_with_claude(initial_msg, context, [])
        st.session_state.messages = [
            {"role": "user", "content": initial_msg},
            {"role": "assistant", "content": response}
        ]


def end_cooking():
    """End the current cooking session."""
    st.session_state.recipe_id = None
    st.session_state.recipe_name = None
    st.session_state.recipe_context = None
    st.session_state.cooking_started = False
    st.session_state.messages = []


# ============================================
# UI
# ============================================

# Authentication gate - must pass before accessing app
if not check_password():
    st.stop()

st.title("🍳 Cooking Assistant")

if not st.session_state.cooking_started:
    # Recipe Selection
    st.markdown("### Select a Recipe")

    recipes = load_recipes()

    if recipes:
        recipe_options = {r["name"]: r["id"] for r in recipes}
        selected_name = st.selectbox(
            "Choose what to cook:",
            options=[""] + list(recipe_options.keys()),
            format_func=lambda x: "Select a recipe..." if x == "" else x
        )

        if selected_name:
            recipe = next(r for r in recipes if r["name"] == selected_name)
            st.markdown(f"""
            **{recipe['description'] or 'No description'}**

            ⏱️ Prep: {recipe['prep_time'] or '?'} min | 🍳 Cook: {recipe['cook_time'] or '?'} min | 🍽️ Serves: {recipe['servings'] or '?'}
            """)

            if st.button("🚀 Start Cooking", type="primary", use_container_width=True):
                start_cooking(recipe_options[selected_name])
                st.rerun()
    else:
        st.warning("No recipes found. Add some recipes to the database.")

else:
    # Cooking Session - Sidebar for controls
    with st.sidebar:
        st.markdown(f"### 📖 {st.session_state.recipe_name}")
        st.markdown("---")

        # Voice Input
        st.markdown("**🎤 Voice Input**")
        audio = st.audio_input(
            "Tap to record",
            key=f"audio_input_{st.session_state.audio_key}"
        )

        if audio:
            with st.spinner("Transcribing..."):
                text = transcribe_audio(audio.read())
                if text:
                    st.session_state.pending_message = text
                    st.session_state.audio_key += 1

        st.markdown("---")

        # Text Input
        st.markdown("**⌨️ Text Input**")
        text_input = st.text_input(
            "Type your message:",
            key="text_input",
            placeholder="What's next?",
            label_visibility="collapsed"
        )

        st.markdown("---")

        # End session button
        if st.button("🛑 End Cooking Session", type="secondary", use_container_width=True):
            end_cooking()
            st.rerun()

    # Main area - Chat history (full width, taller)
    st.markdown("### 💬 Chat")
    chat_container = st.container(height=600)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # Play pending audio (from previous response) using safe st.audio component
    if st.session_state.pending_audio:
        st.audio(st.session_state.pending_audio, format="audio/mp3", autoplay=True)
        st.session_state.pending_audio = None

    # Process message (from voice or text)
    message_to_send = None

    if hasattr(st.session_state, 'pending_message') and st.session_state.pending_message:
        message_to_send = st.session_state.pending_message
        st.session_state.pending_message = None
    elif text_input:
        message_to_send = text_input

    if message_to_send:
        # Check rate limit before processing
        if not check_rate_limit():
            st.error("Too many requests. Please wait a moment before trying again.")
        else:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": message_to_send})

            # Get Claude response
            with st.spinner("Thinking..."):
                response = chat_with_claude(
                    message_to_send,
                    st.session_state.recipe_context,
                    st.session_state.messages[:-1]  # Exclude the message we just added
                )

            st.session_state.messages.append({"role": "assistant", "content": response})

            # Generate TTS and store for playback after rerun
            audio_bytes = text_to_speech(response)
            if audio_bytes:
                st.session_state.pending_audio = audio_bytes

            st.rerun()
