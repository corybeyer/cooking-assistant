"""
Voice Panel Component - reusable voice controls for chat interfaces.

This component provides a consistent voice control experience across
different views (Cooking, Planning) with:
- Push to talk microphone button
- Audio playback with native HTML5 controls
- Voice accent selector
"""

import streamlit as st
from typing import Optional, Callable


def render_voice_panel(
    audio_key: int,
    pending_audio: Optional[bytes],
    accents: list[str],
    current_accent: str,
    on_accent_change: Callable[[str], None],
) -> Optional[bytes]:
    """
    Render the voice control panel.

    Args:
        audio_key: Unique key for the audio input widget
        pending_audio: Audio bytes to play (if any)
        accents: List of available voice accents
        current_accent: Currently selected accent
        on_accent_change: Callback when accent changes

    Returns:
        Audio bytes if recording captured, None otherwise
    """
    # Custom CSS for the voice panel
    st.markdown("""
    <style>
        /* Make the audio input button larger and more touch-friendly */
        div[data-testid="stAudioInput"] > button {
            height: 80px !important;
            min-height: 80px !important;
            font-size: 20px !important;
            border-radius: 40px !important;
        }
        div[data-testid="stAudioInput"] {
            display: flex;
            justify-content: center;
        }
    </style>
    """, unsafe_allow_html=True)

    # Push to talk section
    st.markdown("**Tap to Talk**")

    audio = st.audio_input(
        "Record your message",
        key=f"audio_input_{audio_key}",
        label_visibility="collapsed"
    )

    recorded_bytes = None
    if audio:
        recorded_bytes = audio.read()

    # Audio playback section
    if pending_audio:
        st.markdown("**Response**")
        st.audio(pending_audio, format="audio/mp3", autoplay=True)

    st.markdown("---")

    # Accent selector
    st.markdown("**Voice Accent**")
    selected_accent = st.selectbox(
        "Select accent:",
        options=accents,
        index=accents.index(current_accent) if current_accent in accents else 0,
        label_visibility="collapsed",
        key="voice_panel_accent"
    )

    if selected_accent != current_accent:
        on_accent_change(selected_accent)

    return recorded_bytes
