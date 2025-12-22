"""
Cooking session sidebar component.
"""

import streamlit as st
from typing import Callable


def render_cooking_sidebar(
    recipe_name: str,
    accents: list[str],
    current_accent: str,
    on_accent_change: Callable[[str], None],
    on_text_submit: Callable[[str], tuple[bool, str | None]],
    on_end_session: Callable[[], None],
):
    """
    Render the cooking session sidebar.

    Args:
        recipe_name: Name of the current recipe
        accents: List of available voice accents
        current_accent: Currently selected accent
        on_accent_change: Callback when accent changes
        on_text_submit: Callback when text is submitted, returns (success, error)
        on_end_session: Callback when session ends
    """
    with st.sidebar:
        st.markdown(f"### {recipe_name}")
        st.markdown("---")

        # Voice accent selection
        st.markdown("**Voice**")
        selected_accent = st.selectbox(
            "Select accent:",
            options=accents,
            index=accents.index(current_accent) if current_accent in accents else 0,
            label_visibility="collapsed"
        )
        if selected_accent != current_accent:
            on_accent_change(selected_accent)

        st.markdown("---")

        # Text Input (fallback)
        st.markdown("**Text Input**")
        text_input = st.text_input(
            "Type your message:",
            key="text_input",
            placeholder="What's next?",
            label_visibility="collapsed"
        )

        # Handle text input
        if text_input:
            success, error = on_text_submit(text_input)
            if not success:
                st.error(error)
            else:
                st.rerun()

        st.markdown("---")

        # End session button
        if st.button("End Cooking Session", type="secondary", use_container_width=True):
            on_end_session()
            st.rerun()
