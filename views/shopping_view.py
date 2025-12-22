"""
Shopping View - UI for viewing and managing shopping lists.

This view handles:
- Displaying shopping lists
- Checking off items
- Sharing lists via link
"""

import streamlit as st

from controllers.shopping_controller import ShoppingController
from views.components.sidebar import render_shopping_list_sidebar
from views.components.shopping_item import render_shopping_items_grouped
from views.components.shopping_stats import render_shopping_stats
from views.components.share import render_email_share, render_link_share


class ShoppingView:
    """View for shopping list UI."""

    def __init__(self):
        self.controller = ShoppingController()

    def render(self):
        """Main render method."""
        st.title("Shopping List")

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
        render_shopping_list_sidebar(
            lists=lists,
            on_select=self.controller.set_current_list_id,
            on_delete=self.controller.delete_list,
        )

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

        render_shopping_stats(total, checked)
        st.markdown("---")

        # Share section
        self._render_share_section(list_id)
        st.markdown("---")

        # Items grouped by category
        grouped = self.controller.get_items_grouped(list_id)
        render_shopping_items_grouped(grouped, self.controller.check_item)

    def _render_share_section(self, list_id: int):
        """Render the share/send section."""
        st.markdown("#### Share List")

        tab1, tab2 = st.tabs(["Send via Email", "Copy Link"])

        with tab1:
            render_email_share(
                list_id=list_id,
                is_configured=self.controller.is_email_configured(),
                config_issues=self.controller.get_email_config_issues(),
                validate_email=self.controller.validate_email,
                send_email=self.controller.send_list_via_email,
            )

        with tab2:
            render_link_share(
                list_id=list_id,
                generate_link=self.controller.generate_link,
                get_link_code=self.controller.get_link_code,
                get_shareable_url=self.controller.get_shareable_url,
            )

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
        grouped_items = self._group_items_by_category(items)
        render_shopping_items_grouped(grouped_items, self.controller.check_item)

    def _group_items_by_category(self, items) -> dict:
        """Group items by category with proper ordering."""
        grouped = {}
        for item in items:
            category = item.Category or "Other"
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(item)

        # Sort categories
        category_order = {
            "Produce": 1, "Meat & Seafood": 2, "Dairy & Eggs": 3,
            "Bakery": 4, "Grains & Pasta": 5, "Canned & Jarred": 6,
            "Pantry": 7, "Spices": 8, "Other": 99
        }
        return {
            k: grouped[k]
            for k in sorted(grouped.keys(), key=lambda x: category_order.get(x, 50))
        }
