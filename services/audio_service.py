"""
Audio Service - handles speech recognition and text-to-speech.

This service is pure Python with no Streamlit dependencies.
Uses edge-tts for high-quality neural text-to-speech.
"""

import asyncio
import tempfile
import os
import logging
from typing import Optional

import speech_recognition as sr
import edge_tts

from models.user_preferences import (
    VOICE_OPTIONS,
    DEFAULT_VOICE_NAME,
    DEFAULT_VOICE_RATE,
)

logger = logging.getLogger(__name__)


class AudioService:
    """Service for audio transcription and text-to-speech."""

    def __init__(self):
        self.recognizer = sr.Recognizer()

    def transcribe(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribe audio to text using Google Speech Recognition.

        Args:
            audio_bytes: Raw audio data (WAV format)

        Returns:
            Transcribed text, or None if transcription failed
        """
        temp_path = None
        try:
            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            # Use speech_recognition to transcribe
            with sr.AudioFile(temp_path) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data)
                return text

        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return None
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
        finally:
            # Always clean up temp file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    async def _text_to_speech_async(
        self,
        text: str,
        voice: str = DEFAULT_VOICE_NAME,
        rate: str = DEFAULT_VOICE_RATE
    ) -> Optional[bytes]:
        """
        Async implementation of text-to-speech using edge-tts.

        Args:
            text: Text to convert
            voice: Edge-TTS voice ID (e.g., 'en-US-AriaNeural')
            rate: Speech rate (e.g., '+20%', '-10%')

        Returns:
            MP3 audio bytes, or None if TTS failed
        """
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            audio_bytes = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes += chunk["data"]
            return audio_bytes if audio_bytes else None
        except Exception as e:
            logger.error(f"Edge-TTS error: {e}")
            return None

    def text_to_speech(
        self,
        text: str,
        voice: str = DEFAULT_VOICE_NAME,
        rate: str = DEFAULT_VOICE_RATE
    ) -> Optional[bytes]:
        """
        Convert text to speech audio using edge-tts.

        Args:
            text: Text to convert
            voice: Edge-TTS voice ID (e.g., 'en-US-AriaNeural')
            rate: Speech rate (e.g., '+20%', '-10%')

        Returns:
            MP3 audio bytes, or None if TTS failed
        """
        try:
            # Run async function in sync context
            return asyncio.run(self._text_to_speech_async(text, voice, rate))
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

    @staticmethod
    def get_available_voices() -> dict[str, str]:
        """Get available voice options as {voice_id: display_name}."""
        return VOICE_OPTIONS.copy()

    @staticmethod
    def get_voice_ids() -> list[str]:
        """Get list of available voice IDs."""
        return list(VOICE_OPTIONS.keys())

    @staticmethod
    def get_voice_display_names() -> list[str]:
        """Get list of available voice display names."""
        return list(VOICE_OPTIONS.values())
