"""Shared demo data: a tiny "Campus Cafe" sales dataset used by every example.

Deterministic on purpose, so tests and the recorded execution log are exact.
"""

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CUPS = [42, 51, 38, 47, 60, 72, 55]
PRICE = 3.50
STOCK = {"beans_kg": 4, "milk_l": 9, "cups": 120}


def sales(days: int = 7) -> dict:
    """Return the last `days` days of sales (1..7)."""
    days = max(1, min(7, int(days)))
    d, c = DAYS[-days:], CUPS[-days:]
    revenue = [round(x * PRICE, 2) for x in c]
    best = max(range(days), key=lambda i: c[i])
    return {
        "days": days,
        "labels": d,
        "cups": c,
        "revenue": revenue,
        "total_cups": sum(c),
        "total_revenue": round(sum(revenue), 2),
        "best_day": d[best],
        "stock": dict(STOCK),
    }
