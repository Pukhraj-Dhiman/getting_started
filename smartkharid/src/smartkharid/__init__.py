"""SmartKharid: compare a product's price and reviews across stores and pick where to buy."""

from .models import PRESETS, Comparison, Offer, ProductDetails, ScoredOffer, Weights
from .service import compare, fetch_details, fetch_offers

__all__ = [
    "PRESETS",
    "Comparison",
    "Offer",
    "ProductDetails",
    "ScoredOffer",
    "Weights",
    "compare",
    "fetch_details",
    "fetch_offers",
]
