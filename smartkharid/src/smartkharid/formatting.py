"""Human-friendly formatting of prices and counts."""

from __future__ import annotations

CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "AED": "AED "}


def _indian_grouping(whole: int) -> str:
    """12345678 -> '1,23,45,678' (Indian lakh/crore grouping)."""
    digits = str(whole)
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def format_money(amount: float, currency: str = "INR") -> str:
    """Format an amount the way shoppers expect to read it, e.g. ₹1,23,456."""
    symbol = CURRENCY_SYMBOLS.get(currency, f"{currency} ")
    sign = "-" if amount < 0 else ""
    whole, cents = divmod(round(abs(amount) * 100), 100)
    body = _indian_grouping(whole) if currency == "INR" else f"{whole:,}"
    if cents:
        body += f".{cents:02d}"
    return f"{sign}{symbol}{body}"


def format_count(n: int) -> str:
    """12345 -> '12,345'."""
    return f"{n:,}"
