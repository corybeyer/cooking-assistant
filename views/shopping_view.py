"""
Shopping View - UI for viewing and managing shopping lists.

This view handles:
- Displaying shopping lists
- Checking off items
- Sharing lists via link
- Price comparison via Kroger API
"""

import streamlit as st

from controllers.shopping_controller import ShoppingController, PriceComparisonResult
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

        # Price comparison section
        self._render_price_comparison(list_id)
        st.markdown("---")

        # Share section
        self._render_share_section(list_id)
        st.markdown("---")

        # Items grouped by category
        grouped = self.controller.get_items_grouped(list_id)
        render_shopping_items_grouped(grouped, self.controller.check_item)

    def _render_price_comparison(self, list_id: int):
        """Render the price comparison section."""
        st.markdown("#### Price Comparison")

        # Check if Kroger is configured
        if not self.controller.is_kroger_configured():
            issues = self.controller.get_kroger_config_issues()
            st.warning("Kroger price comparison is not configured.")
            if issues:
                with st.expander("Configuration needed"):
                    for issue in issues:
                        st.markdown(f"- {issue}")
            return

        # Initialize session state for price results
        if "price_results" not in st.session_state:
            st.session_state.price_results = {}

        # Check if we have cached results for this list
        cached_result = st.session_state.price_results.get(list_id)

        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("Get Kroger Prices", type="primary", use_container_width=True):
                with st.spinner("Fetching prices from Kroger..."):
                    result = self.controller.get_prices_for_list(list_id)
                    st.session_state.price_results[list_id] = result
                    st.rerun()

        with col2:
            if cached_result:
                if st.button("Clear", use_container_width=True):
                    del st.session_state.price_results[list_id]
                    st.rerun()

        # Display results if available
        if cached_result:
            self._render_price_results(cached_result)

    def _render_price_results(self, result: PriceComparisonResult):
        """Render the price comparison results."""
        if not result.success:
            st.error(f"Failed to fetch prices: {result.error}")
            return

        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Estimated Total", f"${result.total_estimated:.2f}")
        with col2:
            st.metric("Items Priced", f"{result.items_with_prices}")
        with col3:
            st.metric("Not Found", f"{result.items_without_prices}")

        if result.items_without_prices > 0:
            st.caption("Some items couldn't be matched. Total may be higher.")

        # Item-by-item breakdown
        with st.expander("View Price Details", expanded=False):
            for item_info in result.items:
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    st.markdown(f"**{item_info.ingredient_name}**")
                    if item_info.quantity:
                        st.caption(item_info.quantity)

                with col2:
                    if item_info.best_match:
                        st.markdown(f"{item_info.best_match.product_name}")
                        if item_info.best_match.size:
                            st.caption(item_info.best_match.size)
                    else:
                        st.caption(item_info.error or "Not found")

                with col3:
                    if item_info.best_match:
                        st.markdown(f"**${item_info.best_match.price:.2f}**")
                        st.caption(item_info.best_match.unit)
                    else:
                        st.markdown("--")

                # Show alternative products in a nested expander
                if len(item_info.all_matches) > 1:
                    with st.expander(f"See {len(item_info.all_matches) - 1} alternatives"):
                        for alt in item_info.all_matches[1:]:
                            alt_col1, alt_col2 = st.columns([3, 1])
                            with alt_col1:
                                st.markdown(f"{alt.product_name}")
                                if alt.size:
                                    st.caption(alt.size)
                            with alt_col2:
                                st.markdown(f"${alt.price:.2f}")

                st.divider()

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
