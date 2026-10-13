#!/usr/bin/env python3
"""Run the evaluation: every ticket through every selected system, then score and summarize.

  python3 run_eval.py --systems b0                      # offline, no API key needed
  python3 run_eval.py --systems b0,b1,agent             # full comparison (needs credentials)
  python3 run_eval.py --systems agent,agent_nr --repeats 3
  python3 run_eval.py --systems agent --tickets T06,T18 --verbose

Systems: b0 = keyword templates, b1 = Access (paste + one shot), b1d = same with precomputed day counts, agent = tools + reflection,
agent_nr = agent without the reflection pass (ablation).
"""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from refund_triage import baselines
from refund_triage.agent import run_agent
from refund_triage.config import MODEL, RESULTS_DIR
from refund_triage.data import load_tickets
from refund_triage.llm import LLM
from refund_triage.report import write_html
from refund_triage.scoring import score, summarize


def run_one(system: str, ticket: dict, model: str) -> dict:
    if system == "b0":
        return baselines.run_templates(ticket)
    llm = LLM(model)  # fresh usage counter per ticket
    if system == "b1":
        return baselines.run_access(ticket, llm)
    if system == "b1d":
        return baselines.run_access(ticket, llm, derived=True)
    if system == "agent":
        return run_agent(ticket, llm, use_reflection=True)
    if system == "agent_nr":
        return run_agent(ticket, llm, use_reflection=False)
    raise SystemExit(f"unknown system {system}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="b0")
    ap.add_argument("--tickets", default="", help="comma-separated ids; default all")
    ap.add_argument("--set", default="all", choices=["all", "core", "hard"])
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--workers", type=int, default=1, help="1 = sequential, so latency is not distorted by parallel load")
    ap.add_argument("--label", default="")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    tickets = load_tickets()
    if a.set != "all":
        tickets = [t for t in tickets if t.get("set", "core") == a.set]
    if a.tickets:
        keep = set(a.tickets.split(","))
        tickets = [t for t in tickets if t["ticket_id"] in keep]
    systems = a.systems.split(",")
    jobs = [(s, t, r) for s in systems for t in tickets for r in range(a.repeats)]

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + (f"-{a.label}" if a.label else "")
    out_dir = RESULTS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    def work(job):
        s, t, r = job
        rec = run_one(s, t, a.model)
        rec["repeat"] = r
        if a.verbose:
            print(f"{s:9s} {t['ticket_id']} -> {rec['result']['decision']:14s} (expected {t['expected']['decision']}) "
                  f"{rec['latency_s']}s ${rec['usage']['cost_usd']:.5f} {rec['error'] or ''}", flush=True)
        return rec

    t0 = time.perf_counter()
    if a.workers > 1:
        with ThreadPoolExecutor(a.workers) as ex:
            records = list(ex.map(work, jobs))
    else:
        records = [work(j) for j in jobs]
    wall = time.perf_counter() - t0

    with open(out_dir / "records.jsonl", "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = summarize(tickets, records)
    summary["_meta"] = {"run_id": run_id, "model": a.model, "repeats": a.repeats, "n_tickets": len(tickets),
                        "wall_seconds": round(wall, 1)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    write_html(out_dir / "report.html", tickets, records, summary)

    print(f"\nrun {run_id}  model={a.model}  tickets={len(tickets)} repeats={a.repeats}")
    hdr = f"{'system':14s} {'success':>8s} {'decision':>9s} {'wrong$':>6s} {'err':>3s} {'lat mean/p95 s':>15s} {'$/ticket':>9s} {'staff min':>9s}"
    print(hdr)
    for sysname, s in summary.items():
        if sysname.startswith("_") or sysname == "manual":
            continue
        print(f"{sysname:14s} {s['task_success']:8.0%} {s['decision_accuracy']:9.0%} {s['wrong_money_decisions']:6d} {s['errors']:3d} "
              f"{s['latency_mean_s']:>7.2f}/{s['latency_p95_s']:<7.2f} {s['cost_per_ticket_usd']:9.5f} {s['staff_minutes_per_ticket']:9.2f}")
    print(f"{'manual':14s} {'':>8s} {'':>9s} {'':>6s} {'':>3s} {'':>15s} {'':>9s} {summary['manual']['staff_minutes_per_ticket']:9.2f}")
    print(f"\nresults: {out_dir}")


if __name__ == "__main__":
    main()
