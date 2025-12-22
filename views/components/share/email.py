"""
Email share component for shopping lists.
"""

import streamlit as st
from typing import Any, Callable


def render_email_share(
    list_id: int,
    is_configured: bool,
    config_issues: list[str],
    validate_email: Callable[[str], tuple[bool, str]],
    send_email: Callable[[int, str], Any],
):
    """
    Render the email share section.

    Args:
        list_id: Shopping list ID to share
        is_configured: Whether email is configured
        config_issues: List of configuration issues
        validate_email: Function to validate email, returns (is_valid, message)
        send_email: Function to send email, returns result with .success and .error
    """
    if not is_configured:
        st.warning("Email is not fully configured. Missing settings:")
        for issue in config_issues:
            st.error(f"* {issue}")
        with st.expander("Configuration Help"):
            st.markdown("**Required environment variables:**")
            st.code("""# Azure Communication Services Email
AZURE_COMM_EMAIL_ENDPOINT=https://<resource>.communication.azure.com
AZURE_COMM_EMAIL_SENDER=DoNotReply@<guid>.azurecomm.net

# App URL for shareable links
APP_BASE_URL=https://your-app.azurecontainerapps.io""")
        return

    # Initialize session state for email
    if "share_email" not in st.session_state:
        st.session_state.share_email = ""
    if "email_sent" not in st.session_state:
        st.session_state.email_sent = False
    if "email_error" not in st.session_state:
        st.session_state.email_error = None

    # Email input
    email = st.text_input(
        "Email address:",
        value=st.session_state.share_email,
        placeholder="you@example.com",
        help="Enter an email address"
    )
    st.session_state.share_email = email

    # Send button
    if st.button("Send to Email", type="primary", use_container_width=True):
        if not email:
            st.session_state.email_error = "Please enter an email address"
        else:
            # Validate email
            is_valid, message = validate_email(email)
            if not is_valid:
                st.session_state.email_error = message
            else:
                # Send email
                with st.spinner("Sending..."):
                    result = send_email(list_id, email)

                if result.success:
                    st.session_state.email_sent = True
                    st.session_state.email_error = None
                else:
                    st.session_state.email_error = result.error
                    st.session_state.email_sent = False

        st.rerun()

    # Show status
    if st.session_state.email_sent:
        st.success("Shopping list sent! Check your email.")
        st.session_state.email_sent = False

    if st.session_state.email_error:
        st.error(st.session_state.email_error)
        st.session_state.email_error = None
