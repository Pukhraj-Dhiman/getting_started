from datetime import date

import httpx
import pytest

from smartkharid.sources import SerpApiShoppingSource, SourceError
from smartkharid.sources.serpapi import parse_delivery, parse_item

ITEM = {
    "position": 1,
    "title": "Apple iPhone 15 (128 GB) - Black",
    "product_link": "https://www.google.co.in/shopping/product/123",
    "source": "Amazon.in",
    "price": "₹61,499.00",
    "extracted_price": 61499.0,
    "rating": 4.5,
    "reviews": 8421,
    "delivery": "Free delivery by Fri",
    "thumbnail": "https://example.com/img.jpg",
}


def test_parse_item():
    o = parse_item(ITEM, today=date(2026, 10, 21))  # a Wednesday
    assert o.store == "Amazon.in"
    assert o.price == 61499.0
    assert o.currency == "INR"
    assert o.rating == 4.5 and o.review_count == 8421
    assert o.shipping == 0 and o.delivery_days == 2
    assert o.url == ITEM["product_link"]
    assert o.source == "serpapi"


def test_parse_item_prefers_direct_link_and_price_text_fallback():
    item = {
        **ITEM,
        "link": "https://www.amazon.in/dp/B0CHX1W1XY",
        "extracted_price": None,
        "source": "Croma & more",
        "reviews": "1,204",
    }
    o = parse_item(item)
    assert o.url == "https://www.amazon.in/dp/B0CHX1W1XY"
    assert o.price == 61499.0
    assert o.store == "Croma"
    assert o.review_count == 1204


def test_parse_item_skips_unusable_listings():
    assert parse_item({**ITEM, "extracted_price": None, "price": ""}) is None
    assert parse_item({**ITEM, "second_hand_condition": "refurbished"}) is None


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Free delivery", (0.0, None)),
        ("₹40 delivery", (40.0, None)),
        ("Delivery in 3-5 days", (0.0, 5)),
        ("Get it tomorrow", (0.0, 1)),
        ("Free delivery by Mon", (0.0, 5)),
        ("$5.99 shipping, arrives in 2 business days", (5.99, 2)),
    ],
)
def test_parse_delivery(text, expected):
    assert parse_delivery(text, today=date(2026, 10, 21)) == expected


def _source(handler) -> SerpApiShoppingSource:
    return SerpApiShoppingSource("test-key", transport=httpx.MockTransport(handler))


async def test_search_sends_india_params_and_parses_results():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.url.params)
        return httpx.Response(
            200, json={"shopping_results": [ITEM, {**ITEM, "price": None, "extracted_price": None}]}
        )

    offers = await _source(handler).search("iphone 15")
    assert len(offers) == 1
    assert seen["engine"] == "google_shopping"
    assert seen["q"] == "iphone 15"
    assert seen["gl"] == "in" and seen["google_domain"] == "google.co.in"
    assert seen["api_key"] == "test-key"


async def test_search_no_results_is_empty_not_error():
    def handler(request):
        return httpx.Response(200, json={"error": "Google hasn't returned any results for this query."})

    assert await _source(handler).search("zzzz") == []


async def test_search_api_error_raises():
    def handler(request):
        return httpx.Response(401, json={"error": "Invalid API key. Your API key should be here: ..."})

    with pytest.raises(SourceError, match="Invalid API key"):
        await _source(handler).search("iphone")


async def test_search_without_key_raises():
    with pytest.raises(SourceError, match="key missing"):
        await SerpApiShoppingSource("").search("iphone")


async def test_network_failure_raises_source_error():
    def handler(request):
        raise httpx.ConnectError("boom")

    with pytest.raises(SourceError, match="Could not reach SerpApi"):
        await _source(handler).search("iphone")
