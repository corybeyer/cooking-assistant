"""
Azure Entra ID Authentication Utilities

Extracts user identity from Azure Container Apps Easy Auth headers.
When Easy Auth is enabled, Azure automatically injects user information
into request headers after successful authentication.

Headers injected by Easy Auth:
- X-MS-CLIENT-PRINCIPAL: Base64-encoded JSON with full user claims
- X-MS-CLIENT-PRINCIPAL-ID: User's Entra ID object ID (GUID)
- X-MS-CLIENT-PRINCIPAL-NAME: User's principal name (email/UPN)
"""

import base64
import json
import os
import streamlit as st
from dataclasses import dataclass
from typing import Optional


@dataclass
class UserContext:
    """Represents the authenticated user."""
    user_id: str  # Entra ID object ID (GUID)
    name: str  # Display name or email
    email: Optional[str] = None  # Email address if available


def get_current_user() -> Optional[UserContext]:
    """
    Extract current user from Azure Container Apps Easy Auth headers.

    In Azure Container Apps with Easy Auth enabled, user identity is passed
    via HTTP headers. This function extracts that identity.

    Returns:
        UserContext if authenticated, None otherwise
    """
    # Method 1: Try to get headers from Streamlit's context
    # This works when running behind Azure Container Apps Easy Auth
    try:
        headers = st.context.headers

        if headers:
            # Headers are lowercase in the dict
            user_id = headers.get("x-ms-client-principal-id")
            name = headers.get("x-ms-client-principal-name")

            if user_id:
                # Try to extract email from the full principal
                email = None
                principal_b64 = headers.get("x-ms-client-principal")
                if principal_b64:
                    try:
                        principal_json = base64.b64decode(principal_b64).decode('utf-8')
                        principal = json.loads(principal_json)
                        claims = principal.get("claims", [])
                        for claim in claims:
                            if claim.get("typ") in ["email", "preferred_username"]:
                                email = claim.get("val")
                                break
                    except (ValueError, json.JSONDecodeError):
                        pass

                return UserContext(
                    user_id=user_id,
                    name=name or email or "User",
                    email=email or name  # UPN is often the email
                )
    except AttributeError:
        # Streamlit version may not have st.context.headers
        pass
    except Exception:
        # Header access failed, try other methods
        pass

    # Method 2: Check environment variables (for testing/development)
    # You can set these locally to simulate a user
    user_id = os.environ.get("DEV_USER_ID")
    if user_id:
        return UserContext(
            user_id=user_id,
            name=os.environ.get("DEV_USER_NAME", "Dev User"),
            email=os.environ.get("DEV_USER_EMAIL")
        )

    # Method 3: Check query parameters (for shared link access)
    # Note: This is handled separately in the shopping view

    return None


def require_auth() -> UserContext:
    """
    Require authentication - stops execution if not authenticated.

    Use this at the top of pages that require authentication.
    Shows a friendly message if the user is not logged in.

    Returns:
        UserContext for the authenticated user

    Raises:
        st.stop() if not authenticated
    """
    user = get_current_user()

    if not user:
        st.warning("Please sign in to access this feature.")
        st.info(
            "This app uses Microsoft Entra ID for authentication. "
            "If you're seeing this message, authentication may not be configured "
            "or you may need to sign in."
        )

        # Show dev mode instructions
        if os.environ.get("STREAMLIT_ENV") == "development":
            with st.expander("Development Mode"):
                st.code(
                    "# Set these environment variables to simulate a user:\n"
                    "export DEV_USER_ID='your-test-user-id'\n"
                    "export DEV_USER_NAME='Test User'\n"
                    "export DEV_USER_EMAIL='test@example.com'",
                    language="bash"
                )

        st.stop()

    return user


def get_user_display_name() -> str:
    """Get the current user's display name, or 'Guest' if not authenticated."""
    user = get_current_user()
    return user.name if user else "Guest"


def is_authenticated() -> bool:
    """Check if a user is currently authenticated."""
    return get_current_user() is not None
