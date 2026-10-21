"""Live prices from Google Shopping, through the SerpApi service (https://serpapi.com).

Google Shopping already aggregates listings from Amazon, Flipkart, Croma, Reliance
Digital, Tata CLiQ and hundreds of other stores, with price, rating and review count.
Using an API for this is far more reliable (and allowed) compared with scraping each store,
whose pages change often and whose terms usually forbid scraping.

You need your own SerpApi key (the free plan includes a small monthly quota).
"""

from __future__ import annotations

import re
from datetime import date

import httpx

from ..models import Offer
from .base import SourceError

ENDPOINT = "https://serpapi.com/search.json"

# country code -> (Google domain, currency used when the price text has no symbol)
COUNTRIES = {
    "in": ("google.co.in", "INR"),
    "us": ("google.com", "USD"),
    "gb": ("google.co.uk", "GBP"),
    "ae": ("google.ae", "AED"),
}
_SYMBOLS = {"₹": "INR", "rs": "INR", "$": "USD", "€": "EUR", "£": "GBP", "aed": "AED"}
_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_NO_RESULTS = "hasn't returned any results"


class SerpApiShoppingSource:
    name = "Google Shopping"

    def __init__(
        self,
        api_key: str,
        country: str = "in",
        language: str = "en",
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key = api_key.strip()
        self.country = country.lower()
        self.language = language
        self.timeout = timeout
        self._transport = transport  # injectable for tests

    async def search(self, query: str) -> list[Offer]:
        if not self.api_key:
            raise SourceError("SerpApi key missing — add it in Settings.")
        domain, currency = COUNTRIES.get(self.country, ("google.com", "USD"))
        params = {
            "engine": "google_shopping",
            "q": query,
            "gl": self.country,
            "hl": self.language,
            "google_domain": domain,
            "api_key": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                resp = await client.get(ENDPOINT, params=params)
        except httpx.HTTPError as e:
            raise SourceError(f"Could not reach SerpApi: {e}") from e

        try:
            data = resp.json()
        except ValueError:
            raise SourceError(f"Unexpected reply from SerpApi (HTTP {resp.status_code}).") from None
        if isinstance(data, dict) and data.get("error"):
            if _NO_RESULTS in data["error"]:
                return []
            raise SourceError(data["error"])
        if resp.status_code >= 400 or not isinstance(data, dict):
            raise SourceError(f"SerpApi request failed (HTTP {resp.status_code}).")

        items = data.get("shopping_results") or []
        offers = (parse_item(item, currency) for item in items)
        return [o for o in offers if o is not None]


def parse_item(item: dict, default_currency: str = "INR", today: date | None = None) -> Offer | None:
    """Convert one `shopping_results` entry into an Offer (None if it has no usable price)."""
    if item.get("second_hand_condition"):
        return None  # used / refurbished listings would unfairly undercut new ones
    price_text = str(item.get("price") or "")
    price = _to_float(item.get("extracted_price"))
    if price is None:
        price = parse_price(price_text)
    if not price:
        return None

    delivery_text = " ".join(
        [str(item.get("delivery") or "")] + [str(x) for x in item.get("extensions") or []]
    )
    shipping, days = parse_delivery(delivery_text, today)
    url = item.get("link") or item.get("product_link") or ""
    store = re.sub(r"\s*&\s*more$", "", str(item.get("source") or "Unknown store")).strip()

    return Offer(
        store=store,
        title=str(item.get("title") or ""),
        price=price,
        url=url,
        currency=currency_of(price_text) or default_currency,
        shipping=shipping,
        rating=_to_float(item.get("rating")),
        review_count=_to_int(item.get("reviews")) or 0,
        delivery_days=days,
        in_stock="out of stock" not in delivery_text.lower(),
        source="serpapi",
        image_url=item.get("thumbnail"),
    )


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return parse_price(str(value))


def _to_int(value) -> int | None:
    f = _to_float(value)
    return int(f) if f is not None else None


def parse_price(text: str) -> float | None:
    """'₹59,900.00' -> 59900.0; None if there is no number."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?", text)
    return float(m.group().replace(",", "")) if m else None


def currency_of(price_text: str) -> str | None:
    t = price_text.strip().lower()
    for symbol, code in _SYMBOLS.items():
        if t.startswith(symbol):
            return code
    return None


def parse_delivery(text: str, today: date | None = None) -> tuple[float, int | None]:
    """Extract (shipping cost, delivery days) from text like '₹40 delivery by Fri'."""
    t = text.lower()
    shipping = 0.0
    m = re.search(r"(?:₹|rs\.?|\$|€|£)\s*([\d,]+(?:\.\d+)?)\s*(?:delivery|shipping)", t)
    if m and "free" not in t:
        shipping = float(m.group(1).replace(",", ""))

    days: int | None = None
    if "today" in t or "same day" in t:
        days = 0
    elif "tomorrow" in t or "next day" in t or "next-day" in t:
        days = 1
    elif m := re.search(r"(\d+)(?:\s*(?:-|to)\s*(\d+))?\s*(?:business\s+)?days?", t):
        days = int(m.group(2) or m.group(1))
    elif m := re.search(r"\bby\s+(mon|tue|wed|thu|fri|sat|sun)", t):
        weekday = (today or date.today()).weekday()
        days = (_WEEKDAYS.index(m.group(1)) - weekday) % 7 or 7
    return shipping, days
