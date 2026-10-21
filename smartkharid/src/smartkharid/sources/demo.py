"""Offline sample catalog so the app works without an API key or internet.

The prices, ratings and review counts below are illustrative sample data, not live
store prices. Switch to a live source in Settings for real prices. Each product also
has a few "noise" listings (covers, other variants) like a real store search returns,
so the matching filter has something to do.
"""

from __future__ import annotations

import asyncio

from ..matching import relevance
from ..models import Offer
from .base import store_search_url

# (store, title, price, shipping, rating, reviews, delivery_days, store_rating, in_stock)
_Row = tuple[str, str, float, float, float | None, int, int | None, float | None, bool]

# fmt: off
CATALOG: dict[str, list[_Row]] = {
    "iPhone 15 128GB": [
        ("Amazon", "Apple iPhone 15 (128 GB) - Black", 61499, 0, 4.5, 8421, 2, 4.4, True),
        ("Flipkart", "Apple iPhone 15 (Black, 128 GB)", 60999, 0, 4.6, 125310, 3, 4.3, True),
        ("Croma", "Apple iPhone 15 (128GB, Black)", 62490, 0, 4.4, 512, 1, 4.2, True),
        ("Reliance Digital", "Apple iPhone 15 128 GB, Black", 61990, 0, 4.3, 214, 2, 4.1, True),
        ("Vijay Sales", "Apple iPhone 15 128GB Black", 60490, 99, 4.0, 38, 5, 3.9, True),
        ("JioMart", "Apple iPhone 15 128 GB Black", 59990, 0, 4.2, 96, 4, 3.8, False),
        ("Amazon", "Spigen Liquid Air Case for iPhone 15 - Matte Black", 1299, 0, 4.4, 3120, 2, 4.4, True),
        ("Flipkart", "Apple iPhone 15 Plus (Black, 128 GB)", 69999, 0, 4.6, 40211, 3, 4.3, True),
        ("Croma", "Apple iPhone 15 (256GB, Black)", 71990, 0, 4.4, 133, 1, 4.2, True),
    ],
    "Samsung Galaxy S24 256GB": [
        ("Amazon", "Samsung Galaxy S24 5G AI Smartphone (Onyx Black, 8GB, 256GB Storage)", 64999, 0, 4.3, 3212, 2, 4.4, True),
        ("Flipkart", "SAMSUNG Galaxy S24 5G (Onyx Black, 256 GB) (8 GB RAM)", 59999, 0, 4.4, 18765, 4, 4.3, True),
        ("Croma", "Samsung Galaxy S24 5G (8GB RAM, 256GB, Onyx Black)", 62999, 0, 4.2, 301, 1, 4.2, True),
        ("Reliance Digital", "Samsung Galaxy S24 5G 256 GB, 8 GB RAM, Onyx Black", 63499, 0, 4.1, 120, 2, 4.1, True),
        ("Tata CLiQ", "Samsung Galaxy S24 5G (8GB RAM, 256GB, Onyx Black)", 61490, 0, 3.9, 44, 6, 4.0, True),
        ("Amazon", "Samsung Galaxy S24 Ultra 5G (Titanium Gray, 12GB, 256GB)", 109999, 0, 4.4, 5120, 2, 4.4, True),
        ("Flipkart", "Tempered Glass Screen Protector for Samsung Galaxy S24 256GB", 349, 40, 4.0, 2210, 5, 4.3, True),
    ],
    "Sony WH-1000XM5": [
        ("Amazon", "Sony WH-1000XM5 Wireless Noise Cancelling Headphones, 30Hrs Battery, Black", 26990, 0, 4.4, 9874, 1, 4.4, True),
        ("Flipkart", "SONY WH-1000XM5 Bluetooth Headset (Black, On the Ear)", 27489, 0, 4.5, 6105, 3, 4.3, True),
        ("Croma", "SONY WH-1000XM5 Bluetooth Headphone with Mic (30 Hours Playback, Black)", 29990, 0, 4.3, 412, 2, 4.2, True),
        ("Reliance Digital", "Sony WH-1000XM5 Wireless Noise Cancelling Headphones, Black", 25990, 0, 3.6, 21, 6, 3.8, True),
        ("Tata CLiQ", "Sony WH-1000XM5 Wireless Headphones (Black)", 28490, 0, 4.2, 88, 4, 4.0, True),
        ("Vijay Sales", "Sony WH-1000XM5 Headphones Black", 26490, 0, None, 0, 5, 3.9, True),
        ("Amazon", "Replacement Ear Pads Cushions for Sony WH-1000XM5", 899, 0, 4.1, 760, 2, 4.4, True),
    ],
    "boAt Airdopes 141": [
        ("Amazon", "boAt Airdopes 141 TWS Earbuds with 42H Playtime, Low Latency Mode, ENx Tech (Bold Black)", 1099, 0, 4.0, 412560, 2, 4.4, True),
        ("Flipkart", "boAt Airdopes 141 with 42 Hours Playback, ENx Technology Bluetooth Headset (Bold Black, True Wireless)", 999, 0, 3.9, 298114, 4, 4.3, True),
        ("JioMart", "boAt Airdopes 141 True Wireless Earbuds Bold Black", 1199, 0, 3.8, 1240, 3, 3.8, True),
        ("Croma", "boAt Airdopes 141 TWS Earbuds (Bold Black)", 1299, 0, 4.1, 230, 1, 4.2, True),
        ("Myntra", "boAt Airdopes 141 Bold Black TWS Earbuds", 1149, 79, 4.2, 3412, 5, 4.1, True),
        ("Amazon", "Silicone Case Cover for boAt Airdopes 141", 249, 0, 3.9, 1830, 2, 4.4, True),
        ("Flipkart", "boAt Airdopes 141 Pro Bluetooth Headset (Black)", 1499, 0, 4.0, 12044, 4, 4.3, True),
    ],
    "Nike Revolution 7": [
        ("Myntra", "Nike Men Revolution 7 Running Shoes", 2996, 0, 4.3, 1820, 4, 4.3, True),
        ("Ajio", "NIKE Revolution 7 Lace-Up Running Shoes", 3196, 0, 4.1, 312, 5, 4.1, True),
        ("Amazon", "Nike Mens Revolution 7 Running Shoe", 3295, 0, 4.2, 642, 2, 4.4, True),
        ("Flipkart", "NIKE Revolution 7 Running Shoes For Men (Black)", 3095, 0, 4.0, 1105, 4, 4.3, True),
        ("Tata CLiQ", "Nike Revolution 7 Men's Running Shoes", 2846, 0, 4.2, 230, 4, 4.0, False),
    ],
    "Prestige Iris 750W mixer grinder": [
        ("Amazon", "Prestige Iris 750 Watt Mixer Grinder with 3 Stainless Steel Jars and 1 Juicer Jar (White and Blue)", 3199, 0, 4.1, 58204, 2, 4.4, True),
        ("Flipkart", "Prestige IRIS 750 W Mixer Grinder (4 Jars, White, Blue)", 2999, 0, 4.2, 41876, 5, 4.3, True),
        ("JioMart", "Prestige Iris 750 W Mixer Grinder 4 Jars", 2899, 49, 4.0, 2106, 4, 3.8, True),
        ("Reliance Digital", "Prestige Iris 750W Mixer Grinder, 4 Jars", 3349, 0, 3.9, 166, 3, 4.1, True),
        ("Amazon", "Prestige Iris Plus 750 Watt Mixer Grinder", 3799, 0, 4.1, 21330, 2, 4.4, True),
    ],
}
# fmt: on

SUGGESTIONS = list(CATALOG)

MIN_SEARCH_RELEVANCE = 0.5


class DemoSource:
    name = "Demo catalog"

    def __init__(self, latency: float = 0.4):
        self.latency = latency  # pretend to be a network call so the UI shows progress

    async def search(self, query: str) -> list[Offer]:
        if self.latency:
            await asyncio.sleep(self.latency)
        return [
            Offer(
                store=store,
                title=title,
                price=price,
                shipping=shipping,
                rating=rating,
                review_count=reviews,
                delivery_days=days,
                store_rating=store_rating,
                in_stock=in_stock,
                url=store_search_url(store, product),
                source="demo",
            )
            for product, rows in CATALOG.items()
            for store, title, price, shipping, rating, reviews, days, store_rating, in_stock in rows
            if relevance(query, title) >= MIN_SEARCH_RELEVANCE
        ]
