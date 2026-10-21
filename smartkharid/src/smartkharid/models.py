"""Core data types shared by the data sources, the ranking engine and the UI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Offer:
    """One listing of a product on one store."""

    store: str
    title: str
    price: float
    url: str
    currency: str = "INR"
    shipping: float = 0.0
    rating: float | None = None  # customer rating on a 0-5 scale
    review_count: int = 0
    delivery_days: int | None = None
    store_rating: float | None = None  # seller / store trust on a 0-5 scale
    in_stock: bool = True
    source: str = ""  # name of the data source that produced this offer
    image_url: str | None = None

    @property
    def total_price(self) -> float:
        """What the buyer actually pays: item price plus shipping."""
        return self.price + self.shipping


@dataclass(frozen=True)
class Weights:
    """How much the buyer cares about each criterion. Any non-negative scale works."""

    price: float = 5.0
    reviews: float = 4.0
    delivery: float = 1.0
    trust: float = 1.0

    def normalized(self) -> Weights:
        """Weights rescaled to sum to 1 (equal weights if they are all zero)."""
        values = [max(0.0, v) for v in (self.price, self.reviews, self.delivery, self.trust)]
        total = sum(values)
        if total == 0:
            return Weights(0.25, 0.25, 0.25, 0.25)
        return Weights(*(v / total for v in values))


# Ready-made weight presets for the UI.
PRESETS: dict[str, Weights] = {
    "Balanced": Weights(5, 4, 1, 1),
    "Lowest price": Weights(9, 2, 1, 1),
    "Best quality": Weights(2, 8, 1, 3),
    "Fast delivery": Weights(4, 3, 6, 1),
}


@dataclass(frozen=True)
class ScoredOffer:
    """An offer with its overall score (0-100) and the per-criterion scores (0-1)."""

    offer: Offer
    score: float
    price_score: float
    review_score: float
    delivery_score: float
    trust_score: float
    adjusted_rating: float | None = None  # rating after correcting for few reviews
    badges: tuple[str, ...] = ()


@dataclass
class Comparison:
    """Result of comparing one product across stores."""

    query: str
    ranked: list[ScoredOffer] = field(default_factory=list)  # one per store, best first
    recommended: ScoredOffer | None = None
    reasons: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)  # source name -> error message
    filtered_out: int = 0  # listings dropped as accessories / different variants
