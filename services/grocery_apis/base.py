"""
Base class for grocery store API integrations.

All grocery store APIs should implement this interface to enable
consistent price comparison across multiple stores.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductMatch:
    """A product matched from a grocery store search."""
    store_name: str
    product_id: str
    product_name: str
    price: float
    unit: str  # "each", "per lb", "per oz", etc.
    size: Optional[str] = None  # "16 oz", "1 lb", etc.
    image_url: Optional[str] = None
    product_url: Optional[str] = None


@dataclass
class PriceResult:
    """Result of a price lookup for an ingredient."""
    success: bool
    ingredient_name: str
    products: list[ProductMatch]
    error: Optional[str] = None


class GroceryAPIBase(ABC):
    """Abstract base class for grocery store APIs."""

    @property
    @abstractmethod
    def store_name(self) -> str:
        """Return the store name (e.g., 'Kroger', 'Walmart')."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the API credentials are configured."""
        pass

    @abstractmethod
    def search_products(
        self,
        ingredient: str,
        limit: int = 5
    ) -> PriceResult:
        """
        Search for products matching an ingredient.

        Args:
            ingredient: The ingredient name to search for
            limit: Maximum number of results to return

        Returns:
            PriceResult with matching products or error
        """
        pass
