# Refund Triage Agent

**Refund emails, handled automatically. People still sign.**

Course project for *Generative and Agentic AI for Business*, MSc Data Science and AI for Business, HEC Paris (2026–2027).
**Author: Louan Bardou (sole author).**
Live site: https://louanbardou.github.io/refund-triage-agent/

---

## What this is

A small online shop answers return, cancellation and refund emails by hand. Each one needs the order, a policy whose rules depend on dates, and a reply in the customer's language. I built an agent that reads the email, looks up the order with read-only tools, applies the written policy and drafts the reply. A staff member reviews and approves every draft. Nothing is sent automatically.

Everything is fictional: the shop (Nordlys Home), the orders and the tickets are synthetic.

## Why this problem

- It repeats: the same questions, the same rules, several languages.
- It has a checkable right answer, because a written policy gives every ticket a label.
- A person must stay in charge: money and exceptions need approval, so the control points are concrete.
- The class example was hotel emails. I chose a workflow with an order lookup, so the agent has real work to do.

## Course framework

- **EDGE target:** Efficiency (staff minutes per ticket) as the main target, Decisions (every reply grounded in the policy and the order record) as the second. Growth and Empowerment are not claimed.
- **5A choice:** an **Agent**, kept small and compared against simpler options (Access, Automation). Patterns: tool use, ReAct, reflection. The full argument is in [`docs/rationale.md`](docs/rationale.md).
- **Oversight:** human approval on every draft, read-only tools bound to the sender's email, day counts computed by the tool, a code guardrail at 100 EUR, email text treated as untrusted data, any failure routed to a person.

## Deliverables

| Requirement | Where |
|---|---|
| Working prototype + run instructions | this repository, [Run it](#run-it) |
| One-page EDGE / 5A rationale | [`docs/rationale.md`](docs/rationale.md) |
| At least 10 tests against a simple baseline | 31 hand-written tickets + 500 generated tickets, 5 systems; 41 unit tests in `tests/` |
| Demo video | the Video tab of the live site |
| Task success, latency and cost | Results tab of the live site, `results/<run>/summary.json` |

## Results

Five systems on 31 tickets I wrote, then three of them on 500 generated tickets (four languages, every rule, boundary days). Model: `claude-haiku-5-5`.

| System | 31 tickets | 500 tickets | Mean latency | Model cost / ticket |
|---|---|---|---|---|
| B0 keyword templates | 1/31 | 17/500 | ~0 s | $0 |
| B1 paste email + order + policy, one call | 30/31 | 482/500 | 4.2 s | $0.00064 |
| B1d same, with precomputed day counts | 30/31 | not run | 4.2 s | $0.00063 |
| Agent, no draft check | 31/31 | not run | 4.8 s | $0.00090 |
| **Agent + draft check** | 30/31 | 486/500 | 7.1 s | $0.0013 |

"Success" means the decision, the cited rules, the amount, the language and several claim and leak checks all pass. The checks are deterministic (rules and regular expressions, no LLM judge).

What the results suggest:

- Model-based systems clearly beat templates (97% against 3%).
- Accuracy does not separate the agent from pasting the order into a chat model.
- The difference is **staff time**: about 1 minute per ticket with the agent, against 3.5 minutes pasting by hand and 5 minutes fully manual. This is **modelled from assumed step times**, not measured.
- All-in cost per ticket is about $0.44 against $2.08 manual, with staff time at an assumed $25/h. Model tokens are about 2.1 times the paste approach, a small share of the all-in cost.
- Decisions were identical across three repeated runs of the 31 tickets.

## Limits (read before quoting any number)

- Synthetic tickets that I wrote; the 500 extra tickets are generated, with labels from a rule-based oracle that I checked against my 31 hand-written labels.
- One small model. Sampling parameters cannot be set on this model family, so single-run differences of one ticket are not interpretable.
- Staff minutes and the hourly cost are assumptions (`refund_triage/config.py`). [`docs/time_study.md`](docs/time_study.md) explains how to measure them.
- **Scoring was revised once** after the first live run: four correct replies were wrongly failed by a regex, and one delivery-time regex matched return-window wording. Both were false fails confirmed by reading the replies. The first scores are kept (`summary_v1.json`). The 11 harder tickets were written after that, so there is no held-out set.
- **T30 is label-ambiguous** (a claimed phone authorisation: reject or escalate). I did not change the label after seeing the results. Replaying T30 eight times per system (`data/label_probes.json`) gave 7 escalations and 1 refusal for both the agent with the draft check and the agent without it, and 8 escalations for pasting, so the difference between the two agent variants in the single main run is sampling chance, not an effect of the check. The heat map shows T30 as an amber "ambiguous label" cell; task-success scores stay strict.
- **Policy R7 is ambiguous** for store credit above 100 EUR, and my generated emails name two items in one phrase. Of the agent's 14 misses on 500 tickets, 8 are multi-item emails (in 7 the agent asked which item), 5 are store credits above 100 EUR that it escalated, and 1 is another case. Labels were not changed.
- B1 receives the correct order record from the test harness, a step the agent does with tools.
- Reply-quality flags (completed-action claims, invented conditions, internal-process leaks, identity disclosure) are reported separately and never change task success.

## Run it

Python 3.10+ and `pip install anthropic`. Tests and the template baseline need no API key.

```bash
git clone https://github.com/louanbardou/refund-triage-agent.git
cd refund-triage-agent

python3 -m unittest discover -s tests -t .            # offline checks (41 tests)
python3 run_eval.py --systems b0                       # offline baseline

export ANTHROPIC_API_KEY=...                           # live runs
python3 triage.py T06                                  # one ticket, full trace
python3 run_eval.py --systems b0,b1,b1d,agent_nr,agent --label main
python3 -m refund_triage.gen_tickets --n 500           # regenerate the scale set
python3 run_eval.py --set scale --systems b0,b1,agent --workers 6 --label scale500
python3 -m refund_triage.site results/<run> --repeat results/<repeat-run> --scale results/<scale-run> --video <file.mp4>
```

Model, effort and prices are set in `refund_triage/config.py` (`TRIAGE_MODEL`, `TRIAGE_EFFORT`).

## Repository layout

| Path | Role |
|---|---|
| `data/policy.md` | The written returns policy, rules R1–R9 |
| `data/orders.json`, `data/tickets.json` | 30 synthetic orders, 31 labelled tickets |
| `data/orders_scale.json`, `data/tickets_scale.json` | 500 generated orders and tickets |
| `refund_triage/agent.py` | Tool-use loop (max 6 steps) plus one draft check |
| `refund_triage/tools.py` | Read-only tools, bound to the sender's email |
| `refund_triage/guardrails.py` | Deterministic overrides after the model (above 100 EUR, no evidence) |
| `refund_triage/baselines.py` | Keyword templates and the paste-and-draft baselines |
| `refund_triage/scoring.py` | Deterministic checks, reply-quality flags, summaries |
| `refund_triage/oracle.py` | Rule-based reference used to cross-check labels |
| `refund_triage/gen_tickets.py` | Generator for the scale set |
| `refund_triage/site.py` | Builds the live site in `docs/` |
| `run_eval.py`, `triage.py`, `rescore.py` | Evaluation runner, single-ticket trace, re-scoring without model calls |
| `tests/` | 41 offline tests, including regression tests for scoring |
| `docs/` | The site, [`rationale.md`](docs/rationale.md), [`video_story.md`](docs/video_story.md), [`time_study.md`](docs/time_study.md) |

## Use of AI tools

I built this with Claude Code, as the course allows. The model inside the agent is Claude Haiku 5.5. I also used fresh-context AI reviewers to audit the scoring and the results; they found real defects, which are documented above. The choices, the policy, the labels and the interpretation are mine, and so is the responsibility for them.
