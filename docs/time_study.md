# Optional: replace the staff-time assumptions with a measurement (about 15 minutes)

The staff-minute figures in the results are modelled from assumptions in `refund_triage/config.py`
(`MANUAL_MINUTES`, `REVIEW_MINUTES_APPROVE`, `REVIEW_MINUTES_REVISE`). They are the weakest number in the
evidence, so a small stopwatch measurement makes the efficiency claim much stronger.

Protocol (you are the support agent):

1. Pick 5 tickets from `data/tickets.json` (suggested: T01, T03, T06, T10, T16).
2. **Manual condition.** For each, with a stopwatch: read the email, open `data/orders.json` and find the order, check
   `data/policy.md`, type the reply (in a text editor), stop. Record seconds.
3. **Assisted condition.** Open `results/<run>/report.html`. For each of the same tickets: read the draft beside the
   facts, decide Approve or Revise (fix the text if needed), stop. Record seconds. Do this on a different day, or after
   several other tickets, so you do not just remember the answers.
4. Put the means into `config.py`: set `MANUAL_MINUTES` to a single number split across the keys, and
   `REVIEW_MINUTES_APPROVE` / `REVIEW_MINUTES_REVISE` to the assisted means for approved / revised drafts.
5. Re-run `python3 run_eval.py ...` (or just re-summarize) and state in the rationale that these are n=5 single-person timings.
