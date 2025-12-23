"""
Chat UI components.
"""

import streamlit as st


def render_chat_messages(messages: list[dict], height: int = 450):
    """
    Render chat message history in a scrollable container.

    Args:
        messages: List of {"role": "user/assistant", "content": "..."}
        height: Container height in pixels
    """
    st.markdown("### Conversation")
    chat_container = st.container(height=height)
    with chat_container:
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
