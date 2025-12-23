"""
Notification Service - handles SMS and Email delivery via Azure Communication Services.

This service sends shopping list links to users via SMS or Email.

Supports two authentication methods:
1. Managed Identity (preferred in Azure) - set AZURE_COMM_ENDPOINT
2. Connection String (for local dev) - set AZURE_COMM_CONNECTION_STRING
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass

from config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SMSResult:
    """Result of an SMS send attempt."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class EmailResult:
    """Result of an email send attempt."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class NotificationService:
    """Service for sending notifications (SMS, email, etc.)."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._email_client = None

    def _get_client(self):
        """
        Lazy-load the SMS client.

        Prefers Managed Identity (endpoint) over connection string.
        """
        if self._client is None:
            try:
                from azure.communication.sms import SmsClient

                endpoint = self.settings.azure_comm_endpoint
                connection_string = self.settings.azure_comm_connection_string

                if endpoint:
                    # Use Managed Identity authentication
                    from azure.identity import DefaultAzureCredential
                    credential = DefaultAzureCredential()
                    self._client = SmsClient(endpoint, credential)
                    logger.info("SMS client initialized with Managed Identity")
                elif connection_string:
                    # Fall back to connection string
                    self._client = SmsClient.from_connection_string(connection_string)
                    logger.info("SMS client initialized with connection string")

            except ImportError as e:
                logger.warning(f"Required package not installed: {e}")
            except Exception as e:
                logger.error(f"Failed to create SMS client: {e}")
        return self._client

    def is_configured(self) -> bool:
        """Check if SMS is properly configured."""
        has_auth = bool(
            self.settings.azure_comm_endpoint or
            self.settings.azure_comm_connection_string
        )
        has_sender = bool(self.settings.azure_comm_sender_number)
        return has_auth and has_sender

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
            if not response:
                return SMSResult(
                    success=False,
                    error="SMS service returned empty response"
                )
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

            if not response:
                return SMSResult(success=False, error="SMS service returned empty response")
            sms_response = response[0]
            if sms_response.successful:
                return SMSResult(success=True, message_id=sms_response.message_id)
            else:
                return SMSResult(success=False, error=sms_response.error_message)

        except Exception as e:
            logger.error(f"Test SMS error: {e}")
            return SMSResult(success=False, error=str(e))

    # ==========================================
    # Email Methods
    # ==========================================

    def _get_email_client(self):
        """Lazy-load the Email client using Managed Identity."""
        if self._email_client is None:
            try:
                from azure.communication.email import EmailClient

                endpoint = self.settings.azure_comm_email_endpoint
                if endpoint:
                    from azure.identity import DefaultAzureCredential
                    credential = DefaultAzureCredential()
                    self._email_client = EmailClient(endpoint, credential)
                    logger.info("Email client initialized with Managed Identity")

            except ImportError as e:
                logger.warning(f"Email package not installed: {e}")
            except Exception as e:
                logger.error(f"Failed to create Email client: {e}")
        return self._email_client

    def is_email_configured(self) -> bool:
        """Check if Email is properly configured."""
        has_endpoint = bool(self.settings.azure_comm_email_endpoint)
        has_sender = bool(self.settings.azure_comm_email_sender)
        return has_endpoint and has_sender

    def validate_email(self, email: str) -> tuple[bool, str]:
        """Validate an email address. Returns (is_valid, email_or_error)."""
        email = email.strip().lower()
        # Simple email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, email
        return False, "Please enter a valid email address"

    def send_shopping_list_email(
        self,
        to_email: str,
        list_name: str,
        item_count: int,
        share_url: str
    ) -> EmailResult:
        """
        Send a shopping list link via email.

        Args:
            to_email: Recipient email address
            list_name: Name of the shopping list
            item_count: Number of items in the list
            share_url: Full URL to the shopping list

        Returns:
            EmailResult with success status
        """
        # Validate email
        is_valid, result = self.validate_email(to_email)
        if not is_valid:
            return EmailResult(success=False, error=result)

        validated_email = result

        # Check if configured
        if not self.is_email_configured():
            return EmailResult(
                success=False,
                error="Email is not configured. Please set up Azure Communication Services Email."
            )

        try:
            client = self._get_email_client()
            if not client:
                return EmailResult(success=False, error="Email client not available")

            # Build email message
            message = {
                "senderAddress": self.settings.azure_comm_email_sender,
                "recipients": {
                    "to": [{"address": validated_email}]
                },
                "content": {
                    "subject": f"Your Shopping List: {list_name}",
                    "html": f"""
                        <html>
                        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                            <h2>Your shopping list is ready!</h2>
                            <p><strong>{list_name}</strong></p>
                            <p>{item_count} items to get</p>
                            <p>
                                <a href="{share_url}"
                                   style="display: inline-block; padding: 12px 24px;
                                          background-color: #4CAF50; color: white;
                                          text-decoration: none; border-radius: 4px;">
                                    View Shopping List
                                </a>
                            </p>
                            <p style="color: #666; font-size: 12px;">
                                Or copy this link: {share_url}
                            </p>
                        </body>
                        </html>
                    """,
                    "plainText": f"Your shopping list is ready!\n\n{list_name}\n{item_count} items\n\nView your list: {share_url}"
                }
            }

            # Send email (this is async, we poll for status)
            poller = client.begin_send(message)
            result = poller.result()

            if result["status"] == "Succeeded":
                return EmailResult(success=True, message_id=result.get("id"))
            else:
                return EmailResult(
                    success=False,
                    error=f"Email failed: {result.get('error', {}).get('message', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Email send error: {e}")
            return EmailResult(success=False, error=f"Failed to send email: {str(e)}")

    def send_test_email(self, to_email: str) -> EmailResult:
        """Send a test email to verify configuration."""
        is_valid, result = self.validate_email(to_email)
        if not is_valid:
            return EmailResult(success=False, error=result)

        validated_email = result

        if not self.is_email_configured():
            return EmailResult(success=False, error="Email is not configured")

        try:
            client = self._get_email_client()
            if not client:
                return EmailResult(success=False, error="Email client not available")

            message = {
                "senderAddress": self.settings.azure_comm_email_sender,
                "recipients": {
                    "to": [{"address": validated_email}]
                },
                "content": {
                    "subject": "Test from Cooking Assistant",
                    "plainText": "This is a test email from your Cooking Assistant app!"
                }
            }

            poller = client.begin_send(message)
            result = poller.result()

            if result["status"] == "Succeeded":
                return EmailResult(success=True, message_id=result.get("id"))
            else:
                return EmailResult(
                    success=False,
                    error=result.get("error", {}).get("message", "Unknown error")
                )

        except Exception as e:
            logger.error(f"Test email error: {e}")
            return EmailResult(success=False, error=str(e))
