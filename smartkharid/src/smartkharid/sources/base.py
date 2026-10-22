"""Interface every price data source implements."""

from __future__ import annotations

from typing import Protocol
from urllib.parse import quote_plus

from ..models import Offer


class SourceError(Exception):
    """A data source could not answer (bad API key, network error, quota, ...)."""


class Source(Protocol):
    name: str

    async def search(self, query: str) -> list[Offer]:
        """Return every listing the source finds for `query` (unfiltered)."""
        ...

    # Optional: sources may also provide
    #   async def details(self, query: str, offers: list[Offer]) -> ProductDetails | None
    # describing the product behind `offers` (ranked best first; only the source's own offers
    # are relevant to it). Return None when it has nothing to say about these offers.


# Search pages of popular Indian stores, used to send the buyer to the product.
_STORE_SEARCH = {
    "amazon": "https://www.amazon.in/s?k={q}",
    "flipkart": "https://www.flipkart.com/search?q={q}",
    "croma": "https://www.croma.com/searchB?q={q}%3Arelevance&text={q}",
    "tata cliq": "https://www.tatacliq.com/search/?searchCategory=all&text={q}",
    "jiomart": "https://www.jiomart.com/search/{q}",
    "ajio": "https://www.ajio.com/search/?text={q}",
}
_STORE_DOMAINS = {
    "reliance digital": "reliancedigital.in",
    "vijay sales": "vijaysales.com",
    "myntra": "myntra.com",
}


def store_search_url(store: str, query: str) -> str:
    """Best URL to find `query` on `store` (falls back to a site-restricted web search)."""
    key = store.lower()
    if key in _STORE_SEARCH:
        return _STORE_SEARCH[key].format(q=quote_plus(query))
    domain = _STORE_DOMAINS.get(key)
    site = f"site:{domain} " if domain else f"{store} "
    return "https://www.google.com/search?q=" + quote_plus(site + query)
