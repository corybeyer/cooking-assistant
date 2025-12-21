"""
Audio Service - handles speech recognition and text-to-speech.

This service is pure Python with no Streamlit dependencies.
"""

import tempfile
import os
import logging
from io import BytesIO
from typing import Optional

import speech_recognition as sr
from gtts import gTTS

logger = logging.getLogger(__name__)


# Voice accent options (gTTS tld parameter)
VOICE_ACCENTS = {
    "American 🇺🇸": "com",
    "British 🇬🇧": "co.uk",
    "Australian 🇦🇺": "com.au",
    "Indian 🇮🇳": "co.in",
    "Canadian 🇨🇦": "ca",
    "Irish 🇮🇪": "ie",
    "South African 🇿🇦": "co.za",
}


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

    def text_to_speech(self, text: str, accent: str = "American 🇺🇸") -> Optional[bytes]:
        """
        Convert text to speech audio.

        Args:
            text: Text to convert
            accent: Voice accent key from VOICE_ACCENTS

        Returns:
            MP3 audio bytes, or None if TTS failed
        """
        try:
            tld = VOICE_ACCENTS.get(accent, "com")
            tts = gTTS(text=text, lang='en', tld=tld)
            audio_buffer = BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            return audio_buffer.read()
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

    @staticmethod
    def get_available_accents() -> list[str]:
        """Get list of available voice accents."""
        return list(VOICE_ACCENTS.keys())
