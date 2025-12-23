"""
Voice Panel Component - reusable voice controls for chat interfaces.

This component provides a consistent voice control experience across
different views (Cooking, Planning) with:
- Push to talk microphone button
- Audio playback with native HTML5 controls
- Voice selector (edge-tts neural voices)
- Speed slider
"""

import streamlit as st
from typing import Optional, Callable

from models.user_preferences import VOICE_OPTIONS, SPEED_OPTIONS


# Speed labels for the slider
SPEED_LABELS = {
    -2: "Slower",
    -1: "Slow",
    0: "Normal",
    1: "Fast",
    2: "Faster",
    3: "Quick",
    4: "Rapid",
}


def render_voice_panel(
    audio_key: int,
    pending_audio: Optional[bytes],
    voices: dict[str, str],
    current_voice: str,
    current_speed: int,
    on_voice_change: Callable[[str], None],
    on_speed_change: Callable[[int], None],
) -> Optional[bytes]:
    """
    Render the voice control panel.

    Args:
        audio_key: Unique key for the audio input widget
        pending_audio: Audio bytes to play (if any)
        voices: Dict of {voice_id: display_name}
        current_voice: Currently selected voice ID
        current_speed: Current speed slider value (-2 to +4)
        on_voice_change: Callback when voice changes (receives voice_id)
        on_speed_change: Callback when speed changes (receives slider value)

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

    # Voice selector
    st.markdown("**Voice**")
    voice_ids = list(voices.keys())
    voice_names = list(voices.values())

    # Get current index
    current_idx = 0
    if current_voice in voice_ids:
        current_idx = voice_ids.index(current_voice)

    selected_name = st.selectbox(
        "Select voice:",
        options=voice_names,
        index=current_idx,
        label_visibility="collapsed",
        key="voice_panel_voice"
    )

    # Map back to voice ID
    selected_idx = voice_names.index(selected_name)
    selected_voice_id = voice_ids[selected_idx]

    if selected_voice_id != current_voice:
        on_voice_change(selected_voice_id)

    # Speed slider
    st.markdown("**Speed**")

    # Get the label for current speed
    speed_label = SPEED_LABELS.get(current_speed, "Normal")

    selected_speed = st.slider(
        "Playback speed",
        min_value=-2,
        max_value=4,
        value=current_speed,
        step=1,
        format="%d",
        label_visibility="collapsed",
        key="voice_panel_speed",
        help="Adjust voice playback speed"
    )

    # Show the speed label
    st.caption(f"Speed: {SPEED_LABELS.get(selected_speed, 'Normal')}")

    if selected_speed != current_speed:
        on_speed_change(selected_speed)

    return recorded_bytes
