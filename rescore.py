#!/usr/bin/env python3
"""Re-score an existing run with the current scoring code. No model calls.
Keeps the previous summary as summary_<n>.json so scoring changes stay visible.

  python3 rescore.py results/<run>
"""
import json
import shutil
import sys
from pathlib import Path

from refund_triage.data import load_tickets
from refund_triage.report import write_html
from refund_triage.scoring import summarize

run = Path(sys.argv[1])
records = [json.loads(line) for line in (run / "records.jsonl").read_text().splitlines()]
old = json.loads((run / "summary.json").read_text())
n = 1
while (run / f"summary_v{n}.json").exists():
    n += 1
shutil.copy(run / "summary.json", run / f"summary_v{n}.json")
new = summarize(load_tickets(), records)
new["_meta"] = {**old["_meta"], "rescored": f"scoring revision after v{n}"}
(run / "summary.json").write_text(json.dumps(new, indent=2, ensure_ascii=False))
write_html(run / "report.html", load_tickets(), records, new)
for k, v in new.items():
    if not k.startswith("_") and k != "manual":
        print(f"{k:22s} success {v['task_success']:.0%} CI{v['task_success_ci95']}  fails {v['failures']}")
