"""
Kroger API client for product search and price lookup.

Kroger API Documentation: https://developer.kroger.com/

Authentication: OAuth2 Client Credentials flow
- Obtain access token using client_id and client_secret
- Token is valid for 30 minutes

Endpoints used:
- POST /connect/oauth2/token - Get access token
- GET /products - Search products by term
- GET /locations - Find nearby stores (optional)
"""

import logging
import time
from typing import Optional
import base64

import httpx

from config.settings import get_settings
from services.grocery_apis.base import GroceryAPIBase, ProductMatch, PriceResult

logger = logging.getLogger(__name__)


class KrogerAPI(GroceryAPIBase):
    """Kroger API client for product search and pricing."""

    BASE_URL = "https://api.kroger.com/v1"
    TOKEN_URL = "https://api.kroger.com/v1/connect/oauth2/token"

    def __init__(self):
        self.settings = get_settings()
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._last_auth_error: Optional[str] = None

    @property
    def store_name(self) -> str:
        return "Kroger"

    def is_configured(self) -> bool:
        """Check if Kroger API credentials are configured."""
        return bool(
            self.settings.kroger_client_id and
            self.settings.kroger_client_secret
        )

    def _get_access_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if expired.

        Uses OAuth2 Client Credentials flow.
        """
        # Clear any previous auth error
        self._last_auth_error = None

        # Return cached token if still valid (with 60s buffer)
        if self._access_token and time.time() < (self._token_expires_at - 60):
            return self._access_token

        if not self.is_configured():
            self._last_auth_error = "Kroger API credentials not configured"
            logger.error(self._last_auth_error)
            return None

        try:
            # Create Basic auth header (strip whitespace from credentials)
            client_id = self.settings.kroger_client_id.strip()
            client_secret = self.settings.kroger_client_secret.strip()
            credentials = f"{client_id}:{client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {encoded_credentials}"
            }

            # Request token with product.compact scope
            data = {
                "grant_type": "client_credentials",
                "scope": "product.compact"
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.TOKEN_URL,
                    headers=headers,
                    data=data
                )
                response.raise_for_status()

            token_data = response.json()
            self._access_token = token_data["access_token"]
            # Token expires_in is in seconds (typically 1800 = 30 min)
            self._token_expires_at = time.time() + token_data.get("expires_in", 1800)

            logger.info("Kroger access token obtained successfully")
            return self._access_token

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                self._last_auth_error = (
                    "Invalid Kroger API credentials. Troubleshooting tips:\n"
                    "1. Verify KROGER_CLIENT_ID and KROGER_CLIENT_SECRET are correct\n"
                    "2. Ensure no extra whitespace in your .env file\n"
                    "3. Confirm your Kroger Developer app has 'Product' API access enabled\n"
                    "4. Try regenerating your client secret at developer.kroger.com"
                )
            elif status == 400:
                self._last_auth_error = "Bad request to Kroger API. The credentials may be malformed or contain invalid characters."
            else:
                self._last_auth_error = f"Kroger API error (HTTP {status})"
            logger.error(f"Kroger auth failed: {status} - {e.response.text}")
            return None
        except httpx.ConnectError:
            self._last_auth_error = "Could not connect to Kroger API. Check your network connection."
            logger.error(self._last_auth_error)
            return None
        except httpx.TimeoutException:
            self._last_auth_error = "Kroger API request timed out. Please try again."
            logger.error(self._last_auth_error)
            return None
        except Exception as e:
            self._last_auth_error = f"Kroger authentication error: {str(e)}"
            logger.error(f"Kroger auth error: {e}")
            return None

    def search_products(
        self,
        ingredient: str,
        limit: int = 5
    ) -> PriceResult:
        """
        Search for products matching an ingredient.

        Args:
            ingredient: The ingredient name to search for
            limit: Maximum number of results to return (max 50)

        Returns:
            PriceResult with matching products or error
        """
        if not self.is_configured():
            return PriceResult(
                success=False,
                ingredient_name=ingredient,
                products=[],
                error="Kroger API credentials not configured"
            )

        token = self._get_access_token()
        if not token:
            return PriceResult(
                success=False,
                ingredient_name=ingredient,
                products=[],
                error=self._last_auth_error or "Failed to authenticate with Kroger API"
            )

        try:
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {token}"
            }

            params = {
                "filter.term": ingredient,
                "filter.limit": min(limit, 50)
            }

            # Add location filter for accurate local pricing
            if self.settings.kroger_location_id:
                params["filter.locationId"] = self.settings.kroger_location_id

            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/products",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()

            data = response.json()
            products = []

            for item in data.get("data", []):
                product = self._parse_product(item)
                if product:
                    products.append(product)

            return PriceResult(
                success=True,
                ingredient_name=ingredient,
                products=products
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"Kroger API error: {e.response.status_code}"
            logger.error(f"{error_msg} - {e.response.text}")
            return PriceResult(
                success=False,
                ingredient_name=ingredient,
                products=[],
                error=error_msg
            )
        except Exception as e:
            logger.error(f"Kroger search error: {e}")
            return PriceResult(
                success=False,
                ingredient_name=ingredient,
                products=[],
                error=str(e)
            )

    def _parse_product(self, item: dict) -> Optional[ProductMatch]:
        """Parse a product from the Kroger API response."""
        try:
            product_id = item.get("productId", "")
            description = item.get("description", "")

            # Get price from items array (can have multiple sizes)
            items = item.get("items", [])
            if not items:
                return None

            # Use first item (usually the primary size)
            first_item = items[0]
            price_info = first_item.get("price", {})

            # Prefer regular price, fall back to promo
            price = price_info.get("regular") or price_info.get("promo")
            if price is None:
                return None

            # Get size info
            size = first_item.get("size", "")

            # Determine unit type
            sold_by = first_item.get("soldBy", "UNIT")
            if sold_by == "WEIGHT":
                unit = "per lb"
            else:
                unit = "each"

            # Get image URL (thumbnail)
            images = item.get("images", [])
            image_url = None
            for img in images:
                if img.get("perspective") == "front":
                    sizes = img.get("sizes", [])
                    # Get thumbnail size
                    for size_info in sizes:
                        if size_info.get("size") == "thumbnail":
                            image_url = size_info.get("url")
                            break
                    if image_url:
                        break

            return ProductMatch(
                store_name=self.store_name,
                product_id=product_id,
                product_name=description,
                price=float(price),
                unit=unit,
                size=size,
                image_url=image_url,
                product_url=f"https://www.kroger.com/p/{product_id}"
            )

        except Exception as e:
            logger.warning(f"Failed to parse Kroger product: {e}")
            return None

    def find_nearby_locations(
        self,
        zip_code: str,
        limit: int = 5
    ) -> list[dict]:
        """
        Find Kroger store locations near a zip code.

        Returns list of locations with id, name, and address.
        Useful for setting kroger_location_id for accurate pricing.
        """
        if not self.is_configured():
            return []

        token = self._get_access_token()
        if not token:
            return []

        try:
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {token}"
            }

            params = {
                "filter.zipCode.near": zip_code,
                "filter.limit": limit
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/locations",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()

            data = response.json()
            locations = []

            for loc in data.get("data", []):
                address = loc.get("address", {})
                locations.append({
                    "location_id": loc.get("locationId"),
                    "name": loc.get("name"),
                    "address": f"{address.get('addressLine1', '')}, {address.get('city', '')} {address.get('state', '')} {address.get('zipCode', '')}"
                })

            return locations

        except Exception as e:
            logger.error(f"Kroger locations error: {e}")
            return []
