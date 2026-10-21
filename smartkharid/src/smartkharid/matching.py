"""Decide whether a store listing is the same product the user searched for.

Stores return lots of noise for a search: phone covers, screen guards, the 256 GB
variant when you asked for 128 GB, the "Pro" model, and so on. Comparing those
prices would be meaningless, so they are filtered out before ranking.
"""

from __future__ import annotations

import re
from statistics import median

from .models import Offer

# Units that are written with or without a space ("128 GB" vs "128GB", "750 Watt" vs "750W").
_NUM_UNIT_RE = re.compile(r"\b(\d+)\s*([a-z]+)\b")
_UNITS = {"gb", "tb", "mb", "mah", "w", "mp", "hz", "ml", "l", "kg", "g", "inch", "cm", "mm"}
_UNIT_ALIASES = {"watt": "w", "watts": "w", "inches": "inch", "litre": "l", "liter": "l", "litres": "l"}

# Words that turn "iPhone 15" into a different, pricier model.
VARIANT_WORDS = {"pro", "max", "plus", "ultra", "mini", "lite"}

# Words that indicate an accessory *for* the product rather than the product.
# fmt: off
ACCESSORY_WORDS = {
    "case", "cases", "cover", "covers", "tempered", "glass", "protector", "guard", "skin", "skins",
    "charger", "cable", "adapter", "strap", "stand", "holder", "pouch", "sticker", "film", "sleeve",
    "replacement", "earpads", "cushions",
}
# fmt: on
_ACCESSORY_LINKS = {"for", "compatible"}

MIN_RELEVANCE = 0.7
# A "match" priced below this fraction of the median is almost surely an accessory.
MIN_PRICE_RATIO = 0.35


def _join_unit(m: re.Match[str]) -> str:
    unit = _UNIT_ALIASES.get(m.group(2), m.group(2))
    return m.group(1) + unit if unit in _UNITS else m.group(0)


def normalize(text: str) -> str:
    text = text.lower().replace("-", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return _NUM_UNIT_RE.sub(_join_unit, text).strip()


def tokens(text: str) -> list[str]:
    return normalize(text).split()


def _token_in(tok: str, title_tokens: set[str], title_compact: str) -> bool:
    if tok in title_tokens:
        return True
    if tok.isdigit():
        # Plain numbers ("15", "141") must match a whole number, otherwise "15" would match
        # "150"; a number glued to a word ("iphone15", "airdopes141") is fine.
        return any(t.endswith(tok) and t[: -len(tok)].isalpha() for t in title_tokens)
    # Handles spacing differences such as "airdopes141" vs "Airdopes 141".
    return len(tok) >= 3 and tok in title_compact


def relevance(query: str, title: str) -> float:
    """Fraction of the query's words found in the title (0-1)."""
    q = tokens(query)
    if not q:
        return 0.0
    t = tokens(title)
    t_set, t_compact = set(t), "".join(t)
    return sum(_token_in(tok, t_set, t_compact) for tok in q) / len(q)


def is_accessory(query: str, title: str) -> bool:
    """True for listings like 'Silicone Case for iPhone 15'."""
    q = set(tokens(query))
    t = tokens(title)
    for i, tok in enumerate(t):
        if tok in _ACCESSORY_LINKS:
            # An accessory word *before* "for"/"compatible" means it is the thing being sold.
            return any(w in ACCESSORY_WORDS and w not in q for w in t[:i])
    return False


def is_other_variant(query: str, title: str) -> bool:
    """True when the title names a model variant (Pro, Max, ...) the user did not ask for.

    Only the first few words are checked, where the model name lives; marketing text
    later in a long title ("... with Pro-grade camera") is ignored.
    """
    q = set(tokens(query))
    head = tokens(title)[:8]
    return any(w in VARIANT_WORDS and w not in q for w in head)


def is_same_product(query: str, title: str) -> bool:
    q = tokens(query)
    t = tokens(title)
    t_set, t_compact = set(t), "".join(t)
    # Numbers carry the model / storage / size: all of them must be present.
    for tok in q:
        if any(c.isdigit() for c in tok) and not _token_in(tok, t_set, t_compact):
            return False
    return (
        relevance(query, title) >= MIN_RELEVANCE
        and not is_accessory(query, title)
        and not is_other_variant(query, title)
    )


def filter_matching(query: str, offers: list[Offer]) -> tuple[list[Offer], int]:
    """Keep only offers for the searched product. Returns (kept, number dropped)."""
    kept = [o for o in offers if o.price > 0 and is_same_product(query, o.title)]
    if len(kept) >= 3:
        floor = median(o.price for o in kept) * MIN_PRICE_RATIO
        kept = [o for o in kept if o.price >= floor]
    return kept, len(offers) - len(kept)
