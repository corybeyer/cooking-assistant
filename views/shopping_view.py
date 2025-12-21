"""
Shopping View - UI for viewing and managing shopping lists.

This view handles:
- Displaying shopping lists
- Checking off items
- Sharing lists via link
"""

import streamlit as st
from typing import Optional

from controllers.shopping_controller import ShoppingController


class ShoppingView:
    """View for shopping list UI."""

    def __init__(self):
        self.controller = ShoppingController()

    def render(self):
        """Main render method."""
        st.title("🛒 Shopping List")

        # Check for link code in query params
        query_params = st.query_params
        link_code = query_params.get("code")

        if link_code:
            self._render_shared_list(link_code)
        else:
            self._render_list_selector()

    def _render_list_selector(self):
        """Render list selection and management."""
        lists = self.controller.get_all_lists()

        if not lists:
            st.info("No shopping lists yet. Go to **Plan Meals** to create one!")
            return

        # Sidebar for list selection
        with st.sidebar:
            st.markdown("### 📋 Your Lists")
            st.markdown("---")

            for lst in lists:
                progress = lst.checked_count / lst.item_count if lst.item_count > 0 else 0
                label = f"{lst.name} ({lst.checked_count}/{lst.item_count})"

                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(label, key=f"select_{lst.id}", use_container_width=True):
                        self.controller.set_current_list_id(lst.id)
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"delete_{lst.id}", help="Delete list"):
                        self.controller.delete_list(lst.id)
                        st.rerun()

                # Progress bar
                st.progress(progress)
                st.markdown("")

        # Main area - show selected list or prompt
        current_id = self.controller.get_current_list_id()

        if current_id:
            self._render_shopping_list(current_id)
        else:
            st.markdown("### Select a list from the sidebar")
            st.markdown("Or create a new one in **Plan Meals**")

    def _render_shopping_list(self, list_id: int):
        """Render a shopping list with checkable items."""
        shopping_list = self.controller.get_list(list_id)

        if not shopping_list:
            st.error("Shopping list not found")
            return

        # Header
        st.markdown(f"### {shopping_list.Name or 'Shopping List'}")

        # Stats
        items = shopping_list.items or []
        total = len(items)
        checked = sum(1 for i in items if i.IsChecked)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Items", total)
        with col2:
            st.metric("Checked", checked)
        with col3:
            st.metric("Remaining", total - checked)

        st.progress(checked / total if total > 0 else 0)
        st.markdown("---")

        # Share button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔗 Share", use_container_width=True):
                link_code = self.controller.generate_link(list_id)
                st.session_state.shopping["link_code"] = link_code

        # Show share link if generated
        link_code = self.controller.get_link_code()
        if link_code:
            share_url = self.controller.get_shareable_url(link_code)
            st.success(f"Share this link: `{share_url}`")
            st.code(share_url)

        st.markdown("---")

        # Items grouped by category
        grouped = self.controller.get_items_grouped(list_id)

        if not grouped:
            st.info("No items in this list")
            return

        for category, category_items in grouped.items():
            st.markdown(f"#### {category}")

            for item in category_items:
                self._render_item(item)

            st.markdown("")

    def _render_item(self, item):
        """Render a single shopping list item with checkbox."""
        col1, col2 = st.columns([1, 5])

        with col1:
            # Checkbox
            checked = st.checkbox(
                "checked",
                value=item.IsChecked,
                key=f"item_{item.ShoppingListItemId}",
                label_visibility="collapsed"
            )

            # Update if changed
            if checked != item.IsChecked:
                self.controller.check_item(item.ShoppingListItemId, checked)
                st.rerun()

        with col2:
            # Item text
            ingredient_name = item.ingredient.Name if item.ingredient else "Unknown"
            quantity = item.AggregatedQuantity or ""

            if item.IsChecked:
                st.markdown(f"~~{ingredient_name}~~ {quantity}")
            else:
                st.markdown(f"**{ingredient_name}** {quantity}")

    def _render_shared_list(self, link_code: str):
        """Render a shared list accessed via link."""
        shopping_list = self.controller.get_list_by_link(link_code)

        if not shopping_list:
            st.error("This shopping list link is invalid or has expired.")
            return

        # Header
        st.markdown(f"### {shopping_list.Name or 'Shopping List'}")
        st.caption("Shared shopping list")

        # Stats
        items = shopping_list.items or []
        total = len(items)
        checked = sum(1 for i in items if i.IsChecked)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Items", total)
        with col2:
            st.metric("Remaining", total - checked)

        st.progress(checked / total if total > 0 else 0)
        st.markdown("---")

        # Items grouped by category
        grouped_items = {}
        for item in items:
            category = item.Category or "Other"
            if category not in grouped_items:
                grouped_items[category] = []
            grouped_items[category].append(item)

        # Sort categories
        category_order = {
            "Produce": 1, "Meat & Seafood": 2, "Dairy & Eggs": 3,
            "Bakery": 4, "Grains & Pasta": 5, "Canned & Jarred": 6,
            "Pantry": 7, "Spices": 8, "Other": 99
        }
        sorted_categories = sorted(
            grouped_items.keys(),
            key=lambda x: category_order.get(x, 50)
        )

        for category in sorted_categories:
            category_items = grouped_items[category]
            st.markdown(f"#### {category}")

            for item in category_items:
                self._render_item(item)

            st.markdown("")
