"""Loading the synthetic shop data and computing date facts deterministically.

Date arithmetic is done in code, not by the model: language models are unreliable at it,
and the policy has day-30 / day-31 boundaries.
"""
import json
from datetime import date
from functools import lru_cache

from .config import DATA_DIR, TODAY


def _d(s):
    return date.fromisoformat(s) if s else None


@lru_cache(maxsize=None)
def load_policy() -> str:
    return (DATA_DIR / "policy.md").read_text()


@lru_cache(maxsize=None)
def load_orders() -> dict:
    """Curated orders plus (if generated) the scale-test orders. Order id ranges do not overlap."""
    orders = {o["order_id"]: o for o in json.loads((DATA_DIR / "orders.json").read_text())}
    extra = DATA_DIR / "orders_scale.json"
    if extra.exists():
        orders.update({o["order_id"]: o for o in json.loads(extra.read_text())})
    return orders


def load_tickets(scale: bool = False) -> list:
    """Curated tickets (core + hard). With scale=True, the generated scale-test tickets instead."""
    f = DATA_DIR / ("tickets_scale.json" if scale else "tickets.json")
    return json.loads(f.read_text())


def with_derived(order: dict, today: date = TODAY) -> dict:
    """Return a copy of the order with day counts added."""
    o = json.loads(json.dumps(order))
    delivered, est = _d(o["delivered_date"]), _d(o["estimated_delivery"])
    o["today"] = today.isoformat()
    o["days_since_delivery"] = (today - delivered).days if delivered else None
    o["days_past_estimated_delivery"] = (
        (today - est).days if (est and o["status"] == "shipped") else None
    )
    o["order_total"] = round(sum(i["price"] for i in o["items"]), 2)
    return o
