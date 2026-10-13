#!/usr/bin/env python3
"""Run the agent on ONE ticket and print the full trace. Used for the demo video.

  python3 triage.py T06
  python3 triage.py T18 --no-reflection
  python3 triage.py --email "Hi, I want to return my order O-1001. Unused." --from anna.keller@example.com
"""
import argparse

from refund_triage import trace
from refund_triage.agent import run_agent
from refund_triage.config import MODEL
from refund_triage.data import load_tickets
from refund_triage.llm import LLM
from refund_triage.scoring import score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticket_id", nargs="?")
    ap.add_argument("--email", help="free-text email body (instead of a stored ticket)")
    ap.add_argument("--from", dest="sender", default="anna.keller@example.com")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--no-reflection", action="store_true")
    a = ap.parse_args()

    if a.email:
        ticket = {"ticket_id": "ADHOC", "from_email": a.sender, "subject": "(ad hoc)", "body": a.email, "language": "en"}
    else:
        ticket = next((t for t in load_tickets() if t["ticket_id"] == a.ticket_id), None)
        if ticket is None:
            raise SystemExit("unknown ticket id; see data/tickets.json")

    rec = run_agent(ticket, LLM(a.model), use_reflection=not a.no_reflection)
    sec = trace.sections(ticket, rec)
    print("\n" + sec["email"] + "\n")
    print(sec["tools"] + "\n")
    print(sec["decision"] + "\n")
    print(sec["draft"] + "\n")
    print(sec["stats"])
    if a.ticket_id:
        s = score(ticket, rec)
        print(f"expected: {ticket['expected']['decision']}  ->  {'PASS' if s['success'] else 'FAIL ' + str(s['failed'])}")


if __name__ == "__main__":
    main()
