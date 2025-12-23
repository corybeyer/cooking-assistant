"""
Shopping View - UI for viewing and managing shopping lists.

This view handles:
- Displaying shopping lists with integrated Kroger pricing
- Checking off items while shopping
- Removing items already in the house
- Selecting alternative products
- Sharing lists via link
"""

import streamlit as st

from controllers.shopping_controller import ShoppingController, PriceComparisonResult
from views.components.sidebar import render_shopping_list_sidebar
from views.components.shopping_item import (
    render_shopping_table_header,
    render_category_section,
    render_removed_section,
)
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
        """Render a shopping list with unified pricing table."""
        shopping_list = self.controller.get_list(list_id)

        if not shopping_list:
            st.error("Shopping list not found")
            return

        # Header
        st.markdown(f"### {shopping_list.Name or 'Shopping List'}")

        items = shopping_list.items or []
        removed_items = self.controller.get_removed_items(list_id)
        active_items = [i for i in items if i.ShoppingListItemId not in removed_items]

        # Stats row with pricing
        self._render_stats_and_pricing(list_id, items, active_items, removed_items)

        st.markdown("---")

        # Share section (collapsed)
        with st.expander("Share List", expanded=False):
            self._render_share_section(list_id)

        st.markdown("---")

        # Table header
        render_shopping_table_header()

        # Get price info and selected products for rendering
        cached_prices = self.controller.get_cached_prices(list_id)
        price_info_map = {}
        if cached_prices and cached_prices.success:
            for item_info in cached_prices.items:
                price_info_map[item_info.item_id] = item_info

        selected_products = st.session_state.shopping.get("selected_products", {})

        # Items grouped by category
        grouped = self.controller.get_items_grouped(list_id)

        for category, category_items in grouped.items():
            render_category_section(
                category=category,
                items=category_items,
                price_info_map=price_info_map,
                selected_products=selected_products,
                removed_items=removed_items,
                on_check_change=self.controller.check_item,
                on_remove=lambda item_id: self.controller.remove_item(list_id, item_id),
                on_product_select=self.controller.set_selected_product,
            )

        # Removed items section at bottom
        render_removed_section(
            all_items=items,
            removed_items=removed_items,
            on_restore=lambda item_id: self.controller.restore_item(list_id, item_id),
        )

    def _render_stats_and_pricing(
        self,
        list_id: int,
        all_items: list,
        active_items: list,
        removed_items: set,
    ):
        """Render stats row with integrated pricing controls."""
        total_active = len(active_items)
        checked = sum(1 for i in active_items if i.IsChecked)
        removed_count = len(removed_items)

        # Get cached prices
        cached_prices = self.controller.get_cached_prices(list_id)
        has_prices = cached_prices and cached_prices.success

        # Layout: stats | price button/total
        col_stats, col_pricing = st.columns([2, 1])

        with col_stats:
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            with stat_col1:
                st.metric("Items", total_active)
            with stat_col2:
                st.metric("Got", checked)
            with stat_col3:
                if removed_count > 0:
                    st.metric("Removed", removed_count)
                else:
                    st.metric("Remaining", total_active - checked)

            # Progress bar
            if total_active > 0:
                st.progress(checked / total_active)

        with col_pricing:
            if not self.controller.is_kroger_configured():
                st.caption("Kroger not configured")
                with st.popover("Setup"):
                    issues = self.controller.get_kroger_config_issues()
                    for issue in issues:
                        st.markdown(f"- {issue}")
            elif has_prices:
                # Show effective total
                effective_total = self.controller.get_effective_total(list_id)
                items_priced = cached_prices.items_with_prices
                items_not_found = cached_prices.items_without_prices

                st.metric("Estimated Total", f"${effective_total:.2f}")

                if items_not_found > 0:
                    st.caption(f"{items_priced} priced, {items_not_found} not found")
                else:
                    st.caption(f"All {items_priced} items priced")

                if st.button("Refresh Prices", use_container_width=True):
                    self._fetch_prices(list_id)
            else:
                # Show fetch button
                if st.button(
                    "Get Kroger Prices",
                    type="primary",
                    use_container_width=True
                ):
                    self._fetch_prices(list_id)

    def _fetch_prices(self, list_id: int):
        """Fetch prices from Kroger API."""
        with st.spinner("Fetching prices from Kroger..."):
            result = self.controller.get_prices_for_list(list_id)
            self.controller.set_cached_prices(list_id, result)
            st.rerun()

    def _render_share_section(self, list_id: int):
        """Render the share/send section."""
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

        # For shared lists, use simple grouped view (no pricing)
        grouped_items = self._group_items_by_category(items)

        for category, category_items in grouped_items.items():
            st.markdown(f"#### {category}")
            for item in category_items:
                self._render_simple_item(item)
            st.markdown("")

    def _render_simple_item(self, item):
        """Render a simple item row for shared lists."""
        ingredient_name = item.ingredient.Name if item.ingredient else "Unknown"
        quantity = item.AggregatedQuantity or ""

        col1, col2 = st.columns([1, 5])

        with col1:
            checked = st.checkbox(
                "checked",
                value=item.IsChecked,
                key=f"shared_item_{item.ShoppingListItemId}",
                label_visibility="collapsed"
            )

            if checked != item.IsChecked:
                self.controller.check_item(item.ShoppingListItemId, checked)
                st.rerun()

        with col2:
            if item.IsChecked:
                st.markdown(f"~~{ingredient_name}~~ {quantity}")
            else:
                st.markdown(f"**{ingredient_name}** {quantity}")

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
