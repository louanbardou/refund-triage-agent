"""Deterministic control points applied AFTER the model decides.

The model proposes; code enforces the rules that must never depend on model judgement.
Every override is recorded, so the evaluation can report how often a guardrail was needed.
"""
from .config import LARGE_REFUND_EUR


def apply(result: dict) -> tuple[dict, list]:
    """Return (possibly corrected result, list of override notes)."""
    notes = []
    r = dict(result)
    amount = r.get("refund_amount")
    if r.get("decision") == "approve_refund" and amount is not None and amount > LARGE_REFUND_EUR:
        notes.append(f"R7: refund {amount} EUR exceeds {LARGE_REFUND_EUR} EUR; changed approve_refund to escalate")
        r["decision"] = "escalate"
        r["refund_amount"] = None
        if "R7" not in r.get("rules_cited", []):
            r["rules_cited"] = list(r.get("rules_cited", [])) + ["R7"]
    if r.get("decision") in ("approve_refund", "store_credit") and amount is None:
        notes.append("Money decision without an amount; threshold R7 cannot be checked; changed to escalate")
        r["decision"] = "escalate"
    # Without any evidence there is nothing for the reviewer to verify: force a human decision.
    if r.get("decision") in ("approve_refund", "store_credit") and not r.get("evidence"):
        notes.append("No evidence recorded for a money decision; changed to escalate")
        r["decision"] = "escalate"
        r["refund_amount"] = None
    return r, notes
