"""Product details that every source can fall back on.

Store listings already say quite a lot about a product (title, photos, rating, short facts
such as "128 GB"). `basic_details` turns them into a ProductDetails, so the app can always
show something even when a source has no richer details or fetching them fails.
"""

from __future__ import annotations

from dataclasses import fields, replace

from .formatting import format_money
from .models import Offer, ProductDetails

MAX_IMAGES = 8
MAX_HIGHLIGHTS = 8


def _unique(items) -> list:
    seen, out = set(), []
    for item in items:
        key = item.casefold() if isinstance(item, str) else item
        if item and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def price_range(offers: list[Offer]) -> str:
    prices = [o.total_price for o in offers if o.in_stock] or [o.total_price for o in offers]
    if not prices:
        return ""
    cur = offers[0].currency
    lo, hi = min(prices), max(prices)
    return format_money(lo, cur) if lo == hi else f"{format_money(lo, cur)} – {format_money(hi, cur)}"


def basic_details(offers: list[Offer], source: str, note: str = "") -> ProductDetails | None:
    """Details assembled from the listings themselves (best listing first)."""
    if not offers:
        return None
    # Stores usually show the same product-level rating, so take the one with most reviews
    # instead of adding counts up.
    rated = [o for o in offers if o.rating is not None and o.review_count > 0]
    top = max(rated, key=lambda o: o.review_count) if rated else None
    return ProductDetails(
        title=offers[0].title,
        images=tuple(_unique(o.image_url for o in offers))[:MAX_IMAGES],
        highlights=tuple(_unique(h for o in offers for h in o.highlights))[:MAX_HIGHLIGHTS],
        rating=top.rating if top else None,
        review_count=top.review_count if top else 0,
        price_range=price_range(offers),
        source=source,
        note=note,
    )


def merge(primary: ProductDetails, fallback: ProductDetails | None) -> ProductDetails:
    """`primary`, with any empty field filled in from `fallback`."""
    if fallback is None:
        return primary
    filled = {
        f.name: getattr(fallback, f.name)
        for f in fields(ProductDetails)
        if f.name not in ("source", "note") and not getattr(primary, f.name)
    }
    return replace(primary, **filled)
