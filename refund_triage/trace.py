"""Human-readable trace of one agent run. Shared by triage.py and the video builder so the
video shows exactly what the command line prints."""
import json


def sections(ticket: dict, rec: dict) -> dict:
    r = rec["result"]
    email = f"=== {ticket['ticket_id']}  from {ticket['from_email']}\n{ticket['body']}"
    tools = "\n".join(
        f"[tool] {tc['tool']}({json.dumps(tc['input'])}) -> {json.dumps(tc['output'], ensure_ascii=False)[:300]}"
        for tc in rec["tool_calls"]) or "[no tool calls]"
    dec = f"[decision] {r['decision']}  rules={r['rules_cited']}  amount={r['refund_amount']}"
    for note in rec["guardrail_notes"]:
        dec += f"\n[guardrail] {note}"
    if rec.get("reflection") and rec["reflection"].get("ok") is False:
        dec += f"\n[check revised the draft] {rec['reflection']['issues']}"
    draft = f"--- DRAFT (staff must approve before sending) ---\n{r['draft_reply']}\n---\nnote for reviewer: {r['internal_note']}"
    u = rec["usage"]
    stats = (f"{rec['latency_s']}s, {u['llm_calls']} model calls, {u['input_tokens']} in / {u['output_tokens']} out tokens, "
             f"${u['cost_usd']:.5f}")
    if rec["error"]:
        stats += f"\nERROR: {rec['error']}"
    return {"email": email, "tools": tools, "decision": dec, "draft": draft, "stats": stats}
