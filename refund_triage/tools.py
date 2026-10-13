"""Read-only tools exposed to the agent.

Authorization is enforced here, in code, not in the prompt: the tools are bound to the
sender's email, so a lookup can never return another customer's order (policy R8).
"""
import json

from .config import DECISIONS
from .data import load_orders, with_derived

LOOKUP_ORDER = {
    "name": "lookup_order",
    "description": (
        "Look up one order by order id, for the customer who sent the email. Returns the order "
        "record with computed day counts (days_since_delivery, days_past_estimated_delivery). "
        "Returns an error if no order with that id belongs to the sender's email address."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"order_id": {"type": "string", "description": "e.g. O-1001"}},
        "required": ["order_id"],
        "additionalProperties": False,
    },
}

LIST_MY_ORDERS = {
    "name": "list_my_orders",
    "description": "List the order ids and statuses that belong to the sender's email address. Use when the email gives no order id.",
    "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
}

SUBMIT_DECISION = {
    "name": "submit_decision",
    "description": (
        "Submit the final triage result for staff review. Call exactly once, after you have the facts you need. "
        "Nothing is sent to the customer: a staff member reviews the draft first."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": DECISIONS},
            "rules_cited": {"type": "array", "items": {"type": "string"}, "description": "Policy rule ids, e.g. [\"R1\"]"},
            "evidence": {"type": "array", "items": {"type": "string"}, "description": "Facts from tool results that support the decision"},
            "refund_amount": {"type": ["number", "null"], "description": "EUR amount for approve_refund / store_credit, else null"},
            "customer_language": {"type": "string", "description": "ISO code of the language the customer wrote in"},
            "draft_reply": {"type": "string", "description": "Reply to the customer, in the customer's language"},
            "internal_note": {"type": "string", "description": "One or two sentences for the staff reviewer: what to check, what is missing"},
        },
        "required": ["decision", "rules_cited", "evidence", "refund_amount", "customer_language", "draft_reply", "internal_note"],
        "additionalProperties": False,
    },
}

TOOLS = [LOOKUP_ORDER, LIST_MY_ORDERS, SUBMIT_DECISION]


class ToolBox:
    """Executes tool calls on behalf of one sender. Records every call for the audit trail."""

    def __init__(self, sender_email: str):
        self.sender = sender_email.lower()
        self.orders = load_orders()
        self.calls = []

    def run(self, name: str, args: dict) -> str:
        if name == "lookup_order":
            oid = str(args.get("order_id", "")).strip().upper()
            order = self.orders.get(oid)
            if order is None or order["customer_email"].lower() != self.sender:
                out = {"error": "No order with this id was found for the sender's email address."}
            else:
                out = with_derived(order)
        elif name == "list_my_orders":
            mine = [{"order_id": o["order_id"], "status": o["status"]}
                    for o in self.orders.values() if o["customer_email"].lower() == self.sender]
            out = {"orders": mine}
        else:
            out = {"error": f"Unknown tool {name}"}
        text = json.dumps(out, ensure_ascii=False)
        self.calls.append({"tool": name, "input": args, "output": out})
        return text
