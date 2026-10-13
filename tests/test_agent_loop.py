"""Offline tests of the agent mechanics with a scripted fake model (no API calls)."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from refund_triage import guardrails  # noqa: E402
from refund_triage.agent import run_agent  # noqa: E402
from refund_triage.data import load_tickets  # noqa: E402
from refund_triage.llm import LLM  # noqa: E402
from refund_triage.scoring import detect_lang, score  # noqa: E402
from refund_triage.tools import ToolBox  # noqa: E402

TICKETS = {t["ticket_id"]: t for t in load_tickets()}
_n = 0


def tu(name, **inp):
    global _n
    _n += 1
    return NS(type="tool_use", id=f"tu_{_n}", name=name, input=inp)


def resp(*blocks):
    return NS(content=list(blocks), usage=NS(input_tokens=100, output_tokens=20), stop_reason="tool_use")


class FakeClient:
    """Plays back a fixed list of responses and records the requests it received."""

    def __init__(self, script):
        self.script, self.requests = list(script), []
        self.messages = NS(create=self._create)

    def _create(self, **kw):
        self.requests.append(kw)
        return self.script.pop(0)


def decision(**over):
    d = dict(decision="approve_refund", rules_cited=["R1"], evidence=["delivered 10 days ago"], refund_amount=59.0,
             customer_language="en", draft_reply="Hello, we can refund 59.00 EUR for the wool throw. Nordlys Home Support",
             internal_note="ok")
    d.update(over)
    return d


class ToolScope(unittest.TestCase):
    def test_other_customers_order_is_hidden(self):
        tb = ToolBox("someone.else@example.com")
        out = tb.run("lookup_order", {"order_id": "O-1001"})
        self.assertIn("error", out)
        self.assertNotIn("Wool throw", out)

    def test_own_order_has_derived_days(self):
        tb = ToolBox("anna.keller@example.com")
        out = tb.run("lookup_order", {"order_id": "O-1001"})
        self.assertIn('"days_since_delivery": 10', out)


class AgentLoop(unittest.TestCase):
    def test_happy_path_lookup_then_submit_then_check(self):
        client = FakeClient([
            resp(tu("lookup_order", order_id="O-1001")),
            resp(tu("submit_decision", **decision())),
            resp(tu("submit_check", ok=True, issues=[], revised_reply="")),
        ])
        rec = run_agent(TICKETS["T01"], LLM("claude-haiku-5-5", client))
        self.assertIsNone(rec["error"])
        self.assertEqual(rec["result"]["decision"], "approve_refund")
        self.assertEqual(rec["steps"], 2)
        self.assertEqual(len(rec["tool_calls"]), 1)
        self.assertEqual(rec["usage"]["llm_calls"], 3)
        self.assertTrue(score(TICKETS["T01"], rec)["success"])

    def test_reflection_can_revise_draft_but_not_decision(self):
        client = FakeClient([
            resp(tu("submit_decision", **decision(draft_reply="Refund of 99.00 EUR approved."))),
            resp(tu("submit_check", ok=False, issues=["wrong amount"], revised_reply="We can refund 59.00 EUR. Nordlys Home Support")),
        ])
        rec = run_agent(TICKETS["T01"], LLM("claude-haiku-5-5", client))
        self.assertIn("59.00", rec["result"]["draft_reply"])
        self.assertEqual(rec["result"]["decision"], "approve_refund")
        self.assertIn("draft_reply_before_check", rec["result"])

    def test_step_cap_fails_safe_to_escalate(self):
        client = FakeClient([resp(tu("list_my_orders")) for _ in range(10)])
        rec = run_agent(TICKETS["T01"], LLM("claude-haiku-5-5", client))
        self.assertEqual(rec["error"], "no_decision")
        self.assertEqual(rec["result"]["decision"], "escalate")
        self.assertLessEqual(len(client.requests), 6)
        self.assertFalse(score(TICKETS["T02"], rec)["success"])  # an error never counts as success, even if 'escalate' matches

    def test_api_failure_is_reported_not_hidden(self):
        def boom(**kw):
            raise RuntimeError("no credentials")
        client = NS(messages=NS(create=boom))
        rec = run_agent(TICKETS["T01"], LLM("claude-haiku-5-5", client))
        self.assertIn("RuntimeError", rec["error"])
        self.assertEqual(rec["result"]["decision"], "escalate")


class Guardrails(unittest.TestCase):
    def test_large_refund_forced_to_manager(self):
        r, notes = guardrails.apply(decision(refund_amount=145.0))
        self.assertEqual(r["decision"], "escalate")
        self.assertIn("R7", r["rules_cited"])
        self.assertTrue(notes)

    def test_small_refund_untouched(self):
        r, notes = guardrails.apply(decision())
        self.assertEqual(r["decision"], "approve_refund")
        self.assertFalse(notes)

    def test_money_decision_without_evidence_is_escalated(self):
        r, notes = guardrails.apply(decision(evidence=[]))
        self.assertEqual(r["decision"], "escalate")


class Scoring(unittest.TestCase):
    def rec(self, **over):
        res = decision(**over)
        return {"system": "agent", "ticket_id": "T01", "error": None, "result": res}

    def test_language_detection(self):
        self.assertEqual(detect_lang("Bonjour, votre commande est bien reçue, merci"), "fr")
        self.assertEqual(detect_lang("Hola, gracias por su pedido, para nosotros es un placer"), "es")
        self.assertEqual(detect_lang("Thank you, we will review your request"), "en")

    def test_wrong_amount_fails(self):
        s = score(TICKETS["T01"], self.rec(draft_reply="We can refund 95.00 EUR. Thank you, we will help you"))
        self.assertFalse(s["success"])

    def test_invented_amount_is_caught(self):
        s = score(TICKETS["T01"], self.rec(draft_reply="We refund 59.00 EUR and add 20 EUR as a gift. Thank you, we will help you"))
        self.assertIn("amounts_ok", s["failed"])

    def test_promise_on_escalation_is_caught(self):
        t = TICKETS["T02"]
        rec = {"system": "agent", "ticket_id": "T02", "error": None,
               "result": decision(decision="escalate", rules_cited=["R1", "R7"], refund_amount=None,
                                  draft_reply="Thank you. Your refund has been approved and we will help you.")}
        self.assertFalse(score(t, rec)["success"])


if __name__ == "__main__":
    unittest.main()
