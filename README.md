# Refund triage agent (Nordlys Home): prototype

Assignment: MSc DSAIB, *Generative and Agentic AI for Business* (HEC Paris), afternoon exercise.
One user (a support agent), one workflow (customer emails asking to return, cancel or get a refund on an order), on a fictional shop with synthetic data.

The system reads an email, looks up the order with read-only tools, applies a written policy, and prepares a decision plus a draft reply in the customer's language. A staff member reviews the draft beside the facts. **Nothing is ever sent automatically.**

## Run it

Requirements: Python 3.10+ and `pip install anthropic` (tested with 0.97.0). No other dependency.

```bash
cd refund-triage-agent

# 1. Offline checks (no API key): labels vs rule-based oracle, agent loop with a scripted fake model, scoring
python3 -m unittest discover -s tests -v

# 2. Offline baseline B0 (keyword templates), also writes the review page
python3 run_eval.py --systems b0 --verbose

# 3. Live runs need credentials: either `export ANTHROPIC_API_KEY=...` or `ant auth login`
python3 triage.py T06                                   # one ticket, full trace (for the demo)
python3 run_eval.py --systems b0,b1,agent,agent_nr --label main --verbose
python3 run_eval.py --systems agent --repeats 3 --label variance   # run-to-run variance

open results/*-main/report.html                         # the staff review screen
```

Model: `claude-haiku-5-5` by default (`TRIAGE_MODEL` or `--model` to change; `TRIAGE_EFFORT`, default `low`). Cost uses the per-token prices in `refund_triage/config.py`.

## Layout

| Path | Role |
|---|---|
| `data/policy.md` | The written policy, rules R1–R9 (the only source of truth) |
| `data/orders.json` | 19 synthetic orders |
| `data/tickets.json` | 20 labelled test emails (expected decision, rules, amount, forbidden claims) |
| `refund_triage/tools.py` | Read-only tools, **bound to the sender's email** (identity check enforced in code) |
| `refund_triage/agent.py` | Tool-use + ReAct loop (max 6 steps), then one reflection pass on the draft |
| `refund_triage/guardrails.py` | Deterministic overrides after the model (refund > 100 EUR cannot be auto-approved) |
| `refund_triage/baselines.py` | B0 keyword templates, B1 "Access" (paste email + order + policy, one shot) |
| `refund_triage/scoring.py` | Deterministic checks, no LLM judge |
| `refund_triage/oracle.py` | Rule-based reference used only to cross-check my labels |
| `run_eval.py`, `triage.py` | Evaluation runner, single-ticket trace |
| `docs/` | `rationale.md` (EDGE / 5A page), `video_script.md`, `time_study.md` |
| `results/<run>/` | `records.jsonl` (every trace), `summary.json`, `report.html` |

## What counts as success

A ticket is a **task success** only if all of these hold: correct decision label; expected policy rules cited; correct amount in the reply; reply in the customer's language; none of the ticket's forbidden claims; no refund promise when the decision does not grant one; no invented EUR amounts; no system error. Latency is wall-clock per ticket. Cost is tokens times the price table.

## Limits (read before quoting any number)

- 20 synthetic tickets written by the author, hand-labelled and cross-checked with a rule-based oracle. A small, clean sample says little about real inbox noise.
- Scoring is regex- and rule-based, so it is blunt: it can miss a subtle bad sentence, and it can fail a good reply for an odd phrasing. Read the traces in `report.html`.
- Staff-minute figures are modelled from assumptions in `refund_triage/config.py` (not measured), unless you replace them using `docs/time_study.md`.
- The policy is short and unambiguous by design. Real policies have exceptions and conflicts.
- Model sampling parameters cannot be set on this model family, so repeated runs can differ; use `--repeats`.
- **Scoring was revised once after the first live run** (`summary_v1.json` keeps the earlier scores): four replies that correctly explained a closed refund window were wrongly failed by a regex, and one delivery-time regex also matched return-window wording. Both were false fails confirmed by reading the replies. The 11 "hard" tickets were written after that, and there is no held-out set.
- **Ceiling effect.** On 31 tickets, every model-based system passes 30–31, so the checks cannot rank them. The data supports "model systems clearly beat keyword templates"; it does not support "the agent is more accurate than pasting the order into a chat".
- **Staff minutes are modelled** (2.5 min for a manual lookup + paste, 1.0 or 2.5 min review). The agent-versus-paste time gap is almost entirely that assumption.
- **B1 receives the right order record from the harness** (and falls back to the sender's own order when the id is wrong), a human step the agent performs with tools.
- **T30 is label-ambiguous**: expected `reject` (80 days, R3); `escalate` to verify a claimed phone authorisation is also defensible (R9). The label was not changed after seeing results.
- **Reply-quality flags** (completed-action claims, invented conditions, internal-process leaks, identity disclosure) are reported separately and never change task success. An independent review found a few such defects in replies that passed.
