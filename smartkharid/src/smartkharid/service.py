"""Fetch offers from all sources and turn them into a recommendation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from .matching import filter_matching
from .models import Comparison, Offer, Weights
from .scoring import explain, score_offers
from .sources import Source


@dataclass
class FetchResult:
    offers: list[Offer] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)  # source name -> message


async def fetch_offers(query: str, sources: list[Source], timeout: float = 30.0) -> FetchResult:
    """Ask every source in parallel. One failing source does not hide the others' results."""
    results = await asyncio.gather(
        *(asyncio.wait_for(s.search(query), timeout) for s in sources), return_exceptions=True
    )
    fetched = FetchResult()
    for source, result in zip(sources, results, strict=True):
        if isinstance(result, asyncio.TimeoutError):
            fetched.errors[source.name] = f"No answer within {timeout:.0f} seconds."
        elif isinstance(result, Exception):
            fetched.errors[source.name] = str(result) or type(result).__name__
        else:
            fetched.offers.extend(result)
    return fetched


def compare(
    query: str, offers: list[Offer], weights: Weights, errors: dict[str, str] | None = None
) -> Comparison:
    """Filter to the searched product, keep each store's best listing, rank stores.

    This is pure and fast, so the UI calls it again whenever the buyer moves a
    priority slider, without fetching prices again.
    """
    matched, dropped = filter_matching(query, offers)

    # A store can list the product several times (different sellers); keep its best one.
    best_per_store: dict[str, Offer] = {}
    for scored in score_offers(matched, weights):
        best_per_store.setdefault(scored.offer.store.casefold(), scored.offer)

    ranked = score_offers(list(best_per_store.values()), weights)
    recommended = ranked[0] if ranked and ranked[0].offer.in_stock else None
    return Comparison(
        query=query,
        ranked=ranked,
        recommended=recommended,
        reasons=explain(ranked) if ranked else [],
        errors=dict(errors or {}),
        filtered_out=dropped,
    )
