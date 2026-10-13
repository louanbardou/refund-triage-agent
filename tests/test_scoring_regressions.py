"""Regression tests from the independent review: scoring must neither pass bad replies nor fail good ones."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from refund_triage.agent import run_loop  # noqa: E402
from refund_triage.data import load_tickets  # noqa: E402
from refund_triage.llm import LLM  # noqa: E402
from refund_triage.scoring import detect_lang, score, summarize  # noqa: E402
from refund_triage.tools import ToolBox  # noqa: E402
from tests.test_agent_loop import FakeClient, decision, resp, tu  # noqa: E402

T = {t["ticket_id"]: t for t in load_tickets()}


def rec(tid, **over):
    exp = T[tid]["expected"]
    res = dict(decision=exp["decision"], rules_cited=exp["rules"], evidence=["x"], refund_amount=exp["amount"],
               customer_language=T[tid]["language"], draft_reply="", internal_note="")
    res.update(over)
    return {"system": "agent", "ticket_id": tid, "error": None, "result": res}


class FalsePasses(unittest.TestCase):
    def test_day_31_is_not_an_amount(self):  # T19 expects 31 EUR
        r = rec("T19", draft_reply="Thank you, we will refund your card under the day 31 rule. Regards, Nordlys")
        self.assertIn("amount_ok", score(T["T19"], r)["failed"])

    def test_structured_amount_must_match(self):
        r = rec("T01", refund_amount=95.0, draft_reply="Thank you, we can refund 59.00 EUR for your throw. Regards")
        self.assertIn("amount_ok", score(T["T01"], r)["failed"])

    def test_leak_to_mismatched_sender_is_caught(self):  # T13
        r = rec("T13", draft_reply="Thank you, your order was delivered on 2026-10-02 and we need your checkout email. Regards")
        self.assertIn("leak_ok", score(T["T13"], r)["failed"])

    def test_invented_delivery_time_is_caught(self):  # T10
        r = rec("T10", draft_reply="Thank you for writing. It should arrive in 2-3 days, we will help you. Regards")
        self.assertIn("forbidden_ok", score(T["T10"], r)["failed"])

    def test_wrong_language_with_no_stopwords_fails(self):
        self.assertEqual(detect_lang("12345 !!!"), "unknown")

    def test_error_run_never_counts_as_correct_decision(self):  # T02 expects escalate
        r = rec("T02", draft_reply="")
        r["error"] = "APIError: boom"
        s = score(T["T02"], r)
        self.assertFalse(s["checks"]["decision_ok"])
        self.assertFalse(s["success"])

    def test_summary_decision_accuracy_excludes_errors(self):
        bad = rec("T02")
        bad.update(error="x", latency_s=0, usage={"cost_usd": 0, "output_tokens": 0}, tool_calls=[], guardrail_notes=[])
        out = summarize([T["T02"]], [bad])["agent"]
        self.assertEqual(out["decision_accuracy"], 0.0)


class FalseFails(unittest.TestCase):
    def test_negated_exception_sentence_is_fine(self):  # T15
        r = rec("T15", draft_reply="Thank you, we will pass this to a manager. No exception has been granted yet. Regards, we will help you")
        self.assertTrue(score(T["T15"], r)["checks"]["forbidden_ok"])

    def test_negated_refund_is_fine(self):  # T10
        r = rec("T10", draft_reply="Thank you, we will help you. No refund has been approved at this stage because your order is in transit. Regards")
        s = score(T["T10"], r)
        self.assertTrue(s["checks"]["forbidden_ok"] and s["checks"]["promise_ok"])

    def test_quoting_pre_approved_to_refuse_it_is_fine(self):  # T18
        r = rec("T18", draft_reply="Thank you, we will help you. We cannot treat this as pre-approved; it falls outside our return period. Regards")
        self.assertTrue(score(T["T18"], r)["checks"]["forbidden_ok"])

    def test_store_credit_wording_is_fine(self):  # T03
        r = rec("T03", draft_reply="Thank you, we will help you. Your refund will be issued as store credit of 35.00 EUR. Regards")
        self.assertTrue(score(T["T03"], r)["checks"]["promise_ok"])

    def test_customer_own_words_may_be_echoed(self):  # T13: customer wrote "curtains" and 64 euros
        r = rec("T13", draft_reply="Thank you, we will help you. We could not find the curtains order for this email address; please send the checkout email. Regards")
        s = score(T["T13"], r)
        self.assertTrue(s["checks"]["leak_ok"])

    def test_french_no_free_shipping_confirmation_is_fine(self):  # T17
        r = rec("T17", draft_reply="Bonjour Mia, merci. Nous vous remboursons 26,00 € pour le chemin de table. Nous ne pouvons pas confirmer que la livraison est gratuite; notre équipe vous répondra. Cordialement",
                refund_amount=26.0)
        s = score(T["T17"], r)
        self.assertTrue(s["checks"]["forbidden_ok"], s)
        self.assertTrue(s["checks"]["language_ok"], s)

    def test_natural_spanish_is_detected(self):  # T16
        r = rec("T16", draft_reply="Hola Lucas, hemos recibido tu solicitud. Te reembolsaremos 55,00 € por la tetera. Un saludo, Nordlys Home Support")
        self.assertEqual(score(T["T16"], r)["checks"]["language_ok"], True)
        self.assertTrue(score(T["T16"], r)["checks"]["amount_ok"])

    def test_total_instead_of_item_is_caught(self):  # T12: refund 22, not the 52 total
        r = rec("T12", draft_reply="Thank you, we will refund 52.00 EUR for your frame. Regards, we will help you")
        self.assertIn("amounts_ok", score(T["T12"], r)["failed"])


class LoopSafety(unittest.TestCase):
    def test_decision_in_same_turn_as_lookup_is_not_accepted(self):
        client = FakeClient([
            resp(tu("lookup_order", order_id="O-1001"), tu("submit_decision", **decision())),
            resp(tu("submit_decision", **decision(refund_amount=59.0))),
        ])
        out, steps = run_loop(LLM("claude-haiku-5-5", client), T["T01"], ToolBox(T["T01"]["from_email"]))
        self.assertEqual(steps, 2)  # first submit ignored, accepted only after the lookup result was returned
        self.assertIsNotNone(out)

    def test_order_id_is_normalised(self):
        tb = ToolBox("anna.keller@example.com")
        self.assertIn("Wool throw", tb.run("lookup_order", {"order_id": " o-1001 "}))


if __name__ == "__main__":
    unittest.main()


class RealRepliesFromFirstLiveRun(unittest.TestCase):
    """Good replies from the first live run that an earlier scoring version wrongly failed, and bad variants that must still fail."""

    def test_explaining_closed_cash_window_is_fine(self):  # T03
        r = rec("T03", draft_reply="Dear Sofia, thank you. Our policy allows a full refund to your original payment method only within 30 days of delivery. "
                "Your return window for a cash refund has passed. We can offer store credit of 35.00 EUR, so we will help you. Kind regards")
        self.assertEqual(score(T["T03"], r)["failed"], [])

    def test_promising_card_refund_still_fails(self):  # T03
        r = rec("T03", draft_reply="Dear Sofia, thank you, we will refund 35.00 EUR to your original payment method. Kind regards, we will help you")
        self.assertFalse(score(T["T03"], r)["success"])

    def test_stating_return_windows_is_not_a_delivery_promise(self):  # T18
        r = rec("T18", draft_reply="Hi Oscar, thank you. Our policy allows a full refund within 30 days of delivery, and late returns for store credit "
                "within 45 days. Both windows have now passed, so we are unable to offer a refund. We will help you further. Kind regards")
        self.assertTrue(score(T["T18"], r)["checks"]["forbidden_ok"])

    def test_escalation_may_show_amount_at_stake(self):  # T02
        r = rec("T02", refund_amount=145.0, draft_reply="Hello Marc, thank you, we will help you. Your request has been passed to a manager. Kind regards")
        self.assertTrue(score(T["T02"], r)["checks"]["amount_ok"])


class ReplyQualityFlagsAndP95(unittest.TestCase):
    def test_flags_from_independent_review(self):
        from refund_triage.scoring import quality_flags
        r = rec("T09", draft_reply="Hello, we have cancelled the order and will refund 45.00 EUR. Please return it in its original packaging. We will help you.")
        self.assertEqual(sorted(quality_flags(T["T09"], r)), ["completed_action", "invented_condition"])

    def test_identity_disclosure_only_on_r8_tickets(self):
        from refund_triage.scoring import quality_flags
        r13 = rec("T13", draft_reply="The email you wrote from does not match the email used on the order. Please send it. We will help you.")
        self.assertEqual(quality_flags(T["T13"], r13), ["identity_disclosure"])
        r01 = rec("T01", draft_reply="Your name does not match anything we know, but we will help you.")
        self.assertEqual(quality_flags(T["T01"], r01), [])

    def test_flags_never_change_success(self):
        r = rec("T01", draft_reply="Hello Anna, thank you, we will help you. We can refund 59.00 EUR. Please use the original packaging. Regards")
        self.assertTrue(score(T["T01"], r)["success"])

    def test_p95_interpolates(self):
        from refund_triage.scoring import _p95
        self.assertAlmostEqual(_p95(list(range(1, 32))), 29.5, places=6)  # 31 values: k = 28.5
