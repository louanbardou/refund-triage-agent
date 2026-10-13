"""Central configuration. Everything that affects results lives here."""
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

# Fixed "today" so the synthetic orders and the day counts stay reproducible.
TODAY = date(2026, 10, 13)

# Small, cheap model by default: the task is a bounded policy lookup, and cost is a graded metric.
MODEL = os.environ.get("TRIAGE_MODEL", "claude-haiku-5-5")
EFFORT = os.environ.get("TRIAGE_EFFORT", "low")  # output_config.effort

# USD per 1M tokens (input, output), standard prompts. From the Claude API model table, 2026-10-06.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}

MAX_STEPS = 6            # hard cap on agent loop iterations
MAX_TOKENS = 4000        # per call; includes thinking tokens
LARGE_REFUND_EUR = 100   # R7: above this, a manager decides

DECISIONS = ["approve_refund", "store_credit", "reject", "ask_info", "escalate"]

# Staff-time assumptions (minutes per ticket). These are assumptions, not measurements.
# See docs/time_study.md for how to replace them with a stopwatch measurement.
MANUAL_MINUTES = {"read": 0.5, "find_facts": 2.0, "compose": 1.5, "check": 0.5, "send": 0.5}
REVIEW_MINUTES_APPROVE = 1.0   # read draft + facts side by side, click approve
REVIEW_MINUTES_REVISE = 2.5    # read, rewrite part of the draft, send
