"""Loading the synthetic shop data and computing date facts deterministically.

Date arithmetic is done in code, not by the model: language models are unreliable at it,
and the policy has day-30 / day-31 boundaries.
"""
import json
from datetime import date

from .config import DATA_DIR, TODAY


def _d(s):
    return date.fromisoformat(s) if s else None


def load_policy() -> str:
    return (DATA_DIR / "policy.md").read_text()


def load_orders() -> dict:
    return {o["order_id"]: o for o in json.loads((DATA_DIR / "orders.json").read_text())}


def load_tickets() -> list:
    return json.loads((DATA_DIR / "tickets.json").read_text())


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
