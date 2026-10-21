"""Score store offers and pick the one to buy from.

Every offer gets four sub-scores between 0 and 1:

* price    - 1.0 for the cheapest offer (incl. shipping); every 1% above it costs 0.03,
             so an offer 10% dearer scores 0.7 and one 33% dearer scores 0.
* reviews  - the store's rating, corrected for how many people rated it (a 5.0 from
             3 reviews is worth less than a 4.4 from 10,000). Uses a Bayesian average
             that pulls ratings with few reviews towards a neutral 3.5.
* delivery - 1.0 for next-day delivery, falling to 0 at 8+ days. Unknown -> 0.5.
* trust    - the store/seller rating, if the source provides one. Unknown -> 0.5.

The overall score (0-100) is the weighted sum using the buyer's priorities.
"""

from __future__ import annotations

from dataclasses import replace
from statistics import mean

from .formatting import format_count, format_money
from .models import Offer, ScoredOffer, Weights

PRICE_SENSITIVITY = 3.0
RATING_PRIOR_MEAN = 3.5
RATING_PRIOR_REVIEWS = 25  # reviews needed before a store's own rating outweighs the prior
NEUTRAL = 0.5

BADGE_RECOMMENDED = "Recommended"
BADGE_CHEAPEST = "Cheapest"
BADGE_TOP_RATED = "Top rated"
BADGE_FASTEST = "Fastest delivery"
BADGE_OUT_OF_STOCK = "Out of stock"


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def adjusted_rating(rating: float | None, reviews: int) -> float:
    """Bayesian average: blends the store's rating with a neutral prior by review count."""
    if rating is None or reviews <= 0:
        return RATING_PRIOR_MEAN
    return (RATING_PRIOR_MEAN * RATING_PRIOR_REVIEWS + rating * reviews) / (RATING_PRIOR_REVIEWS + reviews)


def price_score(total: float, cheapest: float) -> float:
    if cheapest <= 0:
        return NEUTRAL
    return _clamp(1 - PRICE_SENSITIVITY * (total - cheapest) / cheapest)


def review_score(rating: float | None, reviews: int) -> float:
    # 2.5 stars or worse -> 0, 5 stars -> 1.
    return _clamp((adjusted_rating(rating, reviews) - 2.5) / 2.5)


def delivery_score(days: int | None) -> float:
    if days is None:
        return NEUTRAL
    return _clamp(1 - (max(days, 1) - 1) / 7)


def trust_score(store_rating: float | None) -> float:
    if store_rating is None:
        return NEUTRAL
    return _clamp((store_rating - 2.5) / 2.5)


def score_offers(offers: list[Offer], weights: Weights) -> list[ScoredOffer]:
    """Score offers and return them best first (out-of-stock offers always last)."""
    if not offers:
        return []
    w = weights.normalized()
    available = [o for o in offers if o.in_stock] or offers
    cheapest = min(o.total_price for o in available)

    scored = []
    for o in offers:
        p = price_score(o.total_price, cheapest)
        r = review_score(o.rating, o.review_count)
        d = delivery_score(o.delivery_days)
        t = trust_score(o.store_rating)
        total = 100 * (w.price * p + w.reviews * r + w.delivery * d + w.trust * t)
        scored.append(
            ScoredOffer(
                offer=o,
                score=round(total, 1),
                price_score=p,
                review_score=r,
                delivery_score=d,
                trust_score=t,
                adjusted_rating=(
                    adjusted_rating(o.rating, o.review_count)
                    if o.rating is not None and o.review_count > 0
                    else None
                ),
            )
        )

    scored.sort(key=lambda s: (not s.offer.in_stock, -s.score, s.offer.total_price))
    return _with_badges(scored)


def _with_badges(scored: list[ScoredOffer]) -> list[ScoredOffer]:
    in_stock = [s for s in scored if s.offer.in_stock]
    cheapest = min((s.offer.total_price for s in in_stock), default=None)
    best_rating = max((s.adjusted_rating for s in in_stock if s.adjusted_rating), default=None)
    fastest = min(
        (s.offer.delivery_days for s in in_stock if s.offer.delivery_days is not None),
        default=None,
    )
    result = []
    for i, s in enumerate(scored):
        o = s.offer
        badges = []
        if not o.in_stock:
            badges.append(BADGE_OUT_OF_STOCK)
        else:
            if i == 0:
                badges.append(BADGE_RECOMMENDED)
            if o.total_price == cheapest:
                badges.append(BADGE_CHEAPEST)
            if best_rating is not None and s.adjusted_rating == best_rating:
                badges.append(BADGE_TOP_RATED)
            if fastest is not None and o.delivery_days == fastest and len(in_stock) > 1:
                badges.append(BADGE_FASTEST)
        result.append(replace(s, badges=tuple(badges)))
    return result


def _rating_text(o: Offer) -> str:
    if o.rating is None or o.review_count <= 0:
        return "no customer reviews"
    return f"{o.rating:.1f} stars from {format_count(o.review_count)} reviews"


def _tradeoff(best: ScoredOffer, cheapest: ScoredOffer) -> str | None:
    """Why the recommended store beat the cheapest one."""
    c = cheapest.offer
    why = []
    if best.review_score - cheapest.review_score > 0.02:
        why.append(f"weaker reviews ({_rating_text(c)})")
    if best.delivery_score - cheapest.delivery_score > 0.05 and c.delivery_days is not None:
        why.append(f"slower delivery ({c.delivery_days} days)")
    if best.trust_score - cheapest.trust_score > 0.05 and c.store_rating is not None:
        why.append(f"a lower store rating ({c.store_rating:.1f}/5)")
    if not why:
        return None
    listed = ", ".join(why[:-1]) + " and " + why[-1] if len(why) > 1 else why[0]
    return f"{c.store} is cheaper but has {listed}."


def explain(ranked: list[ScoredOffer]) -> list[str]:
    """Plain-language reasons why the top offer was recommended."""
    in_stock = [s for s in ranked if s.offer.in_stock]
    if not in_stock:
        return ["No store has this product in stock right now."]
    best = in_stock[0]
    o = best.offer
    cur = o.currency
    reasons = []

    if len(in_stock) == 1:
        reasons.append(f"Only {o.store} has this product in stock.")
    else:
        cheapest = min(in_stock, key=lambda s: s.offer.total_price)
        if cheapest is best:
            next_price = min(s.offer.total_price for s in in_stock[1:])
            reasons.append(
                f"Lowest price at {format_money(o.total_price, cur)}, "
                f"{format_money(next_price - o.total_price, cur)} less than the next cheapest store."
            )
        else:
            extra = o.total_price - cheapest.offer.total_price
            reasons.append(
                f"Only {format_money(extra, cur)} more than the cheapest store "
                f"({cheapest.offer.store}, {format_money(cheapest.offer.total_price, cur)})."
            )
            # If the cheapest store lost, say why: that is the trade-off buyers care about.
            if tradeoff := _tradeoff(best, cheapest):
                reasons.append(tradeoff)
        saving = round(mean(s.offer.total_price for s in in_stock) - o.total_price)
        if saving > 0:
            reasons.append(
                f"{format_money(saving, cur)} below the average price across {len(in_stock)} stores."
            )

    if o.rating is not None and o.review_count > 0:
        reasons.append(f"Customers rate it {_rating_text(o)}.")
    else:
        reasons.append("No customer reviews on this store yet, so check the listing before buying.")

    if o.delivery_days is not None:
        reasons.append(
            "Delivery by tomorrow." if o.delivery_days <= 1 else f"Delivery in {o.delivery_days} days."
        )
    if o.shipping > 0:
        reasons.append(f"Price includes {format_money(o.shipping, cur)} shipping.")
    if o.store_rating is not None:
        reasons.append(f"Store rating {o.store_rating:.1f}/5.")
    return reasons
