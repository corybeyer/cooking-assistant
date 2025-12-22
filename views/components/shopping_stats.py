"""
Shopping list statistics component.
"""

import streamlit as st


def render_shopping_stats(total: int, checked: int):
    """
    Render shopping list progress statistics.

    Args:
        total: Total number of items
        checked: Number of checked items
    """
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Items", total)
    with col2:
        st.metric("Checked", checked)
    with col3:
        st.metric("Remaining", total - checked)

    st.progress(checked / total if total > 0 else 0)
