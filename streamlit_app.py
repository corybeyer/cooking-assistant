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
import base64
import os
from io import BytesIO

from app.config import get_settings
from app.database import SessionLocal
from app.models import Recipe

# Page config
st.set_page_config(
    page_title="Cooking Assistant",
    page_icon="🍳",
    layout="centered"
)

settings = get_settings()

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
        recipe = db.get(Recipe, recipe_id)
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
        st.error(f"Speech recognition service error: {e}")
        return ""
    except Exception as e:
        st.error(f"Transcription error: {e}")
        return ""
    finally:
        # Always clean up temp file to prevent disk space exhaustion
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def text_to_speech(text: str) -> str:
    """Convert text to speech and return audio HTML."""
    try:
        tts = gTTS(text=text, lang='en', tld='co.uk')  # British accent
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)

        audio_base64 = base64.b64encode(audio_buffer.read()).decode()
        audio_html = f"""
            <audio autoplay>
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            </audio>
        """
        return audio_html
    except Exception as e:
        st.error(f"TTS error: {e}")
        return ""


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
    # Cooking Session
    st.markdown(f"### 📖 {st.session_state.recipe_name}")

    # Chat history
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # Input methods
    st.markdown("---")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**🎤 Voice Input**")
        audio = st.audio_input("Tap to record", key="audio_input")

        if audio:
            with st.spinner("Transcribing..."):
                text = transcribe_audio(audio.read())
                if text:
                    st.session_state.pending_message = text
                    st.info(f'You said: "{text}"')

    with col2:
        st.markdown("**⌨️ Text Input**")
        text_input = st.text_input(
            "Type your message:",
            key="text_input",
            placeholder="What's next?",
            label_visibility="collapsed"
        )

    # Process message (from voice or text)
    message_to_send = None

    if hasattr(st.session_state, 'pending_message') and st.session_state.pending_message:
        message_to_send = st.session_state.pending_message
        st.session_state.pending_message = None
    elif text_input:
        message_to_send = text_input

    if message_to_send:
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

        # Text-to-speech
        audio_html = text_to_speech(response)
        if audio_html:
            st.markdown(audio_html, unsafe_allow_html=True)

        st.rerun()

    # End session button
    st.markdown("---")
    if st.button("🛑 End Cooking Session", type="secondary"):
        end_cooking()
        st.rerun()
