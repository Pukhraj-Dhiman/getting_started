"""SmartKharid: compare a product's price and reviews across stores and pick where to buy."""

from .models import PRESETS, Comparison, Offer, ScoredOffer, Weights
from .service import compare, fetch_offers

__all__ = ["PRESETS", "Comparison", "Offer", "ScoredOffer", "Weights", "compare", "fetch_offers"]
