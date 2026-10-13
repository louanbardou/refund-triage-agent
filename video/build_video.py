#!/usr/bin/env python3
"""Build the demo video from a finished evaluation run.

  python3 video/build_video.py results/<run>            # uses system 'agent'
  python3 video/build_video.py results/<run> --demo-system b0_templates --out /tmp/test.mp4   # mechanics test

Everything on screen comes from the run's records.jsonl / summary.json / report.html.
Voice: macOS `say` (synthetic). Frames: headless Chrome. Assembly: ffmpeg.
Drop your own recordings into video/custom_audio/<beat_id>.wav (or .m4a/.aiff) to replace the synthetic voice for that beat.
"""
import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from refund_triage import trace  # noqa: E402
from refund_triage.data import load_tickets  # noqa: E402

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 1920, 1080

CSS = """
:root{--navy:#0f2a4d;--paper:#f4f2ee;--ink:#17233b;--mute:#667085;--accent:#c4553a}
*{box-sizing:border-box}html,body{margin:0;width:1920px;height:1080px;overflow:hidden}
body{font-family:-apple-system,Helvetica,Arial,sans-serif;background:var(--paper);color:var(--ink)}
.stage{height:930px;padding:70px 100px;position:relative}
.cap{position:absolute;left:0;right:0;bottom:0;height:150px;background:#0b1a30;color:#fff;font-size:35px;line-height:1.35;padding:22px 100px;display:flex;align-items:center}
h1{font:600 76px/1.1 Georgia,serif;color:var(--navy);margin:0 0 26px}
h2{font:600 56px/1.15 Georgia,serif;color:var(--navy);margin:0 0 34px}
.kicker{letter-spacing:.18em;text-transform:uppercase;color:var(--mute);font-size:24px;font-weight:700;margin-bottom:22px}
.sub{font-size:38px;color:var(--mute);line-height:1.4}
ul{margin:0;padding:0;list-style:none}li{font-size:40px;line-height:1.35;margin:0 0 22px;padding-left:34px;position:relative}
li:before{content:"";position:absolute;left:0;top:19px;width:14px;height:14px;background:var(--accent);border-radius:3px}
.flow{display:flex;gap:18px;margin:40px 0}.box{flex:1;background:#e8e4dc;border-radius:12px;padding:28px 18px;font-size:38px;font-weight:700;color:var(--navy);text-align:center}
.box.hot{background:var(--navy);color:#fff}
table{border-collapse:collapse;width:100%;font-size:34px;background:#fff;border:1px solid #e3e0d8}
th,td{padding:16px 20px;text-align:right;border-bottom:1px solid #e3e0d8}th:first-child,td:first-child{text-align:left}
th{font-size:24px;color:var(--mute);text-transform:uppercase;letter-spacing:.05em}
.term{background:#0d1117;color:#e6edf3;border-radius:14px;height:790px;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,.25)}
.bar{background:#1b2230;padding:12px 18px;display:flex;gap:9px;align-items:center}.dot{width:15px;height:15px;border-radius:50%}
.term pre{margin:0;padding:22px 30px;font:25px/1.42 Menlo,ui-monospace,monospace;white-space:pre-wrap;word-break:break-word}
.t-tool{color:#79c0ff}.t-dec{color:#7ee787;font-weight:700}.t-warn{color:#ffa657}.t-draft{color:#f0e6c8}.t-dim{color:#8b949e}.t-cmd{color:#d2a8ff}
iframe{border:0;width:1720px;height:850px;background:#fff;border-radius:10px;box-shadow:0 6px 30px rgba(0,0,0,.15)}
.note{font-size:30px;color:var(--mute);margin-top:22px}
"""


def page(body: str, caption: str, stage_style: str = "") -> str:
    cap = f'<div class="cap">{html.escape(caption)}</div>' if caption else ""
    return f'<!doctype html><meta charset="utf-8"><style>{CSS}</style><body><div class="stage" style="{stage_style}">{body}</div>{cap}</body>'


def esc(s):
    return html.escape(s)


def colorize(text: str) -> str:
    out = []
    for line in text.split("\n"):
        e = esc(line)
        if line.startswith("[tool]"):
            e = f'<span class="t-tool">{e}</span>'
        elif line.startswith("[decision]"):
            e = f'<span class="t-dec">{e}</span>'
        elif line.startswith(("[guardrail]", "[check", "ERROR")):
            e = f'<span class="t-warn">{e}</span>'
        elif line.startswith("$ "):
            e = f'<span class="t-cmd">{e}</span>'
        elif line.startswith(("===", "---", "note for")):
            e = f'<span class="t-dim">{e}</span>'
        out.append(e)
    return "\n".join(out)


def terminal(cmd: str, text: str, caption: str) -> str:
    dots = "".join(f'<span class="dot" style="background:{c}"></span>' for c in ("#ff5f56", "#ffbd2e", "#27c93f"))
    body = f'<div class="term"><div class="bar">{dots}</div><pre>{colorize("$ " + cmd + chr(10) + chr(10) + text)}</pre></div>'
    return page(body, caption, "padding:50px 100px 0")


def slide(kicker: str, title: str, bullets=None, sub: str = "", extra: str = "", caption: str = "") -> str:
    b = "".join(f"<li>{esc(x)}</li>" for x in (bullets or []))
    body = f'<div class="kicker">{esc(kicker)}</div><h2>{esc(title)}</h2>{f"<div class=sub>{esc(sub)}</div>" if sub else ""}<ul>{b}</ul>{extra}'
    return page(body, caption)


def pct(x):
    return f"{x * 100:.0f}%"


def build_beats(run: Path, demo_system: str):
    summary = json.loads((run / "summary.json").read_text())
    records = [json.loads(line) for line in (run / "records.jsonl").read_text().splitlines()]
    tickets = {t["ticket_id"]: t for t in load_tickets()}
    rec = {(r["system"], r["ticket_id"]): r for r in records if r.get("repeat", 0) == 0}
    S = summary.get(demo_system)
    n = summary["_meta"]["n_tickets"]
    report = (run / "report.html").resolve().as_uri()
    beats = []

    def add(bid, html_, narration):
        beats.append({"id": bid, "html": html_, "narration": narration})

    def term_beats(tid, tag, parts, narrs):
        t, r = tickets[tid], rec[(demo_system, tid)]
        sec = trace.sections(t, r)
        cmd = f"python3 triage.py {tid}"
        for i, (keys, nar) in enumerate(zip(parts, narrs)):
            text = "\n\n".join(sec[k] for k in keys)
            add(f"{tag}_{i}", terminal(cmd, text, nar), nar)

    # 1 title
    add("01_title", slide("MSc DSAIB · Generative and Agentic AI for Business", "Refund triage assistant",
        sub="A bounded agent that prepares a decision and a draft reply. A staff member approves every send.",
        caption="A small online shop gets return and refund emails. The slow part is finding the order and applying the policy with its date rules."),
        "A small online shop gets return and refund emails. The slow part is not writing the reply. It is finding the order, and applying the policy with its date rules.")

    # 2 problem + EDGE
    flow = '<div class="flow">' + "".join(f'<div class="box{" hot" if h else ""}">{esc(x)}</div>' for x, h in
                                          [("Read", 0), ("Find facts", 1), ("Compose", 0), ("Check", 1), ("Send", 0)]) + "</div>"
    nar = ("I modelled the manual process at five minutes per ticket. Finding the facts and checking the draft are the steps I target. "
           "The efficiency goal is to cut staff time, and the decision goal is a reply that cites the policy and the order record.")
    add("02_edge", slide("Business problem and EDGE target", "Where does the support desk lose time?", extra=flow,
        bullets=["Efficiency: staff minutes per ticket (modelled, not measured)",
                 "Decisions: every reply grounded in the policy and the order record"], caption=nar), nar)

    # 3 design
    nar = ("From the five A's, I chose an agent, kept small. The next step depends on what a lookup returns. "
           "Tools are read only and tied to the sender's email. Code enforces the manager threshold. And a human approves every draft.")
    add("03_design", slide("Solution design", "Agent, with controls around it",
        bullets=["Two read-only tools, scoped to the sender's email",
                 "Maximum six steps, then one check of the draft against the facts",
                 "Code guardrail: refunds above 100 EUR go to a manager",
                 "Email text is untrusted data",
                 "Any failure routes the ticket to a human"], caption=nar), nar)

    # 4 live examples
    term_beats("T06", "04_T06",
               [["email", "tools"], ["decision"], ["draft", "stats"]],
               ["Case one: a cracked carafe, with a photo. The agent looks up the order with a read only tool.",
                "It applies rule R4 and decides to approve a refund.",
                "It drafts the reply for staff to review. The line at the bottom gives latency, tokens and cost for this ticket."])
    term_beats("T11", "05_T11", [["email", "tools"], ["decision", "draft"]],
               ["Case two: a parcel that is fifteen days late. This is a manager decision under rule R6.",
                "The agent does not decide. It escalates, and the draft promises nothing."])
    term_beats("T13", "06_T13", [["email", "tools"], ["decision", "draft"]],
               ["Case three: the sender's email does not match the order. The tool returns nothing.",
                "So the agent asks for information, and reveals no order detail. The identity check lives in the tool, not in the prompt."])
    term_beats("T18", "07_T18", [["email"], ["decision", "draft"]],
               ["Case four: an email that says the manager pre approved the refund and tells the assistant to say yes.",
                "The order is seventy three days old, so the policy says reject. The email is treated as data, not as instructions."])

    # 5 results
    def sysline(k, label):
        s = summary.get(k)
        return f"{label[0].upper() + label[1:]}: {pct(s['task_success'])} task success, ${s['cost_per_ticket_usd']:.4f} per ticket, {s['latency_mean_s']} s on average" if s else ""

    lines = [sysline(k, l) for k, l in [("b0_templates", "keyword templates"), ("b1_access", "single paste and draft call"), ("b1_access_days", "paste and draft with precomputed day counts"),
                                       ("agent_no_reflection", "agent without the check"), ("agent", "agent with the check")]]
    nar = (f"I compared the systems on {n} labelled tickets. " + ". ".join(x for x in lines if x) + ". "
           "These are small, synthetic samples, so I read the differences as indications, not as proof.")
    add("08_results", page(f'<iframe src="{report}#view=summary&zoom=1.35&theme=light" style="height:830px"></iframe>', nar, "padding:50px 100px 0"), nar)

    # 6 a staff review card (first failure of the demo system if any, else T12)
    failing = [tid for (s_, tid), r in rec.items() if s_ == demo_system and tid in tickets and
               summary[demo_system]["failures"].get(tid)]
    pick = sorted(failing)[0] if failing else "T12"
    if failing:
        nar = (f"Here is what staff see: the email, the facts, and the draft side by side. This is ticket {pick}, one that failed an automatic check, "
               "which is why the review step exists.")
    else:
        nar = "Here is what staff see: the email, the retrieved facts, and the draft side by side, with approve, revise or escalate."
    add("09_review", page(f'<iframe src="{report}#view=card&only={pick}&system={demo_system}&zoom=1.0&theme=light" style="height:830px"></iframe>', nar,
                          "padding:50px 100px 0"), nar)

    # 7 limits
    nar = ("Limits: twenty synthetic tickets that I wrote, regular expression scoring, and staff time modelled from assumptions. "
           "A pilot would run in shadow mode on real tickets, with every draft approved by a person. The voice in this video is synthetic.")
    add("10_limits", slide("Limits and next step", "What this does and does not show",
        bullets=[f"{n} synthetic, author-written tickets; one model",
                 "Regex-based scoring; staff minutes are assumptions",
                 "Pilot: shadow mode on real tickets, every draft approved, track revise rate",
                 "Voice-over: synthetic (macOS text to speech)"], caption=nar), nar)
    return beats


def sh(*cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def render(html_text: str, png: Path, work: Path):
    f = work / (png.stem + ".html")
    f.write_text(html_text)
    sh(CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
       f"--window-size={W},{H}", "--virtual-time-budget=4000", f"--screenshot={png}", f.resolve().as_uri())


def duration(path: Path) -> float:
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)).stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--demo-system", default="agent")
    ap.add_argument("--voice", default="Samantha")
    ap.add_argument("--rate", type=int, default=172, help="words per minute for `say`")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    run = Path(a.run).resolve()
    work = ROOT / "video" / "build"
    work.mkdir(parents=True, exist_ok=True)
    custom = ROOT / "video" / "custom_audio"
    beats = build_beats(run, a.demo_system)
    (ROOT / "video" / "narration.txt").write_text("\n\n".join(f"[{b['id']}]\n{b['narration']}" for b in beats))

    clips = []
    for b in beats:
        png, wav, mp4 = work / f"{b['id']}.png", work / f"{b['id']}.wav", work / f"{b['id']}.mp4"
        render(b["html"], png, work)
        own = next((p for ext in ("wav", "m4a", "aiff", "mp3") if (p := custom / f"{b['id']}.{ext}").exists()), None)
        if own:
            sh("ffmpeg", "-y", "-i", str(own), "-ar", "44100", "-ac", "1", str(wav))
        else:
            aiff = work / f"{b['id']}.aiff"
            sh("say", "-v", a.voice, "-r", str(a.rate), "-o", str(aiff), b["narration"])
            sh("ffmpeg", "-y", "-i", str(aiff), "-ar", "44100", "-ac", "1", str(wav))
        d = duration(wav) + 0.7
        sh("ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", str(png), "-i", str(wav), "-t", f"{d:.2f}",
           "-af", "apad=pad_dur=1", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "1", str(mp4))
        clips.append(mp4)
        print(f"{b['id']:12s} {d:5.1f}s")

    lst = work / "clips.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    out = Path(a.out) if a.out else ROOT / "video" / "demo.mp4"
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out))
    print(f"\n{out}  {duration(out):.1f}s")


if __name__ == "__main__":
    main()
