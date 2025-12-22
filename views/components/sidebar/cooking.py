"""
Cooking session sidebar component.
"""

import streamlit as st
from typing import Callable


def render_cooking_sidebar(
    recipe_name: str,
    on_text_submit: Callable[[str], tuple[bool, str | None]],
    on_end_session: Callable[[], None],
):
    """
    Render the cooking session sidebar.

    Args:
        recipe_name: Name of the current recipe
        on_text_submit: Callback when text is submitted, returns (success, error)
        on_end_session: Callback when session ends
    """
    with st.sidebar:
        st.markdown(f"### {recipe_name}")
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
