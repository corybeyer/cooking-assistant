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

        # Share section
        self._render_share_section(list_id)

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

    def _render_share_section(self, list_id: int):
        """Render the share/send section."""
        st.markdown("#### 📤 Share List")

        tab1, tab2 = st.tabs(["📱 Send via SMS", "🔗 Copy Link"])

        with tab1:
            self._render_sms_section(list_id)

        with tab2:
            self._render_link_section(list_id)

    def _render_sms_section(self, list_id: int):
        """Render SMS send form."""
        # Check if SMS is configured
        if not self.controller.is_sms_configured():
            st.warning("SMS is not configured. Please set up Azure Communication Services.")
            st.markdown("Required environment variables:")
            st.code("AZURE_COMM_CONNECTION_STRING\nAZURE_COMM_SENDER_NUMBER")
            return

        # Initialize session state for SMS
        if "sms_phone" not in st.session_state:
            st.session_state.sms_phone = ""
        if "sms_sent" not in st.session_state:
            st.session_state.sms_sent = False
        if "sms_error" not in st.session_state:
            st.session_state.sms_error = None

        # Phone input
        phone = st.text_input(
            "Phone number:",
            value=st.session_state.sms_phone,
            placeholder="(555) 123-4567",
            help="Enter a US phone number"
        )
        st.session_state.sms_phone = phone

        # Send button
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📲 Send to Phone", type="primary", use_container_width=True):
                if not phone:
                    st.session_state.sms_error = "Please enter a phone number"
                else:
                    # Validate phone
                    is_valid, message = self.controller.validate_phone(phone)
                    if not is_valid:
                        st.session_state.sms_error = message
                    else:
                        # Send SMS
                        with st.spinner("Sending..."):
                            result = self.controller.send_list_via_sms(list_id, phone)

                        if result.success:
                            st.session_state.sms_sent = True
                            st.session_state.sms_error = None
                        else:
                            st.session_state.sms_error = result.error
                            st.session_state.sms_sent = False

                st.rerun()

        # Show status
        if st.session_state.sms_sent:
            st.success("✅ Shopping list sent! Check your phone.")
            st.session_state.sms_sent = False  # Reset for next time

        if st.session_state.sms_error:
            st.error(st.session_state.sms_error)
            st.session_state.sms_error = None  # Reset for next time

    def _render_link_section(self, list_id: int):
        """Render shareable link section."""
        if st.button("🔗 Generate Link", use_container_width=True):
            link_code = self.controller.generate_link(list_id)
            st.session_state.shopping["link_code"] = link_code
            st.rerun()

        link_code = self.controller.get_link_code()
        if link_code:
            share_url = self.controller.get_shareable_url(link_code)
            st.success("Link generated!")
            st.code(share_url)
            st.caption("Copy this link and share it")

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
