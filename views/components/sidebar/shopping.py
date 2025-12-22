"""
Shopping list sidebar component.
"""

import streamlit as st
from typing import Callable, Any


def render_shopping_list_sidebar(
    lists: list[Any],
    on_select: Callable[[int], None],
    on_delete: Callable[[int], None],
):
    """
    Render the shopping list selection sidebar.

    Args:
        lists: List of shopping list summary objects (need .id, .name, .checked_count, .item_count)
        on_select: Callback when a list is selected
        on_delete: Callback when a list is deleted
    """
    with st.sidebar:
        st.markdown("### Your Lists")
        st.markdown("---")

        for lst in lists:
            progress = lst.checked_count / lst.item_count if lst.item_count > 0 else 0
            label = f"{lst.name} ({lst.checked_count}/{lst.item_count})"

            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(label, key=f"select_{lst.id}", use_container_width=True):
                    on_select(lst.id)
                    st.rerun()
            with col2:
                if st.button("x", key=f"delete_{lst.id}", help="Delete list"):
                    on_delete(lst.id)
                    st.rerun()

            # Progress bar
            st.progress(progress)
            st.markdown("")
