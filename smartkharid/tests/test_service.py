import asyncio

from smartkharid import PRESETS, Weights, compare, fetch_offers
from smartkharid.models import Offer
from smartkharid.sources import DemoSource


class FailingSource:
    name = "Broken"

    async def search(self, query):
        raise RuntimeError("store is down")


class SlowSource:
    name = "Slow"

    async def search(self, query):
        await asyncio.sleep(5)
        return []


async def test_demo_iphone_end_to_end():
    fetched = await fetch_offers("iPhone 15 128GB", [DemoSource(latency=0)])
    c = compare("iPhone 15 128GB", fetched.offers, Weights())
    stores = [s.offer.store for s in c.ranked]
    assert len(stores) == len(set(stores)), "one row per store"
    assert c.filtered_out == 3  # the case, the Plus model and the 256GB variant
    assert c.recommended.offer.store == "Flipkart"
    assert c.ranked[-1].offer.store == "JioMart"  # out of stock goes last
    assert c.reasons


async def test_priorities_change_the_recommendation():
    fetched = await fetch_offers("iPhone 15 128GB", [DemoSource(latency=0)])
    fast = compare("iPhone 15 128GB", fetched.offers, PRESETS["Fast delivery"])
    assert fast.recommended.offer.store == "Croma"


async def test_every_demo_suggestion_finds_a_recommendation():
    from smartkharid.sources.demo import SUGGESTIONS

    for query in SUGGESTIONS:
        fetched = await fetch_offers(query, [DemoSource(latency=0)])
        c = compare(query, fetched.offers, Weights())
        assert c.recommended is not None, query
        assert len(c.ranked) >= 4, query


async def test_one_failing_source_does_not_hide_others():
    fetched = await fetch_offers("Sony WH-1000XM5", [FailingSource(), DemoSource(latency=0)])
    assert fetched.errors == {"Broken": "store is down"}
    assert fetched.offers


async def test_slow_source_times_out():
    fetched = await fetch_offers("x", [SlowSource()], timeout=0.05)
    assert "Slow" in fetched.errors


def test_keeps_best_listing_per_store():
    offers = [
        Offer("Amazon", "Widget 5000", 1000, "u1", rating=2.0, review_count=500),
        Offer("Amazon", "Widget 5000", 1010, "u2", rating=4.8, review_count=5000),
        Offer("Flipkart", "Widget 5000", 1050, "u3", rating=4.5, review_count=900),
    ]
    c = compare("widget 5000", offers, Weights())
    amazon = [s for s in c.ranked if s.offer.store == "Amazon"]
    assert len(amazon) == 1 and amazon[0].offer.url == "u2"


def test_no_offers():
    c = compare("anything", [], Weights(), {"Google Shopping": "quota exceeded"})
    assert c.ranked == [] and c.recommended is None
    assert c.errors == {"Google Shopping": "quota exceeded"}
