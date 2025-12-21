"""
Audio UI components for voice input/output.
"""

import streamlit as st
from typing import Optional


def render_mic_button(audio_key: int) -> Optional[bytes]:
    """
    Render a large microphone button for voice input.

    Args:
        audio_key: Unique key for the audio input widget

    Returns:
        Audio bytes if recording captured, None otherwise
    """
    # Custom CSS for large mic button
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

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<h3 style='text-align: center;'>🎤 Tap to Talk</h3>", unsafe_allow_html=True)
        audio = st.audio_input(
            "Record your message",
            key=f"audio_input_{audio_key}",
            label_visibility="collapsed"
        )

        if audio:
            return audio.read()

    return None


def render_audio_playback(audio_bytes: Optional[bytes]):
    """
    Render audio playback if audio is available.

    Args:
        audio_bytes: MP3 audio bytes to play
    """
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
