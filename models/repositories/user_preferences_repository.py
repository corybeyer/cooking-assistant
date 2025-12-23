"""
User Preferences Repository - Data access for user preferences.

This repository handles all database operations related to user preferences,
providing typed access through Pydantic models.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models.entities import UserPreference
from models.user_preferences import UserPreferencesData


class UserPreferencesRepository:
    """Repository for user preferences database operations."""

    def __init__(self, db: Session):
        """Initialize with a database session."""
        self.db = db

    def get(self, user_id: str) -> UserPreferencesData:
        """
        Get user preferences, returning defaults if not found.

        Args:
            user_id: The Entra ID object ID of the user

        Returns:
            UserPreferencesData with user's preferences or defaults
        """
        record = self.db.query(UserPreference).filter(
            UserPreference.UserId == user_id
        ).first()

        if record:
            return UserPreferencesData.from_json(record.Preferences)
        return UserPreferencesData()

    def get_record(self, user_id: str) -> Optional[UserPreference]:
        """
        Get the raw database record for user preferences.

        Args:
            user_id: The Entra ID object ID of the user

        Returns:
            UserPreference entity or None
        """
        return self.db.query(UserPreference).filter(
            UserPreference.UserId == user_id
        ).first()

    def save(self, user_id: str, preferences: UserPreferencesData) -> UserPreference:
        """
        Save user preferences (upsert).

        Args:
            user_id: The Entra ID object ID of the user
            preferences: The preferences data to save

        Returns:
            The saved UserPreference entity
        """
        record = self.get_record(user_id)

        if record:
            # Update existing
            record.Preferences = preferences.to_json()
            record.UpdatedAt = datetime.utcnow()
        else:
            # Create new
            record = UserPreference(
                UserId=user_id,
                Preferences=preferences.to_json()
            )
            self.db.add(record)

        self.db.commit()
        self.db.refresh(record)
        return record

    def update_voice(self, user_id: str, voice_name: str, voice_rate: str) -> UserPreferencesData:
        """
        Update voice preferences specifically.

        Args:
            user_id: The Entra ID object ID of the user
            voice_name: The edge-tts voice ID
            voice_rate: The speech rate (e.g., '+20%')

        Returns:
            Updated UserPreferencesData
        """
        prefs = self.get(user_id)
        prefs.voice.name = voice_name
        prefs.voice.rate = voice_rate
        self.save(user_id, prefs)
        return prefs

    def delete(self, user_id: str) -> bool:
        """
        Delete user preferences.

        Args:
            user_id: The Entra ID object ID of the user

        Returns:
            True if deleted, False if not found
        """
        result = self.db.query(UserPreference).filter(
            UserPreference.UserId == user_id
        ).delete()
        self.db.commit()
        return result > 0
