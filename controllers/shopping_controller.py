"""
Shopping Controller - manages shopping list view and interactions.

This controller handles:
- Loading and displaying shopping lists (filtered by authenticated user)
- Checking/unchecking items
- Generating shareable links

Multi-user support:
- Each user only sees their own shopping lists
- Shared links allow access to specific lists without ownership
"""

import streamlit as st
from typing import Optional
from dataclasses import dataclass

from config.settings import get_settings
from config.database import SessionLocal
from config.auth import get_current_user, require_auth, UserContext
from models import ShoppingList, ShoppingListItem
from models.repositories import ShoppingListRepository
from services.notification_service import NotificationService, SMSResult, EmailResult
from services.grocery_apis import KrogerAPI, PriceResult, ProductMatch


@dataclass
class ShoppingListSummary:
    """Summary of a shopping list for display."""
    id: int
    name: str
    item_count: int
    checked_count: int
    recipe_count: int
    status: str


@dataclass
class ItemPriceInfo:
    """Price information for a shopping list item."""
    item_id: int
    ingredient_name: str
    quantity: str
    best_match: Optional[ProductMatch]
    all_matches: list[ProductMatch]
    error: Optional[str] = None


@dataclass
class PriceComparisonResult:
    """Result of price comparison for a shopping list."""
    success: bool
    items: list[ItemPriceInfo]
    total_estimated: float
    store_name: str
    items_with_prices: int
    items_without_prices: int
    error: Optional[str] = None


class ShoppingController:
    """Controller for shopping list management."""

    def __init__(self):
        self._init_session_state()

    def _init_session_state(self):
        """Initialize session state if not already set."""
        if "shopping" not in st.session_state:
            st.session_state.shopping = {
                "current_list_id": None,
                "link_code": None,
                "shared_access_list_id": None,  # ID of list accessed via shared link
                "removed_items": {},  # {list_id: set of item_ids}
                "selected_products": {},  # {item_id: ProductMatch}
                "price_results": {},  # {list_id: PriceComparisonResult}
            }

    # ==========================================
    # Session State
    # ==========================================

    def get_current_list_id(self) -> Optional[int]:
        """Get the currently selected list ID."""
        return st.session_state.shopping["current_list_id"]

    def set_current_list_id(self, list_id: Optional[int]):
        """Set the currently selected list ID."""
        st.session_state.shopping["current_list_id"] = list_id
        st.session_state.shopping["link_code"] = None

    def get_link_code(self) -> Optional[str]:
        """Get the current shareable link code."""
        return st.session_state.shopping["link_code"]

    # ==========================================
    # Removed Items Management
    # ==========================================

    def get_removed_items(self, list_id: int) -> set[int]:
        """Get set of removed item IDs for a list."""
        return st.session_state.shopping["removed_items"].get(list_id, set())

    def remove_item(self, list_id: int, item_id: int):
        """Mark an item as removed (user already has it)."""
        if list_id not in st.session_state.shopping["removed_items"]:
            st.session_state.shopping["removed_items"][list_id] = set()
        st.session_state.shopping["removed_items"][list_id].add(item_id)

    def restore_item(self, list_id: int, item_id: int):
        """Restore a previously removed item."""
        if list_id in st.session_state.shopping["removed_items"]:
            st.session_state.shopping["removed_items"][list_id].discard(item_id)

    def is_item_removed(self, list_id: int, item_id: int) -> bool:
        """Check if an item is marked as removed."""
        return item_id in self.get_removed_items(list_id)

    # ==========================================
    # Product Selection Management
    # ==========================================

    def get_selected_product(self, item_id: int) -> Optional[ProductMatch]:
        """Get the selected product for an item."""
        return st.session_state.shopping["selected_products"].get(item_id)

    def set_selected_product(self, item_id: int, product: ProductMatch):
        """Set the selected product for an item."""
        st.session_state.shopping["selected_products"][item_id] = product

    def clear_selected_product(self, item_id: int):
        """Clear the selected product for an item."""
        st.session_state.shopping["selected_products"].pop(item_id, None)

    # ==========================================
    # Price Results Cache
    # ==========================================

    def get_cached_prices(self, list_id: int) -> Optional[PriceComparisonResult]:
        """Get cached price results for a list."""
        return st.session_state.shopping["price_results"].get(list_id)

    def set_cached_prices(self, list_id: int, result: PriceComparisonResult):
        """Cache price results for a list."""
        st.session_state.shopping["price_results"][list_id] = result

    def clear_cached_prices(self, list_id: int):
        """Clear cached price results for a list."""
        st.session_state.shopping["price_results"].pop(list_id, None)

    def get_effective_total(self, list_id: int) -> float:
        """
        Calculate the effective total based on selections and removals.

        Uses selected products where available, falls back to best match,
        and excludes removed items.
        """
        cached = self.get_cached_prices(list_id)
        if not cached or not cached.success:
            return 0.0

        removed = self.get_removed_items(list_id)
        total = 0.0

        for item_info in cached.items:
            if item_info.item_id in removed:
                continue

            # Use selected product if available, otherwise best match
            selected = self.get_selected_product(item_info.item_id)
            if selected:
                total += selected.price
            elif item_info.best_match:
                total += item_info.best_match.price

        return total

    # ==========================================
    # Authentication Helpers
    # ==========================================

    def get_current_user(self) -> Optional[UserContext]:
        """Get the current authenticated user."""
        return get_current_user()

    def can_access_list(self, list_id: int) -> bool:
        """
        Check if current user can access a shopping list.

        Access is granted if:
        - User owns the list, OR
        - User accessed via a valid shared link
        """
        # Check if accessing via shared link
        if st.session_state.shopping.get("shared_access_list_id") == list_id:
            return True

        # Check ownership
        user = get_current_user()
        if not user:
            return False

        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)
            return repo.is_owner(list_id, user.user_id)
        finally:
            db.close()

    # ==========================================
    # List Operations
    # ==========================================

    def get_all_lists(self) -> list[ShoppingListSummary]:
        """
        Get all active shopping lists for the current user.

        Returns an empty list if user is not authenticated.
        """
        user = get_current_user()
        if not user:
            return []

        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)
            lists = repo.get_all_active(user.user_id)

            summaries = []
            for sl in lists:
                items = sl.items if sl.items else []
                summaries.append(ShoppingListSummary(
                    id=sl.ShoppingListId,
                    name=sl.Name or f"List #{sl.ShoppingListId}",
                    item_count=len(items),
                    checked_count=sum(1 for i in items if i.IsChecked),
                    recipe_count=len(sl.recipes) if sl.recipes else 0,
                    status=sl.Status,
                ))
            return summaries
        finally:
            db.close()

    def get_list(self, list_id: int) -> Optional[ShoppingList]:
        """Get a shopping list by ID with all items."""
        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)
            return repo.get_by_id(list_id)
        finally:
            db.close()

    def get_list_by_link(self, link_code: str) -> Optional[ShoppingList]:
        """
        Get a shopping list by shareable link code.

        This also grants temporary access to the list for the session,
        allowing unauthenticated users to view shared lists.
        """
        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)
            shopping_list = repo.get_by_link_code(link_code)
            if shopping_list:
                # Grant access to this list for the session
                st.session_state.shopping["shared_access_list_id"] = shopping_list.ShoppingListId
            return shopping_list
        finally:
            db.close()

    def get_items_grouped(self, list_id: int) -> dict[str, list[ShoppingListItem]]:
        """Get shopping list items grouped by category."""
        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)
            return repo.get_items_by_category(list_id)
        finally:
            db.close()

    # ==========================================
    # Item Operations
    # ==========================================

    def toggle_item(self, item_id: int) -> Optional[bool]:
        """Toggle an item's checked status. Returns new status."""
        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)
            return repo.toggle_item(item_id)
        finally:
            db.close()

    def check_item(self, item_id: int, checked: bool):
        """Set an item's checked status."""
        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)
            repo.set_item_checked(item_id, checked)
        finally:
            db.close()

    # ==========================================
    # Link Operations
    # ==========================================

    def generate_link(self, list_id: int, expires_days: int = 7) -> Optional[str]:
        """
        Generate a shareable link for a shopping list.

        Only the owner can generate a link for their list.
        Returns None if the user doesn't have access.
        """
        if not self.can_access_list(list_id):
            return None

        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)

            # Check if link already exists
            existing = repo.get_link(list_id)
            if existing:
                link_code = existing.LinkCode
            else:
                link = repo.create_link(list_id, expires_days=expires_days)
                link_code = link.LinkCode

            st.session_state.shopping["link_code"] = link_code
            return link_code
        finally:
            db.close()

    def get_shareable_url(self, link_code: str) -> str:
        """Get the full shareable URL for a link code."""
        settings = get_settings()
        base_url = settings.app_base_url.rstrip('/') if settings.app_base_url else ""
        return f"{base_url}/Shopping_List?code={link_code}"

    # ==========================================
    # List Management
    # ==========================================

    def delete_list(self, list_id: int) -> bool:
        """
        Delete a shopping list.

        Only the owner can delete their list.
        """
        if not self.can_access_list(list_id):
            return False

        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)
            success = repo.delete(list_id)
            if success and st.session_state.shopping["current_list_id"] == list_id:
                st.session_state.shopping["current_list_id"] = None
                st.session_state.shopping["link_code"] = None
            return success
        finally:
            db.close()

    def mark_complete(self, list_id: int) -> bool:
        """
        Mark a shopping list as complete.

        Only the owner can mark their list as complete.
        """
        if not self.can_access_list(list_id):
            return False

        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)
            return repo.update_status(list_id, "completed")
        finally:
            db.close()

    # ==========================================
    # SMS Operations
    # ==========================================

    def is_sms_configured(self) -> bool:
        """Check if SMS is properly configured (including app base URL)."""
        notification = NotificationService()
        settings = get_settings()
        has_base_url = bool(settings.app_base_url)
        return notification.is_configured() and has_base_url

    def get_sms_config_issues(self) -> list[str]:
        """Get list of SMS configuration issues."""
        issues = []
        notification = NotificationService()
        settings = get_settings()

        if not settings.azure_comm_endpoint and not settings.azure_comm_connection_string:
            issues.append("Missing AZURE_COMM_ENDPOINT or AZURE_COMM_CONNECTION_STRING")
        if not settings.azure_comm_sender_number:
            issues.append("Missing AZURE_COMM_SENDER_NUMBER")
        if not settings.app_base_url:
            issues.append("Missing APP_BASE_URL (required for SMS links)")

        return issues

    def send_list_via_sms(
        self,
        list_id: int,
        phone_number: str,
    ) -> SMSResult:
        """
        Send shopping list to a phone number via SMS.

        Args:
            list_id: Shopping list ID
            phone_number: Recipient's phone number

        Returns:
            SMSResult with success status
        """
        # Get or create link code
        link_code = self.generate_link(list_id)

        # Build full URL (uses APP_BASE_URL from config)
        share_url = self.get_shareable_url(link_code)

        # Get list details
        shopping_list = self.get_list(list_id)
        if not shopping_list:
            return SMSResult(success=False, error="Shopping list not found")

        list_name = shopping_list.Name or "Shopping List"
        item_count = len(shopping_list.items) if shopping_list.items else 0

        # Send SMS
        notification = NotificationService()
        return notification.send_shopping_list_sms(
            phone_number=phone_number,
            list_name=list_name,
            item_count=item_count,
            share_url=share_url
        )

    def validate_phone(self, phone: str) -> tuple[bool, str]:
        """Validate a phone number. Returns (is_valid, message)."""
        notification = NotificationService()
        return notification.validate_phone_number(phone)

    def send_test_sms(self, phone_number: str) -> SMSResult:
        """Send a test SMS to verify configuration."""
        notification = NotificationService()
        return notification.send_test_sms(phone_number)

    # ==========================================
    # Email Operations
    # ==========================================

    def is_email_configured(self) -> bool:
        """Check if Email is properly configured (including app base URL)."""
        notification = NotificationService()
        settings = get_settings()
        has_base_url = bool(settings.app_base_url)
        return notification.is_email_configured() and has_base_url

    def get_email_config_issues(self) -> list[str]:
        """Get list of Email configuration issues."""
        issues = []
        settings = get_settings()

        if not settings.azure_comm_email_endpoint:
            issues.append("Missing AZURE_COMM_EMAIL_ENDPOINT")
        if not settings.azure_comm_email_sender:
            issues.append("Missing AZURE_COMM_EMAIL_SENDER")
        if not settings.app_base_url:
            issues.append("Missing APP_BASE_URL (required for email links)")

        return issues

    def send_list_via_email(self, list_id: int, email: str) -> EmailResult:
        """Send shopping list to an email address."""
        # Get or create link code
        link_code = self.generate_link(list_id)
        share_url = self.get_shareable_url(link_code)

        # Get list details
        shopping_list = self.get_list(list_id)
        if not shopping_list:
            return EmailResult(success=False, error="Shopping list not found")

        list_name = shopping_list.Name or "Shopping List"
        item_count = len(shopping_list.items) if shopping_list.items else 0

        # Send Email
        notification = NotificationService()
        return notification.send_shopping_list_email(
            to_email=email,
            list_name=list_name,
            item_count=item_count,
            share_url=share_url
        )

    def validate_email(self, email: str) -> tuple[bool, str]:
        """Validate an email address. Returns (is_valid, message)."""
        notification = NotificationService()
        return notification.validate_email(email)

    def send_test_email(self, email: str) -> EmailResult:
        """Send a test email to verify configuration."""
        notification = NotificationService()
        return notification.send_test_email(email)

    # ==========================================
    # Price Comparison Operations
    # ==========================================

    def is_kroger_configured(self) -> bool:
        """Check if Kroger API is properly configured."""
        kroger = KrogerAPI()
        return kroger.is_configured()

    def get_kroger_config_issues(self) -> list[str]:
        """Get list of Kroger configuration issues."""
        issues = []
        settings = get_settings()

        if not settings.kroger_client_id:
            issues.append("Missing KROGER_CLIENT_ID")
        if not settings.kroger_client_secret:
            issues.append("Missing KROGER_CLIENT_SECRET")
        if not settings.kroger_location_id:
            issues.append("KROGER_LOCATION_ID not set (prices may vary by location)")

        return issues

    def get_price_for_ingredient(
        self,
        ingredient_name: str,
        limit: int = 5
    ) -> PriceResult:
        """
        Get prices for a single ingredient from Kroger.

        Args:
            ingredient_name: Name of the ingredient to search
            limit: Maximum number of product matches to return

        Returns:
            PriceResult with matching products
        """
        kroger = KrogerAPI()
        return kroger.search_products(ingredient_name, limit=limit)

    def get_prices_for_list(self, list_id: int) -> PriceComparisonResult:
        """
        Get prices for all items in a shopping list.

        Args:
            list_id: Shopping list ID

        Returns:
            PriceComparisonResult with prices for each item
        """
        kroger = KrogerAPI()

        if not kroger.is_configured():
            return PriceComparisonResult(
                success=False,
                items=[],
                total_estimated=0.0,
                store_name="Kroger",
                items_with_prices=0,
                items_without_prices=0,
                error="Kroger API not configured"
            )

        # Get shopping list items
        shopping_list = self.get_list(list_id)
        if not shopping_list:
            return PriceComparisonResult(
                success=False,
                items=[],
                total_estimated=0.0,
                store_name="Kroger",
                items_with_prices=0,
                items_without_prices=0,
                error="Shopping list not found"
            )

        items = shopping_list.items or []
        if not items:
            return PriceComparisonResult(
                success=True,
                items=[],
                total_estimated=0.0,
                store_name="Kroger",
                items_with_prices=0,
                items_without_prices=0
            )

        # Fetch prices for each item
        item_prices: list[ItemPriceInfo] = []
        total = 0.0
        with_prices = 0
        without_prices = 0

        for item in items:
            ingredient_name = item.ingredient.Name if item.ingredient else "Unknown"
            quantity = item.AggregatedQuantity or ""

            # Search Kroger for this ingredient
            result = kroger.search_products(ingredient_name, limit=5)

            if result.success and result.products:
                best_match = result.products[0]  # First result is best match
                total += best_match.price
                with_prices += 1

                item_prices.append(ItemPriceInfo(
                    item_id=item.ShoppingListItemId,
                    ingredient_name=ingredient_name,
                    quantity=quantity,
                    best_match=best_match,
                    all_matches=result.products
                ))
            else:
                without_prices += 1
                item_prices.append(ItemPriceInfo(
                    item_id=item.ShoppingListItemId,
                    ingredient_name=ingredient_name,
                    quantity=quantity,
                    best_match=None,
                    all_matches=[],
                    error=result.error if not result.success else "No products found"
                ))

        return PriceComparisonResult(
            success=True,
            items=item_prices,
            total_estimated=total,
            store_name="Kroger",
            items_with_prices=with_prices,
            items_without_prices=without_prices
        )

    def find_kroger_locations(self, zip_code: str) -> list[dict]:
        """
        Find Kroger store locations near a zip code.

        Returns list of locations with location_id, name, and address.
        """
        kroger = KrogerAPI()
        return kroger.find_nearby_locations(zip_code, limit=5)
