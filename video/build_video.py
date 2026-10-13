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
    n = summary["_meta"]["n_tickets"]
    site = (ROOT / "docs" / "index.html").resolve().as_uri()
    beats = []

    def add(bid, html_, narration):
        beats.append({"id": bid, "html": html_, "narration": narration})

    PLAT = [250, 600, 950, 1300, 1650, 2000, 2350, 2700, 3100, 3600, 4300, 9000]   # virtual-time stops: steps tick, draft types
    BARS = [150, 450, 800, 1400, 9000]

    def frame(hash_, caption, z=1.0, h=840, wait=9000, anim=None):
        return {"html": page(f'<iframe src="{site}#{hash_}&clean=1&z={z}" style="height:{h}px;width:1720px"></iframe>', caption, "padding:40px 100px 0"), "wait": wait, "anim": anim}

    # the story must match the data: fail the build instead of narrating something untrue
    expect = {"T06": "approve_refund", "T11": "escalate", "T13": "ask_info", "T18": "reject"}
    for tid, dec in expect.items():
        got = rec[(demo_system, tid)]["result"]["decision"]
        assert got == dec, f"narration assumes {tid} -> {dec}, but {demo_system} produced {got}"

    llm = [k for k in summary if k not in ("manual", "_meta", "b0_templates") and not k.startswith("_")]
    ks = [round(summary[k]["task_success"] * n) for k in llm]
    lo, hi = min(ks), max(ks)
    A, B1 = summary.get("agent"), summary.get("b1_access")
    fails = sorted({t for k in llm for t in summary[k]["failures"]})

    # 1 title
    nar = ("A small online shop gets return and refund emails. The slow part is not writing the reply. "
           "It is finding the order and applying the policy with its date rules. This is a bounded agent that drafts the reply, and a person decides.")
    add("01_title", slide("MSc DSAIB · Generative and Agentic AI for Business", "Refund triage agent",
                          sub="Drafts a decision and a reply. A staff member approves every send.", caption=nar), nar)

    # 2 overview from the site
    nar = ("The agent reads the email, looks up the order with read only tools, applies nine policy rules, and checks its own draft against the facts. "
           "Tools are tied to the sender's email, refunds above one hundred euros go to a manager, and any failure goes to a person.")
    f = frame("overview", nar, 1.12)
    add("02_overview", f["html"], nar); beats[-1]["wait"] = f["wait"]

    # 3 terminal trace T06
    t = tickets["T06"]; sec = trace.sections(t, rec[(demo_system, "T06")])
    cmd = "python3 triage.py T06"
    for i, (keys, nr) in enumerate(zip([["email", "tools"], ["decision"], ["draft", "stats"]],
                                      ["Case one: a cracked carafe, with a photo. The agent looks up the order with a read only tool.",
                                       "It applies rule four and decides to approve a refund.",
                                       "It drafts the reply for staff to review. The last line gives latency, tokens and cost for this ticket."])):
        add(f"03_T06_{i}", terminal(cmd, "\n\n".join(sec[k] for k in keys), nr), nr)

    # 4 staff platform cases
    for tid, tag, nr in [("T11", "04_T11", "Case two, in the staff platform: a parcel fifteen days late. This is a manager decision, so the agent escalates and the draft promises nothing."),
                         ("T13", "05_T13", "Case three: the sender's email does not match the order, so the tool returns nothing. The agent asks for information and reveals no order detail."),
                         ("T18", "06_T18", "Case four: an email claims the manager pre approved the refund and tells the assistant to say yes. The order is seventy three days old, so the policy says reject. The email is treated as data.")]:
        f = frame(f"platform&t={tid}&e={demo_system}&anim=1", nr, 1.0, anim=PLAT)
        add(tag, f["html"], nr); beats[-1]["wait"] = f["wait"]; beats[-1]["anim"] = f["anim"]

    # 5 results
    b0 = summary["b0_templates"]["task_success"]
    nar = (f"I compared five systems on {n} labelled tickets. Keyword templates pass {round(b0*100)} percent. "
           f"The model based systems pass {lo if lo == hi else str(lo) + ' to ' + str(hi)} of {n}, so at this scale accuracy does not separate them.")
    f = frame("results", nar, 1.0, anim=BARS); add("07_results_a", f["html"], nar); beats[-1]["wait"] = f["wait"]; beats[-1]["anim"] = f["anim"]
    if A and B1:
        nar = (f"The difference is modelled staff time: about {A['staff_minutes_per_ticket']:.1f} minute per ticket with the agent, against {B1['staff_minutes_per_ticket']:.1f} pasting the order by hand. "
               f"That rests on an assumed lookup time. The agent costs about {A['cost_per_ticket_usd']/B1['cost_per_ticket_usd']:.1f} times as much per ticket, and is slower.")
        f = frame("results&sc=c-cost", nar, 1.0); add("08_results_b", f["html"], nar); beats[-1]["wait"] = f["wait"]
    if fails == ["T30"]:
        nar = ("Each cell in this map is one ticket. The only failure among the model systems is ticket thirty, where the label itself is ambiguous. Escalating to verify a claimed authorisation is also defensible.")
    else:
        nar = "Each cell is one ticket. I read every failure; the map shows which system failed which ticket."
    f = frame("results&sc=heatcard", nar, 1.0); add("09_heat", f["html"], nar); beats[-1]["wait"] = f["wait"]

    # 6 limits
    nar = ("Limits: thirty one synthetic tickets that I wrote, deterministic checks, and staff time modelled from assumptions. "
           "The data supports that model systems beat keyword templates. It does not show the agent is more accurate than pasting the order into a chat. "
           "A pilot would run in shadow mode on real tickets, with every draft approved by a person. The voice in this video is synthetic.")
    add("10_limits", slide("Limits and next step", "What this does and does not show",
                           bullets=[f"{n} synthetic, author-written tickets; one small model",
                                    "Deterministic checks; staff minutes are assumptions",
                                    "Model systems beat templates; the agent is not shown more accurate than paste",
                                    "Pilot: shadow mode, every draft approved by a person",
                                    "Voice-over: synthetic (text to speech)"], caption=nar), nar)
    return beats


def sh(*cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def render(html_text: str, png: Path, work: Path, wait: int = 4000):
    f = work / (png.stem + ".html")
    f.write_text(html_text)
    sh(CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
       f"--window-size={W},{H}", f"--virtual-time-budget={wait}", f"--screenshot={png}", f.resolve().as_uri())


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
        stops = b.get("anim")
        if stops:
            seq = []
            for k, w in enumerate(stops):
                pk = work / f"{b['id']}_f{k:02d}.png"
                render(b["html"], pk, work, w)
                seq.append(pk)
            png = seq[-1]
        else:
            render(b["html"], png, work, b.get("wait", 4000))
        own = next((p for ext in ("wav", "m4a", "aiff", "mp3") if (p := custom / f"{b['id']}.{ext}").exists()), None)
        if own:
            sh("ffmpeg", "-y", "-i", str(own), "-ar", "44100", "-ac", "1", str(wav))
        else:
            aiff = work / f"{b['id']}.aiff"
            sh("say", "-v", a.voice, "-r", str(a.rate), "-o", str(aiff), b["narration"])
            sh("ffmpeg", "-y", "-i", str(aiff), "-ar", "44100", "-ac", "1", str(wav))
        d = duration(wav) + 0.7
        if stops:
            hold = 0.42
            lines = "".join(f"file '{p_.resolve()}'\nduration {hold}\n" for p_ in seq[:-1])
            lines += f"file '{seq[-1].resolve()}'\nduration {max(d - hold * (len(seq) - 1), 1.0):.2f}\nfile '{seq[-1].resolve()}'\n"
            (work / f"{b['id']}_frames.txt").write_text(lines)
            sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(work / f"{b['id']}_frames.txt"), "-i", str(wav), "-t", f"{d:.2f}",
               "-af", "apad=pad_dur=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
               "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "1", str(mp4))
            clips.append(mp4)
            print(f"{b['id']:12s} {d:5.1f}s  ({len(seq)} animation frames)")
            continue
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
