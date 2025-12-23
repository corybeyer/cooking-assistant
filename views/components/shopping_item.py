"""
Shopping list item components.

Provides unified table row with integrated pricing and product selection.
"""

import streamlit as st
from typing import Any, Callable, Optional
from dataclasses import dataclass


@dataclass
class ProductOption:
    """A product option for the dropdown."""
    product_id: str
    name: str
    size: Optional[str]
    price: float
    unit: str


def render_shopping_item_row(
    item: Any,
    price_info: Optional[Any],
    selected_product: Optional[Any],
    is_removed: bool,
    on_check_change: Callable[[int, bool], None],
    on_remove: Callable[[int], None],
    on_product_select: Callable[[int, Any], None],
):
    """
    Render a unified shopping item row with pricing.

    Args:
        item: Shopping list item
        price_info: ItemPriceInfo with Kroger matches (or None if not fetched)
        selected_product: Currently selected ProductMatch (or None for best match)
        is_removed: Whether this item is marked as removed
        on_check_change: Callback when checked state changes
        on_remove: Callback to remove item
        on_product_select: Callback when product selection changes
    """
    ingredient_name = item.ingredient.Name if item.ingredient else "Unknown"
    quantity = item.AggregatedQuantity or ""
    item_id = item.ShoppingListItemId

    # Determine current product and price
    current_product = selected_product
    if not current_product and price_info and price_info.best_match:
        current_product = price_info.best_match

    # Layout: checkbox | item | qty | product dropdown | price | remove
    col_check, col_item, col_qty, col_product, col_price, col_remove = st.columns(
        [0.5, 2.5, 1.5, 3, 1, 0.5]
    )

    with col_check:
        checked = st.checkbox(
            "checked",
            value=item.IsChecked,
            key=f"check_{item_id}",
            label_visibility="collapsed"
        )
        if checked != item.IsChecked:
            on_check_change(item_id, checked)
            st.rerun()

    with col_item:
        if item.IsChecked:
            st.markdown(f"~~{ingredient_name}~~")
        else:
            st.markdown(f"**{ingredient_name}**")

    with col_qty:
        if item.IsChecked:
            st.markdown(f"~~{quantity}~~")
        else:
            st.caption(quantity)

    with col_product:
        if price_info:
            if price_info.all_matches:
                # Build options for selectbox
                options = price_info.all_matches
                option_labels = [
                    f"{p.product_name} ({p.size})" if p.size else p.product_name
                    for p in options
                ]

                # Find current selection index
                current_idx = 0
                if selected_product:
                    for idx, p in enumerate(options):
                        if p.product_id == selected_product.product_id:
                            current_idx = idx
                            break

                selected_idx = st.selectbox(
                    "Product",
                    range(len(options)),
                    index=current_idx,
                    format_func=lambda i: option_labels[i],
                    key=f"product_{item_id}",
                    label_visibility="collapsed"
                )

                # Handle selection change
                if selected_idx != current_idx:
                    on_product_select(item_id, options[selected_idx])
                    st.rerun()
            else:
                st.caption(price_info.error or "No match")
        else:
            st.caption("--")

    with col_price:
        if current_product:
            if item.IsChecked:
                st.markdown(f"~~${current_product.price:.2f}~~")
            else:
                st.markdown(f"**${current_product.price:.2f}**")
        else:
            st.markdown("--")

    with col_remove:
        if st.button("🗑️", key=f"remove_{item_id}", help="Already have this"):
            on_remove(item_id)
            st.rerun()


def render_removed_item_row(
    item: Any,
    on_restore: Callable[[int], None],
):
    """
    Render a removed item row with restore option.

    Args:
        item: Shopping list item
        on_restore: Callback to restore item
    """
    ingredient_name = item.ingredient.Name if item.ingredient else "Unknown"
    quantity = item.AggregatedQuantity or ""
    item_id = item.ShoppingListItemId

    col_restore, col_item, col_qty, col_spacer = st.columns([0.5, 2.5, 1.5, 5.5])

    with col_restore:
        if st.button("↩️", key=f"restore_{item_id}", help="Add back to list"):
            on_restore(item_id)
            st.rerun()

    with col_item:
        st.markdown(f"*{ingredient_name}*", help="Removed - click ↩️ to restore")

    with col_qty:
        st.caption(quantity)


def render_shopping_table_header():
    """Render the table header row."""
    col_check, col_item, col_qty, col_product, col_price, col_remove = st.columns(
        [0.5, 2.5, 1.5, 3, 1, 0.5]
    )

    with col_check:
        st.caption("✓")
    with col_item:
        st.caption("Item")
    with col_qty:
        st.caption("Qty")
    with col_product:
        st.caption("Kroger Product")
    with col_price:
        st.caption("Price")
    with col_remove:
        st.caption("")


def render_category_section(
    category: str,
    items: list[Any],
    price_info_map: dict[int, Any],
    selected_products: dict[int, Any],
    removed_items: set[int],
    on_check_change: Callable[[int, bool], None],
    on_remove: Callable[[int], None],
    on_product_select: Callable[[int, Any], None],
):
    """
    Render a category section with its items.

    Args:
        category: Category name (e.g., "Produce")
        items: List of items in this category
        price_info_map: Map of item_id to ItemPriceInfo
        selected_products: Map of item_id to selected ProductMatch
        removed_items: Set of removed item IDs
        on_check_change: Callback for check changes
        on_remove: Callback for item removal
        on_product_select: Callback for product selection
    """
    # Filter out removed items for this category
    active_items = [i for i in items if i.ShoppingListItemId not in removed_items]

    if not active_items:
        return  # Hide category if all items removed

    st.markdown(f"#### {category}")

    for item in active_items:
        item_id = item.ShoppingListItemId
        price_info = price_info_map.get(item_id)
        selected = selected_products.get(item_id)

        render_shopping_item_row(
            item=item,
            price_info=price_info,
            selected_product=selected,
            is_removed=False,
            on_check_change=on_check_change,
            on_remove=on_remove,
            on_product_select=on_product_select,
        )

    st.markdown("")  # Spacing between categories


def render_removed_section(
    all_items: list[Any],
    removed_items: set[int],
    on_restore: Callable[[int], None],
):
    """
    Render the collapsed removed items section.

    Args:
        all_items: All shopping list items
        removed_items: Set of removed item IDs
        on_restore: Callback to restore an item
    """
    removed = [i for i in all_items if i.ShoppingListItemId in removed_items]

    if not removed:
        return

    with st.expander(f"Removed ({len(removed)} items)", expanded=False):
        st.caption("Items you already have. Click ↩️ to add back.")
        for item in removed:
            render_removed_item_row(item, on_restore)


# Legacy function for backwards compatibility
def render_shopping_item(
    item: Any,
    on_check_change: Callable[[int, bool], None],
):
    """
    Render a single shopping list item with checkbox (legacy).

    Args:
        item: Shopping list item
        on_check_change: Callback when checked state changes
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
    Render shopping items grouped by category (legacy).

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
