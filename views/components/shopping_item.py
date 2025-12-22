"""
Shopping list item component.
"""

import streamlit as st
from typing import Any, Callable


def render_shopping_item(
    item: Any,
    on_check_change: Callable[[int, bool], None],
):
    """
    Render a single shopping list item with checkbox.

    Args:
        item: Shopping list item (needs .ShoppingListItemId, .IsChecked, .ingredient, .AggregatedQuantity)
        on_check_change: Callback when checked state changes (item_id, new_state)
    """
    col1, col2 = st.columns([1, 5])

    with col1:
        checked = st.checkbox(
            "checked",
            value=item.IsChecked,
            key=f"item_{item.ShoppingListItemId}",
            label_visibility="collapsed"
        )

        if checked != item.IsChecked:
            on_check_change(item.ShoppingListItemId, checked)
            st.rerun()

    with col2:
        ingredient_name = item.ingredient.Name if item.ingredient else "Unknown"
        quantity = item.AggregatedQuantity or ""

        if item.IsChecked:
            st.markdown(f"~~{ingredient_name}~~ {quantity}")
        else:
            st.markdown(f"**{ingredient_name}** {quantity}")


def render_shopping_items_grouped(
    grouped_items: dict[str, list[Any]],
    on_check_change: Callable[[int, bool], None],
):
    """
    Render shopping items grouped by category.

    Args:
        grouped_items: Dict mapping category names to lists of items
        on_check_change: Callback when item checked state changes
    """
    if not grouped_items:
        st.info("No items in this list")
        return

    for category, items in grouped_items.items():
        st.markdown(f"#### {category}")

        for item in items:
            render_shopping_item(item, on_check_change)

        st.markdown("")
