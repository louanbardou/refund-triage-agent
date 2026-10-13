"""Deterministic scoring of one result against the hand-labelled expectation.

A ticket counts as a task success only if ALL checks pass. No LLM judge is used, so the
scores are reproducible; the cost is that regex checks are blunt (see README, Limits).

Design rules after independent review:
- Claims are checked sentence by sentence, and a sentence that negates the claim ("no refund has
  been approved yet") is not a violation. Leak terms are never exempted.
- An amount only counts if it appears next to a currency marker; the structured refund_amount
  field must match too.
- A run with a system error never counts as a correct decision.
"""
import math
import re
import statistics

from .config import MANUAL_MINUTES, REVIEW_MINUTES_APPROVE, REVIEW_MINUTES_REVISE, STAFF_USD_PER_HOUR
from .data import load_orders

MONEY = {"approve_refund", "store_credit"}

_STOP = {
    "en": "the and you your we is to for of with please thank thanks will have been this that our regards".split(),
    "fr": ("bonjour merci votre vous nous est pour avec commande sera avons cordialement retour remboursement "
           "nous vous pas bien").split(),
    "de": ("guten tag sehr geehrte vielen dank ihre ihr ihnen wir ist bitte erstattung bestellung freundlichen grüßen "
           "gerne rückgabe werden wurde haben").split(),
    "es": ("hola gracias usted su tu te hemos pedido para con una reembolso solicitud recibido saludo "
           "nuestro será nos").split(),
}
# words shared by fr/es/en that must not vote
_NEG = re.compile(r"\b(not|no|n't|cannot|can't|never|unable|without|yet)\b|\bne\b[^.]{0,30}\bpas\b|\bpas\b|\bnon\b|"
                  r"\b(aún|todavía|aun|todavia)\s+no\b|\bnunca\b|\bsin\b|\bjamais\b|\bpas encore\b", re.I)

# Promises that must never appear in a reply whose decision does not grant money.
_PROMISES = [
    r"refund (has been|will be|is being|is) (issued|processed|approved|made|confirmed)",
    r"we(?: will|'ll) (?:refund|process your refund|issue (?:a|your) refund)",
    r"(?:has|have) been (?:refunded|approved)",
    r"your refund (?:is|has been) (?:approved|confirmed)",
    r"(?:sera|a été) (?:remboursé|approuvé)|nous (?:vous )?rembourserons|remboursement (?:a été|sera) (?:effectué|approuvé|accepté)",
    r"(?:será|ha sido) (?:reembolsad|aprobad)|le reembolsaremos|reembolso (?:ha sido|será) (?:aprobado|procesado)",
]
# Delivery-time promises are never allowed (R9), whatever the decision.
_DELIVERY_CLAIMS = [
    r"\b(?:will|should|shall|is going to) (?:arrive|be delivered|be with you)\b",
    r"\b(?:arrive|be delivered)\b[^.]{0,25}\b(?:within|in) \d",
    r"\btomorrow\b",
]


def _sentences(text: str):
    return [s for s in re.split(r"(?<=[.!?\n])\s+", text) if s.strip()]


def claim_violated(patterns, text: str, skip_if_contains: str = "") -> bool:
    """True if any non-negated sentence matches a pattern."""
    for s in _sentences(text.lower()):
        if _NEG.search(s):
            continue
        if skip_if_contains and re.search(skip_if_contains, s):
            continue
        if any(re.search(p, s, re.S) for p in patterns):
            return True
    return False


def detect_lang(text: str) -> str:
    words = re.findall(r"[a-záéíóúñàâçèêëîïôùûü']+", text.lower())
    counts = {lang: sum(w in set(sw) for w in words) for lang, sw in _STOP.items()}
    best = max(counts.values())
    if best == 0:
        return "unknown"
    return max(counts, key=lambda k: (counts[k], k == "en"))


def _amount_forms(x: float):
    f2 = f"{x:.2f}"
    forms = {f2, f2.replace(".", ",")}
    if x == int(x):
        forms.add(str(int(x)))
    return forms


def _money_regex(forms):
    alt = "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True))
    num = rf"(?<![\d.,])(?:{alt})(?![\d])"
    return rf"{num}\s*(?:€|eur\b|euros?\b)|(?:€|eur\b)\s*{num}"


def mentions_amount(text: str, x: float) -> bool:
    return bool(re.search(_money_regex(_amount_forms(x)), text.lower()))


def amounts_in(text: str) -> set:
    found = set()
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(?:€|eur\b|euros?\b)|(?:€|eur\b)\s*(\d+(?:[.,]\d+)?)", text.lower()):
        found.add(float((m.group(1) or m.group(2)).replace(",", ".")))
    return found


def score(ticket: dict, record: dict) -> dict:
    exp, res = ticket["expected"], record["result"]
    reply = res.get("draft_reply", "") or ""
    low = reply.lower()
    decision = res.get("decision")
    error = record.get("error")

    decision_ok = decision == exp["decision"] and error is None
    rules_ok = set(exp["rules"]) <= {r.strip().upper() for r in res.get("rules_cited", [])}

    got_amt = res.get("refund_amount")
    if exp["amount"] is None:
        amount_ok = True  # structured amount is the "amount at stake" for non-money decisions; not scored
    else:
        amount_ok = (got_amt is not None and abs(float(got_amt) - exp["amount"]) < 0.01
                     and mentions_amount(reply, exp["amount"]))

    language_ok = bool(reply) and detect_lang(reply) == ticket["language"]
    forbidden_ok = not claim_violated(exp["forbidden_regex"], reply) and not claim_violated(_DELIVERY_CLAIMS, reply)
    leak_ok = not any(re.search(p, low, re.S) for p in exp.get("leak_regex", []))
    promise_ok = True if decision == "approve_refund" else not claim_violated(
        _PROMISES, reply, skip_if_contains=r"store credit|crédit|credito|crédito" if decision == "store_credit" else "")

    # Amounts quoted in the reply must be: the expected amount, the price of the ticket's own item, 100 (R7),
    # or an amount the customer wrote themselves.
    order = load_orders().get(ticket["facts"]["order_id"])
    allowed = {100.0} | amounts_in(ticket["body"])
    if exp["amount"] is not None:
        allowed.add(float(exp["amount"]))
    if order and order["customer_email"].lower() == ticket["from_email"].lower():
        skus = ticket["facts"].get("skus") or ([ticket["facts"]["sku"]] if ticket["facts"].get("sku") else None)
        for i in order["items"]:
            if skus is None or i["sku"] in skus:
                allowed.add(float(i["price"]))
    amounts_ok = all(any(abs(a - b) < 0.005 for b in allowed) for a in amounts_in(reply))

    checks = dict(decision_ok=decision_ok, rules_ok=rules_ok, amount_ok=amount_ok, language_ok=language_ok,
                  forbidden_ok=forbidden_ok, leak_ok=leak_ok, promise_ok=promise_ok, amounts_ok=amounts_ok,
                  no_error=error is None)
    wrong_money = decision in MONEY and decision != exp["decision"]  # granted money the policy does not grant
    return {"ticket_id": ticket["ticket_id"], "system": record["system"], "success": all(checks.values()),
            "expected": exp["decision"], "got": decision, "wrong_money_decision": bool(wrong_money),
            "checks": checks, "failed": [k for k, v in checks.items() if not v]}


# Reply-quality flags: defects an independent review found that the pass/fail checks do not cover.
# They are REPORTED SEPARATELY and never change task success (the success rules were fixed before these were added).
_QUALITY = {
    "completed_action": r"\b(?:we have|we've|has been|have been|i have|i've) (?:cancel+ed|refunded|processed)\b",
    "invented_condition": r"original packaging|original box",
    "process_leak": r"(?:staff|team) member (?:reviews|will review) this (?:reply|draft)|reviewed by a staff",
    "photo_claim": r"based on the photo|the photo (?:shows|confirms)|from the photo you",
    "identity_disclosure": r"does not match|doesn't match|different (?:order )?number|under your email",
}


def quality_flags(ticket: dict, record: dict) -> list:
    reply = (record["result"].get("draft_reply") or "").lower()
    flags = []
    for name, pat in _QUALITY.items():
        if name == "identity_disclosure" and "R8" not in ticket["expected"]["rules"]:
            continue
        hit = re.search(pat, reply) if name == "identity_disclosure" else claim_violated([pat], reply)  # a negated disclosure is still a disclosure
        if hit:
            flags.append(name)
    return flags


def staff_minutes(system: str, success: bool) -> float:
    """Modelled staff minutes per ticket. Assumptions are in config.py; they are not measured."""
    manual = sum(MANUAL_MINUTES.values())
    find = MANUAL_MINUTES["find_facts"]
    if system == "manual":
        return manual
    if system == "b0_templates":
        return REVIEW_MINUTES_APPROVE if success else manual
    if system in ("b1_access", "b1_access_days"):
        return find + 0.5 + (REVIEW_MINUTES_APPROVE if success else REVIEW_MINUTES_REVISE)
    return REVIEW_MINUTES_APPROVE if success else REVIEW_MINUTES_REVISE  # agent variants


def _p95(xs):
    """95th percentile, linear interpolation between order statistics (same as numpy's default)."""
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = 0.95 * (len(xs) - 1)
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def wilson(k: int, n: int, z: float = 1.96):
    """95% Wilson interval for a proportion. With n=20 it is wide; report it."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def summarize(tickets: list, records: list) -> dict:
    by_id = {t["ticket_id"]: t for t in tickets}
    out = {}
    for system in sorted({r["system"] for r in records}):
        rs = [r for r in records if r["system"] == system]
        sc = [score(by_id[r["ticket_id"]], r) for r in rs]
        n = len(rs)
        lat = [r["latency_s"] for r in rs]
        cost = [r["usage"]["cost_usd"] for r in rs]
        mins = [staff_minutes(system, s["success"]) for s in sc]
        k = sum(s["success"] for s in sc)
        out[system] = {
            "n": n,
            "task_success": k / n,
            "task_success_ci95": wilson(k, n),
            "decision_accuracy": sum(s["checks"]["decision_ok"] for s in sc) / n,
            "wrong_money_decisions": sum(s["wrong_money_decision"] for s in sc),
            "errors": sum(r["error"] is not None for r in rs),
            "latency_mean_s": round(statistics.mean(lat), 2), "latency_p95_s": round(_p95(lat), 2),
            "cost_per_ticket_usd": round(statistics.mean(cost), 5), "cost_total_usd": round(sum(cost), 4),
            "mean_output_tokens": round(statistics.mean(r["usage"]["output_tokens"] for r in rs), 1),
            "mean_tool_calls": round(statistics.mean(len(r["tool_calls"]) for r in rs), 2),
            "guardrail_overrides": sum(bool(r["guardrail_notes"]) for r in rs),
            "reflection_revisions": sum(bool(r.get("reflection") and r["reflection"].get("ok") is False) for r in rs),
            "reflection_failures": sum(bool(r.get("reflection") and r["reflection"].get("ok") is None) for r in rs),
            "staff_minutes_per_ticket": round(statistics.mean(mins), 2),
            "staff_cost_per_ticket_usd": round(statistics.mean(mins) / 60 * STAFF_USD_PER_HOUR, 4),
            "all_in_cost_per_ticket_usd": round(statistics.mean(mins) / 60 * STAFF_USD_PER_HOUR + statistics.mean(cost), 4),
            "task_success_by_set": {st: [sum(s["success"] for s, r in zip(sc, rs) if by_id[r["ticket_id"]].get("set") == st),
                                         sum(1 for r in rs if by_id[r["ticket_id"]].get("set") == st)]
                                    for st in sorted({t.get("set", "core") for t in tickets})},
            "reply_flag_tickets": sum(1 for r in rs if quality_flags(by_id[r["ticket_id"]], r)),
            "reply_flags": {r["ticket_id"]: quality_flags(by_id[r["ticket_id"]], r) for r in reversed(rs)
                            if quality_flags(by_id[r["ticket_id"]], r)},
            "failures": {s["ticket_id"]: s["failed"] for s in reversed(sc) if not s["success"]},
            "failure_counts": {t: sum(1 for s in sc if s["ticket_id"] == t and not s["success"])
                               for t in sorted({s["ticket_id"] for s in sc if not s["success"]})},
        }
    man = staff_minutes("manual", True)
    out["manual"] = {"n": len(tickets), "staff_minutes_per_ticket": round(man, 2),
                     "all_in_cost_per_ticket_usd": round(man / 60 * STAFF_USD_PER_HOUR, 4), "staff_usd_per_hour": STAFF_USD_PER_HOUR}
    return out
