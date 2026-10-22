"""Live prices from Google Shopping, through the SerpApi service (https://serpapi.com).

Google Shopping already aggregates listings from Amazon, Flipkart, Croma, Reliance
Digital, Tata CLiQ and hundreds of other stores, with price, rating and review count.
Using an API for this is far more reliable (and allowed) compared with scraping each store,
whose pages change often and whose terms usually forbid scraping.

Full product details (photos, description, specifications, reviews) come from SerpApi's
Google Immersive Product engine, using the `immersive_product_page_token` of the chosen
listing. That costs one more search, so it can be switched off in Settings. Its response
layout is only partly documented, so `parse_product_results` accepts several shapes and the
app falls back to details taken from the listings when it gets nothing usable.

You need your own SerpApi key (the free plan includes a small monthly quota).
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date

import httpx

from ..details import basic_details, merge
from ..models import Offer, ProductDetails, Review, SpecSection
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
_NO_RESULTS = re.compile(r"(hasn't|didn't) return(ed)? any results")
# Listing "extensions" that describe the offer rather than the product.
_OFFER_NOISE = re.compile(
    r"deliver|shipping|stock|return|% off|\bsale\b|discount|emi|cashback", re.IGNORECASE
)
SOURCE_TAG = "serpapi"


class SerpApiShoppingSource:
    name = "Google Shopping"

    def __init__(
        self,
        api_key: str,
        country: str = "in",
        language: str = "en",
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
        full_details: bool = True,
    ):
        self.api_key = api_key.strip()
        self.country = country.lower()
        self.language = language
        self.timeout = timeout
        self.full_details = full_details  # one extra SerpApi search per product
        self._transport = transport  # injectable for tests

    async def _get(self, params: dict) -> dict | None:
        """Call SerpApi. Returns None when Google found nothing; raises SourceError on failure."""
        if not self.api_key:
            raise SourceError("SerpApi key missing — add it in Settings.")
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                resp = await client.get(ENDPOINT, params={**params, "api_key": self.api_key})
        except httpx.HTTPError as e:
            raise SourceError(f"Could not reach SerpApi: {e}") from e

        try:
            data = resp.json()
        except ValueError:
            raise SourceError(f"Unexpected reply from SerpApi (HTTP {resp.status_code}).") from None
        if isinstance(data, dict) and data.get("error"):
            if _NO_RESULTS.search(data["error"]):
                return None
            raise SourceError(data["error"])
        if resp.status_code >= 400 or not isinstance(data, dict):
            raise SourceError(f"SerpApi request failed (HTTP {resp.status_code}).")
        return data

    async def search(self, query: str) -> list[Offer]:
        domain, currency = COUNTRIES.get(self.country, ("google.com", "USD"))
        data = await self._get(
            {
                "engine": "google_shopping",
                "q": query,
                "gl": self.country,
                "hl": self.language,
                "google_domain": domain,
            }
        )
        items = (data or {}).get("shopping_results") or []
        offers = (parse_item(item, currency) for item in items)
        return [o for o in offers if o is not None]

    async def details(self, query: str, offers: list[Offer]) -> ProductDetails | None:
        """Details of the product behind `offers` (ranked best first)."""
        mine = [o for o in offers if o.source == SOURCE_TAG]
        basic = basic_details(mine, self.name)
        if basic is None:
            return None
        token = next((o.details_token for o in mine if o.details_token), None)
        if not self.full_details:
            return replace(basic, note="Turn on “Full product details” in Settings for specs and reviews.")
        if not token:
            return basic
        try:
            data = await self._get({"engine": "google_immersive_product", "page_token": token})
        except SourceError as e:
            return replace(basic, note=f"Full details unavailable: {e}")
        full = parse_product_results((data or {}).get("product_results"), self.name)
        if full is None:
            return replace(basic, note="Google has no extra details for this product.")
        return merge(full, basic)


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
    highlights = tuple(
        x for x in (_text(e) for e in item.get("extensions") or []) if x and not _OFFER_NOISE.search(x)
    )
    image = item.get("thumbnail") or next(iter(_images(item.get("thumbnails"))), None)

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
        source=SOURCE_TAG,
        image_url=image,
        highlights=highlights,
        details_token=item.get("immersive_product_page_token") or None,
    )


def _to_float(value) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return parse_price(value) if isinstance(value, str) else None


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


# ---------- product details (google_immersive_product) ----------


def _text(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list) and all(isinstance(v, (str, int, float)) for v in value):
        return ", ".join(_text(v) for v in value if _text(v))
    return ""


def _pick(d: dict, *keys: str):
    for key in keys:
        if isinstance(d, dict) and d.get(key):
            return d[key]
    return None


def _images(value) -> list[str]:
    if isinstance(value, (str, dict)):
        value = [value]
    out = []
    for v in value or []:
        url = v if isinstance(v, str) else _pick(v, "image", "original", "link", "url", "thumbnail")
        if isinstance(url, str) and url.startswith("http") and url not in out:
            out.append(url)
    return out


def _name_value(item) -> tuple[str, str] | None:
    if isinstance(item, dict):
        name = _text(_pick(item, "title", "name", "key", "label"))
        value = _text(_pick(item, "value", "text", "description", "snippet", "values"))
        if name and value:
            return name, value
    return None


def _rows(value) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        return [(str(k), _text(v)) for k, v in value.items() if _text(v)]
    if isinstance(value, list):
        return [r for r in (_name_value(i) for i in value) if r]
    return []


def _specs(value) -> tuple[SpecSection, ...]:
    """Accepts {name: value}, {section: {name: value}}, [{title, value}] or [{title, items}]."""
    sections = []
    if isinstance(value, dict):
        nested = {k: v for k, v in value.items() if isinstance(v, (dict, list)) and _rows(v)}
        flat = _rows({k: v for k, v in value.items() if k not in nested})
        if flat:
            sections.append(SpecSection("", tuple(flat)))
        sections += [SpecSection(str(k), tuple(_rows(v))) for k, v in nested.items()]
    elif isinstance(value, list):
        flat = []
        for item in value:
            inner = _pick(item, "items", "specs", "specifications", "rows", "values", "list")
            if isinstance(item, dict) and isinstance(inner, (list, dict)) and _rows(inner):
                sections.append(SpecSection(_text(_pick(item, "title", "name")), tuple(_rows(inner))))
            elif row := _name_value(item):
                flat.append(row)
        if flat:
            sections.insert(0, SpecSection("", tuple(flat)))
    return tuple(s for s in sections if s.rows)


def _highlights(value) -> list[str]:
    out = []
    for item in value if isinstance(value, list) else []:
        if text := _text(item):
            out.append(text)
        elif row := _name_value(item):
            out.append(f"{row[0]}: {row[1]}")
    return out


def _reviews(value) -> tuple[Review, ...]:
    out = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        text = _text(_pick(item, "text", "snippet", "content", "review", "description"))
        if not text:
            continue
        user = item.get("user")
        author = _text(user.get("name") if isinstance(user, dict) else user) or _text(
            _pick(item, "user_name", "author", "name")
        )
        out.append(
            Review(
                text=text,
                rating=_to_float(_pick(item, "rating", "stars")),
                title=_text(item.get("title")),
                author=author,
                date=_text(item.get("date")),
                source=_text(_pick(item, "source", "store")),
            )
        )
    return tuple(out)


def _breakdown(value) -> tuple[tuple[int, int], ...]:
    rows = []
    for item in value if isinstance(value, list) else []:
        stars = _to_int(_pick(item, "stars", "star")) if isinstance(item, dict) else None
        amount = _to_int(_pick(item, "amount", "count", "total")) if isinstance(item, dict) else None
        if stars and 1 <= stars <= 5 and amount is not None:
            rows.append((stars, amount))
    return tuple(sorted(rows, reverse=True))


def parse_product_results(pr, source: str = "") -> ProductDetails | None:
    """Convert a google_immersive_product `product_results` object (None if unusable)."""
    if not isinstance(pr, dict):
        return None
    title = _text(pr.get("title"))
    if not title:
        return None  # SerpApi has been seen to return malformed objects like {"title": {"108": 1}}
    about = pr.get("about_the_product")
    about = about if isinstance(about, dict) else {"description": about}
    reviews_results = pr.get("reviews_results") if isinstance(pr.get("reviews_results"), dict) else {}

    highlights = _highlights(_pick(pr, "highlights") or _pick(about, "highlights"))
    specs = _specs(
        _pick(pr, "specifications", "specs", "specs_results", "tech_specs")
        or _pick(about, "specifications", "specs")
    )
    # "features" are either plain sentences (-> highlights) or name/value pairs (-> specs).
    features = _pick(pr, "features") or _pick(about, "features")
    if isinstance(features, list):
        highlights += [_text(f) for f in features if isinstance(f, str) and _text(f)]
    if feature_rows := _rows(features):
        specs = (SpecSection("Key features", tuple(feature_rows)), *specs)

    user_reviews = _pick(pr, "user_reviews", "top_reviews") or _pick(reviews_results, "reviews")
    if isinstance(pr.get("reviews"), list):
        user_reviews = user_reviews or pr["reviews"]

    return ProductDetails(
        title=title,
        brand=_text(pr.get("brand")),
        description=_text(_pick(pr, "description", "product_description")) or _text(about.get("description")),
        images=tuple(_images(_pick(pr, "thumbnails", "images", "media")))[:8],
        highlights=tuple(dict.fromkeys(highlights))[:8],
        specs=specs,
        rating=_to_float(pr.get("rating")),
        review_count=(_to_int(pr.get("reviews")) or 0) if not isinstance(pr.get("reviews"), list) else 0,
        rating_breakdown=_breakdown(_pick(pr, "ratings") or _pick(reviews_results, "ratings")),
        reviews=_reviews(user_reviews)[:10],
        price_range=_text(pr.get("price_range")),
        source=source,
    )
