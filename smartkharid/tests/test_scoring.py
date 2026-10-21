import pytest

from smartkharid.formatting import format_money
from smartkharid.models import Offer, Weights
from smartkharid.scoring import (
    BADGE_CHEAPEST,
    BADGE_FASTEST,
    BADGE_OUT_OF_STOCK,
    BADGE_RECOMMENDED,
    BADGE_TOP_RATED,
    adjusted_rating,
    delivery_score,
    explain,
    price_score,
    score_offers,
)


def offer(store, price, rating=None, reviews=0, days=None, in_stock=True, shipping=0.0, store_rating=None):
    return Offer(
        store=store,
        title="Thing",
        price=price,
        url="https://example.com",
        rating=rating,
        review_count=reviews,
        delivery_days=days,
        in_stock=in_stock,
        shipping=shipping,
        store_rating=store_rating,
    )


def test_format_money_uses_indian_grouping():
    assert format_money(123456) == "₹1,23,456"
    assert format_money(59999) == "₹59,999"
    assert format_money(999) == "₹999"
    assert format_money(12345678.5) == "₹1,23,45,678.50"
    assert format_money(1234.5, "USD") == "$1,234.50"


def test_weights_normalize():
    w = Weights(2, 1, 1, 0).normalized()
    assert (w.price, w.reviews, w.delivery, w.trust) == (0.5, 0.25, 0.25, 0.0)
    assert Weights(0, 0, 0, 0).normalized().price == 0.25


def test_few_reviews_count_for_less():
    assert adjusted_rating(5.0, 3) < adjusted_rating(4.4, 10_000)
    assert adjusted_rating(None, 0) == adjusted_rating(4.9, 0)


def test_price_and_delivery_scores():
    assert price_score(100, 100) == 1.0
    assert price_score(110, 100) == pytest.approx(0.7)
    assert price_score(200, 100) == 0.0
    assert delivery_score(1) == 1.0
    assert delivery_score(0) == 1.0
    assert delivery_score(None) == 0.5
    assert delivery_score(30) == 0.0


def test_shipping_counts_towards_price():
    ranked = score_offers(
        [offer("A", 1000, shipping=150), offer("B", 1100)], Weights(price=1, reviews=0, delivery=0, trust=0)
    )
    assert ranked[0].offer.store == "B"
    assert BADGE_CHEAPEST in ranked[0].badges


def test_slightly_dearer_store_with_far_better_reviews_wins():
    cheap_unknown = offer("CheapCo", 60_000, rating=4.0, reviews=12, days=6)
    trusted = offer("BigStore", 60_400, rating=4.6, reviews=120_000, days=2)
    ranked = score_offers([cheap_unknown, trusted], Weights())
    assert ranked[0].offer.store == "BigStore"
    assert BADGE_RECOMMENDED in ranked[0].badges
    assert BADGE_TOP_RATED in ranked[0].badges
    assert BADGE_FASTEST in ranked[0].badges
    assert BADGE_CHEAPEST in ranked[1].badges


def test_price_only_priority_picks_cheapest():
    ranked = score_offers(
        [offer("CheapCo", 60_000, 4.0, 12), offer("BigStore", 60_400, 4.6, 120_000)],
        Weights(price=1, reviews=0, delivery=0, trust=0),
    )
    assert ranked[0].offer.store == "CheapCo"


def test_out_of_stock_never_recommended():
    ranked = score_offers(
        [offer("Gone", 10, 5.0, 10_000, in_stock=False), offer("Here", 1000, 3.0, 5)], Weights()
    )
    assert [s.offer.store for s in ranked] == ["Here", "Gone"]
    assert ranked[1].badges == (BADGE_OUT_OF_STOCK,)
    assert BADGE_RECOMMENDED in ranked[0].badges
    # The out-of-stock price does not make in-stock offers look expensive.
    assert ranked[0].price_score == 1.0


def test_explain_mentions_tradeoff_with_cheapest():
    ranked = score_offers(
        [
            offer("CheapCo", 60_000, rating=4.0, reviews=12, days=6),
            offer("BigStore", 60_400, rating=4.6, reviews=120_000, days=2),
        ],
        Weights(),
    )
    reasons = explain(ranked)
    assert reasons[0] == "Only ₹400 more than the cheapest store (CheapCo, ₹60,000)."
    assert "CheapCo is cheaper but has weaker reviews (4.0 stars from 12 reviews)" in reasons[1]
    assert "slower delivery (6 days)" in reasons[1]


def test_explain_when_recommended_is_cheapest():
    ranked = score_offers([offer("A", 900, 4.5, 500), offer("B", 1000, 4.5, 500)], Weights())
    reasons = explain(ranked)
    assert reasons[0] == "Lowest price at ₹900, ₹100 less than the next cheapest store."
    assert "₹50 below the average price across 2 stores." in reasons


def test_explain_nothing_in_stock():
    ranked = score_offers([offer("A", 900, in_stock=False)], Weights())
    assert explain(ranked) == ["No store has this product in stock right now."]
