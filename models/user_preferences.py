"""
User Preferences - Pydantic models for typed JSON access.

These models define the structure of the Preferences JSON blob
stored in the UserPreferences table.
"""

from pydantic import BaseModel, Field


# Available edge-tts voices for English (US, UK, Ireland)
VOICE_OPTIONS = {
    "en-US-AriaNeural": "Aria (US, Female)",
    "en-US-GuyNeural": "Guy (US, Male)",
    "en-US-JennyNeural": "Jenny (US, Female)",
    "en-US-ChristopherNeural": "Christopher (US, Male)",
    "en-GB-SoniaNeural": "Sonia (UK, Female)",
    "en-GB-RyanNeural": "Ryan (UK, Male)",
    "en-GB-LibbyNeural": "Libby (UK, Female)",
    "en-GB-ThomasNeural": "Thomas (UK, Male)",
    "en-IE-EmilyNeural": "Emily (Ireland, Female)",
    "en-IE-ConnorNeural": "Connor (Ireland, Male)",
}

# Default voice settings
DEFAULT_VOICE_NAME = "en-US-AriaNeural"
DEFAULT_VOICE_RATE = "+0%"  # Normal speed

# Speed presets for the slider (maps slider value to edge-tts rate)
SPEED_OPTIONS = {
    -2: "-20%",   # Slower
    -1: "-10%",   # Slightly slower
    0: "+0%",     # Normal
    1: "+10%",    # Slightly faster
    2: "+20%",    # Faster
    3: "+30%",    # Much faster
    4: "+40%",    # Very fast
}


class VoicePreferences(BaseModel):
    """Voice-related preferences."""
    name: str = Field(default=DEFAULT_VOICE_NAME, description="Edge-TTS voice ID")
    rate: str = Field(default=DEFAULT_VOICE_RATE, description="Speech rate (e.g., '+20%')")


class UserPreferencesData(BaseModel):
    """
    Root preferences model.

    Extensible structure - add new preference groups as needed.
    """
    voice: VoicePreferences = Field(default_factory=VoicePreferences)
    # Future preferences can be added here:
    # theme: ThemePreferences = Field(default_factory=ThemePreferences)
    # cooking: CookingPreferences = Field(default_factory=CookingPreferences)

    @classmethod
    def from_json(cls, json_str: str) -> "UserPreferencesData":
        """Parse preferences from JSON string, with defaults for missing fields."""
        import json
        try:
            data = json.loads(json_str) if json_str else {}
            return cls.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            return cls()

    def to_json(self) -> str:
        """Serialize preferences to JSON string."""
        return self.model_dump_json()


def get_voice_display_name(voice_id: str) -> str:
    """Get the display name for a voice ID."""
    return VOICE_OPTIONS.get(voice_id, voice_id)


def get_voice_id_from_display(display_name: str) -> str:
    """Get the voice ID from a display name."""
    for voice_id, name in VOICE_OPTIONS.items():
        if name == display_name:
            return voice_id
    return DEFAULT_VOICE_NAME


def rate_to_slider_value(rate: str) -> int:
    """Convert edge-tts rate string to slider value."""
    for slider_val, rate_str in SPEED_OPTIONS.items():
        if rate_str == rate:
            return slider_val
    return 0  # Default to normal


def slider_value_to_rate(slider_val: int) -> str:
    """Convert slider value to edge-tts rate string."""
    return SPEED_OPTIONS.get(slider_val, "+0%")
