"""
Azure Speech Services integration.

This module will handle:
- Speech-to-Text (STT): Convert user's voice to text
- Text-to-Speech (TTS): Convert Claude's response to audio

Placeholder for Phase 4 implementation.
"""

from app.config import get_settings

settings = get_settings()


async def speech_to_text(audio_data: bytes) -> str:
    """
    Convert audio to text using Azure Speech Services.

    Args:
        audio_data: Raw audio bytes (WAV format expected)

    Returns:
        Transcribed text
    """
    # TODO: Implement with azure-cognitiveservices-speech
    raise NotImplementedError("Speech-to-text not yet implemented")


async def text_to_speech(text: str) -> bytes:
    """
    Convert text to speech using Azure Speech Services.

    Args:
        text: Text to convert to speech

    Returns:
        Audio data as bytes (WAV format)
    """
    # TODO: Implement with azure-cognitiveservices-speech
    raise NotImplementedError("Text-to-speech not yet implemented")
