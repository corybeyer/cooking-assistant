"""
Config Package - Application configuration and database setup.
"""

from config.settings import Settings, get_settings
from config.database import SessionLocal, Base, get_db, engine
from config.auth import (
    UserContext,
    get_current_user,
    require_auth,
    get_user_display_name,
    is_authenticated,
)

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    # Database
    "SessionLocal",
    "Base",
    "get_db",
    "engine",
    # Authentication
    "UserContext",
    "get_current_user",
    "require_auth",
    "get_user_display_name",
    "is_authenticated",
]
