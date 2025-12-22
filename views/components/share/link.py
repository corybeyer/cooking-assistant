"""
Link share component for shopping lists.
"""

import streamlit as st
from typing import Callable


def render_link_share(
    list_id: int,
    generate_link: Callable[[int], str],
    get_link_code: Callable[[], str | None],
    get_shareable_url: Callable[[str], str],
):
    """
    Render the shareable link section.

    Args:
        list_id: Shopping list ID to share
        generate_link: Function to generate a link code for a list
        get_link_code: Function to get current link code from session
        get_shareable_url: Function to build full URL from link code
    """
    if st.button("Generate Link", use_container_width=True):
        link_code = generate_link(list_id)
        st.session_state.shopping["link_code"] = link_code
        st.rerun()

    link_code = get_link_code()
    if link_code:
        share_url = get_shareable_url(link_code)
        st.success("Link generated!")
        st.code(share_url)
        st.caption("Copy this link and share it")
