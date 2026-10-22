import httpx
import pytest

from smartkharid import Weights, compare, fetch_details, fetch_offers
from smartkharid.details import basic_details, merge
from smartkharid.models import Offer, ProductDetails
from smartkharid.sources import DemoSource, SerpApiShoppingSource
from smartkharid.sources.demo import SUGGESTIONS
from smartkharid.sources.serpapi import parse_item, parse_product_results


def offer(store, price, rating=None, reviews=0, image=None, highlights=(), in_stock=True):
    return Offer(
        store=store,
        title=f"Phone X ({store})",
        price=price,
        url="u",
        rating=rating,
        review_count=reviews,
        image_url=image,
        highlights=highlights,
        in_stock=in_stock,
    )


def test_basic_details_from_listings():
    d = basic_details(
        [
            offer("A", 1000, 4.1, 50, "https://img/1", ("128 GB", "5G")),
            offer("B", 1200, 4.6, 9000, "https://img/1", ("5g", "OLED")),
            offer("C", 900, in_stock=False),
        ],
        source="Test",
    )
    assert d.title == "Phone X (A)"
    assert d.images == ("https://img/1",)
    assert d.highlights == ("128 GB", "5G", "OLED")  # de-duplicated, case-insensitive
    assert (d.rating, d.review_count) == (4.6, 9000)  # listing with most reviews, not a sum
    assert d.price_range == "₹1,000 – ₹1,200"  # out-of-stock price left out
    assert basic_details([], "Test") is None


def test_merge_fills_only_empty_fields():
    full = ProductDetails(title="Full", description="Long text", source="Google Shopping")
    basic = ProductDetails(title="Basic", images=("https://img/1",), rating=4.2, review_count=10, source="x")
    merged = merge(full, basic)
    assert merged.title == "Full" and merged.description == "Long text"
    assert merged.images == ("https://img/1",) and merged.rating == 4.2
    assert merged.source == "Google Shopping"


PRODUCT_RESULTS = {
    "title": "Apple iPhone 15 128GB",
    "brand": "Apple",
    "rating": 4.6,
    "reviews": 12345,
    "price_range": "₹59,900 – ₹69,900",
    "thumbnails": ["https://img/a.jpg", "https://img/b.jpg", "https://img/a.jpg"],
    "about_the_product": {
        "description": "The latest iPhone.",
        "features": [{"title": "Display", "value": "6.1 inch"}, "Dynamic Island"],
    },
    "specifications": [
        {
            "title": "Camera",
            "items": [{"name": "Main", "value": "48 MP"}, {"name": "Front", "value": "12 MP"}],
        },
        {"title": "Weight", "value": "171 g"},
    ],
    "ratings": [{"stars": 4, "amount": 200}, {"stars": 5, "amount": 900}, {"stars": 9, "amount": 1}],
    "user_reviews": [
        {"title": "Great", "text": "Love it", "rating": 5, "user": {"name": "Asha"}, "date": "2 weeks ago"},
        {"title": "No text"},
    ],
    "stores": [{"name": "Amazon.in", "price": "₹61,499"}],
}


def test_parse_product_results():
    d = parse_product_results(PRODUCT_RESULTS, "Google Shopping")
    assert d.title == "Apple iPhone 15 128GB" and d.brand == "Apple"
    assert d.images == ("https://img/a.jpg", "https://img/b.jpg")
    assert d.description == "The latest iPhone."
    assert "Dynamic Island" in d.highlights
    assert d.specs[0].title == "Key features" and d.specs[0].rows == (("Display", "6.1 inch"),)
    sections = {s.title: s.rows for s in d.specs}
    assert sections["Camera"] == (("Main", "48 MP"), ("Front", "12 MP"))
    assert sections[""] == (("Weight", "171 g"),)
    assert (d.rating, d.review_count) == (4.6, 12345)
    assert d.rating_breakdown == ((5, 900), (4, 200))  # sorted, invalid star value dropped
    assert len(d.reviews) == 1 and d.reviews[0].author == "Asha" and d.reviews[0].rating == 5
    assert d.price_range == "₹59,900 – ₹69,900"


def test_parse_product_results_alternative_shapes():
    d = parse_product_results(
        {
            "title": "Sony WH-1000XM5",
            "description": "Noise cancelling headphones.",
            "images": [{"link": "https://img/1.jpg"}, {"thumbnail": "https://img/2.jpg"}, {"x": 1}],
            "highlights": ["30 hour battery", ""],
            "features": ["Multipoint"],
            "specs": {"Weight": "250 g", "Audio": {"Driver": "30 mm", "Codecs": ["SBC", "AAC", "LDAC"]}},
            "reviews_results": {
                "ratings": [{"stars": 5, "count": "1,200"}],
                "reviews": [{"snippet": "Superb ANC", "author": "Ravi", "source": "Flipkart"}],
            },
        }
    )
    assert d.images == ("https://img/1.jpg", "https://img/2.jpg")
    assert d.description == "Noise cancelling headphones."
    assert d.highlights == ("30 hour battery", "Multipoint")
    sections = {s.title: s.rows for s in d.specs}
    assert sections[""] == (("Weight", "250 g"),)
    assert sections["Audio"] == (("Driver", "30 mm"), ("Codecs", "SBC, AAC, LDAC"))
    assert d.rating_breakdown == ((5, 1200),)
    assert d.reviews[0].text == "Superb ANC" and d.reviews[0].source == "Flipkart"


@pytest.mark.parametrize(
    "bad",
    [None, "oops", [], {}, {"title": {"108": 1}}, {"title": ""}],
)
def test_parse_product_results_rejects_malformed(bad):
    # {"title": {"108": 1}} is a malformed response SerpApi has been reported to return.
    assert parse_product_results(bad) is None


def test_parse_product_results_ignores_non_scalar_numbers():
    d = parse_product_results({"title": "X", "rating": {"value": 4}, "reviews": {"n": 3}})
    assert d.rating is None and d.review_count == 0


SHOPPING_ITEM = {
    "title": "Apple iPhone 15 (128 GB) - Black",
    "source": "Amazon.in",
    "price": "₹61,499.00",
    "extracted_price": 61499.0,
    "rating": 4.5,
    "reviews": 8421,
    "thumbnail": "https://img/listing.jpg",
    "extensions": ["128 GB", "5G", "Free delivery", "10% off"],
    "immersive_product_page_token": "TOKEN123",
}


def test_parse_item_keeps_product_facts_and_token():
    o = parse_item(SHOPPING_ITEM)
    assert o.highlights == ("128 GB", "5G")
    assert o.details_token == "TOKEN123"
    assert o.image_url == "https://img/listing.jpg"


def _serpapi(handler, **kwargs) -> SerpApiShoppingSource:
    return SerpApiShoppingSource("key", transport=httpx.MockTransport(handler), **kwargs)


async def _details(source, query="iPhone 15 128GB"):
    fetched = await fetch_offers(query, [source])
    comparison = compare(query, fetched.offers, Weights())
    return await fetch_details(query, comparison, [source])


async def test_serpapi_full_details_use_page_token():
    calls = []

    def handler(request):
        params = dict(request.url.params)
        calls.append(params)
        if params["engine"] == "google_shopping":
            return httpx.Response(200, json={"shopping_results": [SHOPPING_ITEM]})
        return httpx.Response(200, json={"product_results": {**PRODUCT_RESULTS, "thumbnails": []}})

    details, error = await _details(_serpapi(handler))
    assert error is None
    assert [c["engine"] for c in calls] == ["google_shopping", "google_immersive_product"]
    assert calls[1]["page_token"] == "TOKEN123" and calls[1]["api_key"] == "key"
    assert details.brand == "Apple" and details.specs
    assert details.images == ("https://img/listing.jpg",)  # filled in from the listing
    assert details.source == "Google Shopping" and details.note == ""


@pytest.mark.parametrize(
    "reply, note",
    [
        (
            httpx.Response(401, json={"error": "Your account has run out of searches."}),
            "Full details unavailable",
        ),
        (
            httpx.Response(
                200, json={"error": "Google Immersive Product didn't return any results for this query."}
            ),
            "no extra details",
        ),
        (httpx.Response(200, json={"product_results": {"title": {"108": 1}}}), "no extra details"),
    ],
)
async def test_serpapi_details_fall_back_to_listing(reply, note):
    def handler(request):
        if request.url.params["engine"] == "google_shopping":
            return httpx.Response(200, json={"shopping_results": [SHOPPING_ITEM]})
        return reply

    details, error = await _details(_serpapi(handler))
    assert error is None
    assert details.title == SHOPPING_ITEM["title"] and details.highlights == ("128 GB", "5G")
    assert note in details.note


async def test_serpapi_full_details_switch_off_saves_a_search():
    engines = []

    def handler(request):
        engines.append(request.url.params["engine"])
        return httpx.Response(200, json={"shopping_results": [SHOPPING_ITEM]})

    details, _ = await _details(_serpapi(handler, full_details=False))
    assert engines == ["google_shopping"]
    assert "Settings" in details.note


async def test_demo_details_for_every_suggestion():
    for query in SUGGESTIONS:
        details, error = await _details(DemoSource(latency=0), query)
        assert error is None, query
        assert details.brand and details.description and details.highlights, query
        assert details.specs and details.reviews, query
        assert details.rating is not None and details.price_range, query
        stars = [s for s, _ in details.rating_breakdown]
        assert stars == [5, 4, 3, 2, 1], query
        assert abs(sum(n for _, n in details.rating_breakdown) - details.review_count) <= 3, query


class BrokenDetails:
    name = "Broken"

    async def search(self, query):
        return [Offer("Shop", "Widget 5000", 100, "u", source="broken")]

    async def details(self, query, offers):
        raise RuntimeError("boom")


class NoDetails:
    name = "Plain"

    async def search(self, query):
        return [Offer("Shop", "Widget 5000", 100, "u")]


async def test_fetch_details_errors_never_raise():
    details, error = await _details(BrokenDetails(), "widget 5000")
    assert details is None and error == "Broken: boom"
    assert await _details(NoDetails(), "widget 5000") == (None, None)
