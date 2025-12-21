"""
Notification Service - handles SMS delivery via Azure Communication Services.

This service sends shopping list links to users via SMS.
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SMSResult:
    """Result of an SMS send attempt."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class NotificationService:
    """Service for sending notifications (SMS, email, etc.)."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    def _get_client(self):
        """Lazy-load the SMS client."""
        if self._client is None:
            try:
                from azure.communication.sms import SmsClient
                connection_string = self.settings.azure_comm_connection_string
                if connection_string:
                    self._client = SmsClient.from_connection_string(connection_string)
            except ImportError:
                logger.warning("azure-communication-sms not installed")
            except Exception as e:
                logger.error(f"Failed to create SMS client: {e}")
        return self._client

    def is_configured(self) -> bool:
        """Check if SMS is properly configured."""
        return bool(
            self.settings.azure_comm_connection_string and
            self.settings.azure_comm_sender_number
        )

    def validate_phone_number(self, phone: str) -> tuple[bool, str]:
        """
        Validate and normalize a phone number.

        Returns (is_valid, normalized_number_or_error)
        """
        # Remove all non-digit characters except leading +
        cleaned = re.sub(r'[^\d+]', '', phone)

        # Handle various formats
        if cleaned.startswith('+1'):
            # Already in E.164 format
            if len(cleaned) == 12:  # +1 + 10 digits
                return True, cleaned
        elif cleaned.startswith('1') and len(cleaned) == 11:
            # US number with country code but no +
            return True, f"+{cleaned}"
        elif len(cleaned) == 10:
            # US number without country code
            return True, f"+1{cleaned}"

        return False, "Please enter a valid US phone number (10 digits)"

    def send_shopping_list_sms(
        self,
        phone_number: str,
        list_name: str,
        item_count: int,
        share_url: str
    ) -> SMSResult:
        """
        Send a shopping list link via SMS.

        Args:
            phone_number: Recipient phone number (will be normalized)
            list_name: Name of the shopping list
            item_count: Number of items in the list
            share_url: Full URL to the shopping list

        Returns:
            SMSResult with success status and any error message
        """
        # Validate phone number
        is_valid, result = self.validate_phone_number(phone_number)
        if not is_valid:
            return SMSResult(success=False, error=result)

        normalized_phone = result

        # Check if configured
        if not self.is_configured():
            return SMSResult(
                success=False,
                error="SMS is not configured. Please set up Azure Communication Services."
            )

        # Build message
        message = (
            f"Your shopping list is ready!\n\n"
            f"📋 {list_name}\n"
            f"🛒 {item_count} items\n\n"
            f"View & check off items:\n{share_url}"
        )

        # Send SMS
        try:
            client = self._get_client()
            if not client:
                return SMSResult(
                    success=False,
                    error="SMS client not available"
                )

            response = client.send(
                from_=self.settings.azure_comm_sender_number,
                to=normalized_phone,
                message=message
            )

            # Check response
            sms_response = response[0]
            if sms_response.successful:
                return SMSResult(
                    success=True,
                    message_id=sms_response.message_id
                )
            else:
                return SMSResult(
                    success=False,
                    error=f"SMS failed: {sms_response.error_message}"
                )

        except Exception as e:
            logger.error(f"SMS send error: {e}")
            return SMSResult(
                success=False,
                error=f"Failed to send SMS: {str(e)}"
            )

    def send_test_sms(self, phone_number: str) -> SMSResult:
        """Send a test SMS to verify configuration."""
        is_valid, result = self.validate_phone_number(phone_number)
        if not is_valid:
            return SMSResult(success=False, error=result)

        normalized_phone = result

        if not self.is_configured():
            return SMSResult(
                success=False,
                error="SMS is not configured"
            )

        try:
            client = self._get_client()
            if not client:
                return SMSResult(success=False, error="SMS client not available")

            response = client.send(
                from_=self.settings.azure_comm_sender_number,
                to=normalized_phone,
                message="Test message from Cooking Assistant 🍳"
            )

            sms_response = response[0]
            if sms_response.successful:
                return SMSResult(success=True, message_id=sms_response.message_id)
            else:
                return SMSResult(success=False, error=sms_response.error_message)

        except Exception as e:
            logger.error(f"Test SMS error: {e}")
            return SMSResult(success=False, error=str(e))
