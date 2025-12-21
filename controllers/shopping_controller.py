"""
Shopping Controller - manages shopping list view and interactions.

This controller handles:
- Loading and displaying shopping lists
- Checking/unchecking items
- Generating shareable links
"""

import streamlit as st
from typing import Optional
from dataclasses import dataclass

from app.database import SessionLocal
from app.models import ShoppingList, ShoppingListItem
from app.models.repositories import ShoppingListRepository
from services.notification_service import NotificationService, SMSResult


@dataclass
class ShoppingListSummary:
    """Summary of a shopping list for display."""
    id: int
    name: str
    item_count: int
    checked_count: int
    recipe_count: int
    status: str


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
    # List Operations
    # ==========================================

    def get_all_lists(self) -> list[ShoppingListSummary]:
        """Get all active shopping lists."""
        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)
            lists = repo.get_all_active()

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
        """Get a shopping list by shareable link code."""
        db = SessionLocal()
        try:
            repo = ShoppingListRepository(db)
            return repo.get_by_link_code(link_code)
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

    def generate_link(self, list_id: int, expires_days: int = 7) -> str:
        """Generate a shareable link for a shopping list."""
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
        # In production, this would use the actual domain
        # For now, construct a relative URL
        return f"/Shopping_List?code={link_code}"

    # ==========================================
    # List Management
    # ==========================================

    def delete_list(self, list_id: int) -> bool:
        """Delete a shopping list."""
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
        """Mark a shopping list as complete."""
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
        """Check if SMS is properly configured."""
        notification = NotificationService()
        return notification.is_configured()

    def send_list_via_sms(
        self,
        list_id: int,
        phone_number: str,
        base_url: str = ""
    ) -> SMSResult:
        """
        Send shopping list to a phone number via SMS.

        Args:
            list_id: Shopping list ID
            phone_number: Recipient's phone number
            base_url: Base URL for the app (for building share link)

        Returns:
            SMSResult with success status
        """
        # Get or create link code
        link_code = self.generate_link(list_id)

        # Build full URL
        share_url = f"{base_url}/Shopping_List?code={link_code}" if base_url else self.get_shareable_url(link_code)

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
