"""Rule-based reference implementation of the policy.

It is used for two things only: (1) to cross-check my hand-written ticket labels, so a
labelling slip does not silently score the model wrong; (2) as a unit-test target.
It is NOT part of the prototype: the agent never sees it.
"""
from .config import LARGE_REFUND_EUR
from .data import with_derived


def _item(order, sku):
    return next(i for i in order["items"] if i["sku"] == sku)


def decide(order, facts, sender_email):
    """Return (decision, rules, amount) for a ticket whose structured facts are known."""
    if order is None or order["customer_email"].lower() != sender_email.lower():
        return "ask_info", ["R8"], None
    o = with_derived(order)
    reason = facts["reason"]
    days = o["days_since_delivery"]

    if reason == "cancel":
        if o["status"] == "processing":
            amt = o["order_total"]
            return ("escalate", ["R5", "R7"], None) if amt > LARGE_REFUND_EUR else ("approve_refund", ["R5"], amt)
        return "reject", ["R5"], None

    if reason == "where_is_order":
        if o["status"] == "shipped" and o["days_past_estimated_delivery"] > 10:
            return "escalate", ["R6"], None
        return "reject", ["R6"], None

    skus = facts.get("skus") or [facts["sku"]]
    items = [_item(o, k) for k in skus]
    item = {"final_sale": any(i["final_sale"] for i in items)}
    price = round(sum(i["price"] for i in items), 2)

    if reason == "damaged":
        if days > 14:
            return "escalate", ["R4"], None
        if not facts.get("photo"):
            return "ask_info", ["R4"], None
        return ("escalate", ["R4", "R7"], None) if price > LARGE_REFUND_EUR else ("approve_refund", ["R4"], price)

    # reason == "return"
    if item["final_sale"]:
        base = ("reject", ["R2"], None)
    elif days <= 30:
        base = ("escalate", ["R1", "R7"], None) if price > LARGE_REFUND_EUR else ("approve_refund", ["R1"], price)
    elif days <= 45:
        base = ("store_credit", ["R3"], price)
    else:
        base = ("reject", ["R3"], None)

    if facts.get("exception_requested") and base[0] == "reject":
        return "escalate", ["R9"], None
    return base
