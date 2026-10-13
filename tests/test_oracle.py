"""Cross-check: every hand-written label in tickets.json must match the rule-based oracle."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from refund_triage.data import load_orders, load_tickets, with_derived  # noqa: E402
from refund_triage.oracle import decide  # noqa: E402


class OracleMatchesLabels(unittest.TestCase):
    def test_all_labels(self):
        orders = load_orders()
        for t in load_tickets():
            order = orders.get(t["facts"]["order_id"])
            decision, rules, amount = decide(order, t["facts"], t["from_email"])
            exp = t["expected"]
            with self.subTest(ticket=t["ticket_id"]):
                self.assertEqual(decision, exp["decision"])
                self.assertEqual(sorted(rules), sorted(exp["rules"]))
                self.assertEqual(amount, exp["amount"])

    def test_boundaries(self):
        orders = load_orders()
        self.assertEqual(with_derived(orders["O-1018"])["days_since_delivery"], 30)
        self.assertEqual(with_derived(orders["O-1019"])["days_since_delivery"], 31)
        self.assertEqual(with_derived(orders["O-1011"])["days_past_estimated_delivery"], 15)

    def test_ticket_set_is_diverse(self):
        decisions = {t["expected"]["decision"] for t in load_tickets()}
        self.assertEqual(decisions, {"approve_refund", "store_credit", "reject", "ask_info", "escalate"})
        self.assertGreaterEqual(len(load_tickets()), 10)


if __name__ == "__main__":
    unittest.main()
