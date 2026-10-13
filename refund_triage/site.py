"""Generate the public project site (GitHub Pages) from a finished evaluation run.

  python3 -m refund_triage.site results/<run> [--video video/demo.mp4] [--preliminary] [--out docs]

Writes docs/index.html (+ docs/data/results.json, docs/demo.mp4, docs/.nojekyll). Static: no server, no API key.
"""
import argparse
import json
import shutil
from pathlib import Path

from .config import ROOT
from .data import load_tickets
from .report import build_data

REPO = "https://github.com/louanbardou/refund-triage-agent"

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Refund Triage Agent</title>
<meta name="description" content="A bounded support agent that prepares a decision and a draft reply for staff review. MSc DSAIB course project, synthetic data.">
<style>
:root{--bg:#fafaf9;--panel:#fff;--ink:#14213d;--mute:#5b6577;--line:#e7e5e0;--brand:#2b59c3;--brand-ink:#fff;--ok:#16794c;--bad:#b3261e;--warn:#9a6700;--soft:#f1f0ec;--code:#0f1623;--codeink:#e6edf3;
--c-approve_refund:#16794c;--c-store_credit:#2b59c3;--c-reject:#b3261e;--c-ask_info:#9a6700;--c-escalate:#7a46b8}
@media (prefers-color-scheme:dark){:root{--bg:#0e131c;--panel:#161d2a;--ink:#e9eef7;--mute:#9aa6bb;--line:#263042;--brand:#7da3ff;--brand-ink:#0e131c;--soft:#1c2535;--ok:#4cc38a;--bad:#ff7b72;--warn:#e3b341;--code:#0a0e16}}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:72px}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--brand);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
nav{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
nav .wrap{display:flex;align-items:center;gap:22px;height:58px}
nav .logo{font-weight:700;letter-spacing:-.01em;color:var(--ink)}nav .logo span{color:var(--brand)}
nav .links{display:flex;gap:4px;margin-left:auto;flex-wrap:wrap}
nav .links a{color:var(--mute);padding:6px 10px;border-radius:8px;font-size:14px}nav .links a:hover{background:var(--soft);color:var(--ink);text-decoration:none}
nav .gh{border:1px solid var(--line);color:var(--ink)!important}
section{padding:72px 0 8px}
.eyebrow{font-size:12.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--brand)}
h1{font-size:clamp(34px,5.4vw,56px);line-height:1.08;letter-spacing:-.03em;margin:14px 0 18px}
h2{font-size:clamp(26px,3.4vw,34px);letter-spacing:-.02em;margin:8px 0 10px}
h3{font-size:17px;margin:0 0 6px}
p.lead{font-size:clamp(17px,2vw,20px);color:var(--mute);max-width:720px;margin:0 0 26px}
.sub{color:var(--mute);max-width:720px;margin:0 0 24px}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px}
.tag{font-size:13px;padding:4px 11px;border:1px solid var(--line);border-radius:999px;color:var(--mute);background:var(--panel)}
.banner{background:color-mix(in srgb,var(--warn) 14%,var(--panel));border:1px solid color-mix(in srgb,var(--warn) 45%,var(--line));color:var(--ink);border-radius:12px;padding:12px 16px;margin:22px 0 0;font-size:14.5px}
.btns{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 34px}
.btn{display:inline-block;padding:10px 18px;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--ink);font-weight:600;font-size:15px}
.btn.primary{background:var(--brand);color:var(--brand-ink);border-color:var(--brand)}.btn:hover{text-decoration:none;filter:brightness(.97)}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
.tile .v{font-size:32px;font-weight:700;letter-spacing:-.02em;line-height:1.1}.tile .l{color:var(--mute);font-size:13.5px;margin-top:6px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}
.card p,.card li{color:var(--mute);font-size:15px;margin:0}.card ul{margin:8px 0 0;padding-left:18px}.card li{margin:4px 0}
.flow{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0 26px}
.step{flex:1;min-width:120px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.step b{display:block;font-size:12px;color:var(--brand);letter-spacing:.1em;text-transform:uppercase}.step span{font-size:15px}
.step.hl{background:var(--ink);color:var(--bg);border-color:var(--ink)}.step.hl b{color:var(--bg);opacity:.7}
.tablewrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:14px}
table{border-collapse:collapse;width:100%;min-width:760px;font-size:14.5px}
th,td{padding:12px 14px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}th:first-child,td:first-child{text-align:left}
th{font-size:12px;color:var(--mute);text-transform:uppercase;letter-spacing:.06em;font-weight:600}tr:last-child td{border-bottom:0}
.bar{display:inline-block;vertical-align:middle;width:90px;height:8px;background:var(--soft);border-radius:99px;margin-right:8px;overflow:hidden}.bar i{display:block;height:100%;background:var(--brand)}
.note{color:var(--mute);font-size:14px;margin-top:12px;max-width:820px}
.explorer{display:grid;grid-template-columns:300px 1fr;gap:14px;align-items:start}
.pane{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.pane .top{padding:12px;border-bottom:1px solid var(--line);display:flex;gap:8px;flex-wrap:wrap}
select{font:inherit;padding:8px 10px;border-radius:9px;border:1px solid var(--line);background:var(--bg);color:var(--ink);width:100%}
.list{max-height:640px;overflow:auto}
.item{display:flex;gap:10px;align-items:center;width:100%;text-align:left;border:0;border-bottom:1px solid var(--line);background:transparent;color:var(--ink);padding:10px 14px;cursor:pointer;font:inherit;font-size:14px}
.item:hover{background:var(--soft)}.item.on{background:var(--soft);box-shadow:inset 3px 0 0 var(--brand)}
.dot{width:9px;height:9px;border-radius:50%;flex:none}.item small{color:var(--mute);margin-left:auto}
.badge{display:inline-block;padding:2px 10px;border-radius:99px;color:#fff;font-size:12.5px;font-weight:600}
.detail{padding:20px}.detail h3{margin:0}.meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0 18px}
.pill{font-size:12.5px;border:1px solid var(--line);border-radius:7px;padding:1px 8px;color:var(--mute)}
.blk{margin:0 0 16px}.blk .k{font-size:12px;text-transform:uppercase;letter-spacing:.09em;color:var(--mute);font-weight:700;margin-bottom:6px}
.box{background:var(--soft);border-radius:10px;padding:12px 14px;white-space:pre-wrap;word-break:break-word;font-size:14.5px}
.mono{font:12.5px/1.5 ui-monospace,Menlo,Consolas,monospace}
.checks{display:flex;gap:6px;flex-wrap:wrap}.chip{font-size:12.5px;border-radius:7px;padding:2px 9px;border:1px solid var(--line)}
.chip.p{color:var(--ok)}.chip.f{color:var(--bad);border-color:var(--bad);font-weight:600}
.act{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}.act button{font:inherit;font-size:14px;padding:7px 14px;border-radius:9px;border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer}
.act button.p{background:var(--brand);color:var(--brand-ink);border-color:var(--brand)}
video{width:100%;border-radius:14px;border:1px solid var(--line);background:#000}
.soon{background:var(--panel);border:1px dashed var(--line);border-radius:14px;padding:36px;text-align:center;color:var(--mute)}
pre.code{background:var(--code);color:var(--codeink);border-radius:12px;padding:16px 18px;overflow:auto;font:13.5px/1.6 ui-monospace,Menlo,Consolas,monospace;margin:0}
footer{margin-top:90px;border-top:1px solid var(--line);padding:26px 0 60px;color:var(--mute);font-size:14px}
@media (max-width:860px){.tiles{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}.explorer{grid-template-columns:1fr}.list{max-height:260px}nav .links a:not(.gh){display:none}}
</style></head><body>
<nav><div class="wrap"><a class="logo" href="#top">Refund<span>Triage</span></a>
<div class="links"><a href="#design">Design</a><a href="#results">Results</a><a href="#explorer">Explorer</a><a href="#video">Video</a><a href="#run">Run it</a><a class="gh" href="__REPO__">GitHub</a></div></div></nav>

<main class="wrap" id="top">
<section style="padding-top:64px">
 <div class="tags"><span class="tag">MSc DSAIB · HEC Paris</span><span class="tag">Generative and Agentic AI for Business</span><span class="tag">Synthetic data</span></div>
 <h1>A support agent that drafts.<br>A person who decides.</h1>
 <p class="lead">A bounded agent reads a customer email, looks up the order with read-only tools, applies a written returns policy, and prepares a decision and a draft reply. A staff member reviews every draft. Nothing is sent automatically.</p>
 <div class="btns"><a class="btn primary" href="#explorer">Explore the tickets</a><a class="btn" href="#results">See the results</a><a class="btn" href="__REPO__">Source code</a></div>
 __BANNER__
 <div class="tiles" id="tiles" style="margin-top:26px"></div>
</section>

<section id="design">
 <div class="eyebrow">Design</div><h2>From a business problem to an agent</h2>
 <p class="sub">A fictional shop, Nordlys Home, receives return, cancellation and refund emails. Finding the order and applying date-dependent rules is the slow part, so the design targets that step.</p>
 <div class="flow">
  <div class="step"><b>1 · Read</b><span>Customer email, any language</span></div>
  <div class="step hl"><b>2 · Look up</b><span>Order record, day counts</span></div>
  <div class="step hl"><b>3 · Decide</b><span>Policy rules R1–R9</span></div>
  <div class="step hl"><b>4 · Check</b><span>Draft vs facts</span></div>
  <div class="step"><b>5 · Staff review</b><span>Approve, revise or escalate</span></div>
 </div>
 <div class="grid">
  <div class="card"><h3>Why an agent</h3><p>The next step depends on what a lookup returns: no order id, an order that is not the sender's, a shipped versus a delivered order. That is the test for an agent in the course's five-A menu. Automation and plain assistants were considered and compared against.</p></div>
  <div class="card"><h3>Controls</h3><ul><li>Two read-only tools, bound to the sender's email in code</li><li>Day counts computed by the tool, not the model</li><li>Max 6 steps, then one check of the draft</li><li>Refunds above 100 EUR cannot be approved by the agent</li><li>Email text is treated as untrusted data</li><li>Any failure routes to a human</li></ul></div>
  <div class="card"><h3>Systems compared</h3><ul><li><b>B0</b> keyword templates</li><li><b>B1</b> paste email, order, policy; one call</li><li><b>B1d</b> same, with precomputed day counts</li><li><b>Agent, no check</b> tools and loop</li><li><b>Agent</b> tools, loop and check</li></ul></div>
 </div>
 <p class="note">EDGE targets: <b>Efficiency</b> (staff minutes per ticket, modelled from assumptions, not measured) and <b>Decisions</b> (every reply grounded in the policy and the order record).</p>
</section>

<section id="results">
 <div class="eyebrow">Results</div><h2>Five systems, one ticket set</h2>
 <p class="sub" id="resultsub"></p>
 <div class="tablewrap"><table id="restable"></table></div>
 <p class="note">A ticket is a success only if the decision, cited rules, amount, language, claims and leak checks all pass. Checks are deterministic (regex and rules, no LLM judge), so they are reproducible but blunt. Intervals are 95% Wilson; with this few tickets they are wide. Staff minutes are modelled from assumed step times.</p>
 <div id="interp"></div>
</section>

<section id="explorer">
 <div class="eyebrow">Explorer</div><h2>What staff would see</h2>
 <p class="sub">Pick a system and a ticket: the customer email, the facts the system used, the draft reply, and the automatic checks. The buttons are a simulation; nothing is sent.</p>
 <div class="explorer">
  <div class="pane"><div class="top"><select id="sys"></select></div><div class="list" id="list"></div></div>
  <div class="pane detail" id="detail"></div>
 </div>
</section>

<section id="video">
 <div class="eyebrow">Demo</div><h2>Demo video</h2>
 __VIDEO__
</section>

<section id="run">
 <div class="eyebrow">Run it</div><h2>Reproduce everything</h2>
 <p class="sub">Python 3.10+ and <code>pip install anthropic</code>. Offline tests and the template baseline need no API key.</p>
<pre class="code">git clone __REPO__.git && cd refund-triage-agent
python3 -m unittest discover -s tests -t .      # offline checks
python3 run_eval.py --systems b0                # offline baseline

export ANTHROPIC_API_KEY=...                    # live runs
python3 triage.py T06                           # one ticket, full trace
python3 run_eval.py --systems b0,b1,b1d,agent_nr,agent --label main
python3 -m refund_triage.site results/&lt;run&gt; --out docs   # rebuild this site</pre>
 <p class="note"><b>Limits.</b> Author-written synthetic tickets, hand-labelled and cross-checked with a rule-based oracle; one small model (<code>claude-haiku-5-5</code>); regex-based scoring; modelled staff time; a short, unambiguous policy. The results suggest the design is feasible on clean cases. They do not show it would hold on a real inbox. A pilot would run in shadow mode with every draft approved by a person.</p>
</section>
</main>
<footer><div class="wrap">Course project, MSc Data Science and AI for Business, HEC Paris. All data is fictional. Built with Claude Code. <a href="__REPO__">Repository</a> · <span id="runid"></span></div></footer>

<script>
const D=__DATA__;
const $=id=>document.getElementById(id),el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
const LAB={b0_templates:'B0 · Keyword templates',b1_access:'B1 · Paste + one call',b1_access_days:'B1d · Paste + day counts',agent_no_reflection:'Agent · no check',agent:'Agent · with check'};
const DEC={approve_refund:'Approve refund',store_credit:'Store credit',reject:'Reject',ask_info:'Ask for info',escalate:'Escalate'};
const pct=x=>Math.round(x*100)+'%',lab=s=>LAB[s]||s;
const S=D.summary,order=['b0_templates','b1_access','b1_access_days','agent_no_reflection','agent'].filter(s=>S[s]);
const best=S.agent||S[order[order.length-1]],bk=S.agent?'agent':order[order.length-1];
$('runid').textContent='run '+D.summary._meta.run_id+' · '+D.summary._meta.model;

// tiles
[[pct(best.task_success),'Task success, '+lab(bk).split(' · ')[0]],['$'+best.cost_per_ticket_usd.toFixed(4),'Model cost per ticket'],[best.latency_mean_s+' s','Mean latency per ticket'],[best.staff_minutes_per_ticket.toFixed(1)+' min','Modelled staff time (manual: '+S.manual.staff_minutes_per_ticket.toFixed(1)+')']]
 .forEach(([v,l])=>{const t=el('div','tile');t.appendChild(el('div','v',v));t.appendChild(el('div','l',l));$('tiles').appendChild(t)});

// results table
const n=D.summary._meta.n_tickets;
$('resultsub').textContent=n+' labelled tickets'+(D.summary._meta.repeats>1?' × '+D.summary._meta.repeats+' repeats':'')+', model '+D.summary._meta.model+'. Each system produces a decision and a draft; the same deterministic checks score all of them.';
const tb=$('restable'),hr=el('tr');['System','Task success','95% CI','Decision acc.','Wrong-money decisions','Latency mean / p95','Cost / ticket','Staff min / ticket'].forEach(h=>hr.appendChild(el('th','',h)));tb.appendChild(hr);
order.forEach(s=>{const m=S[s],r=el('tr');r.appendChild(el('td','',lab(s)));
 const c=el('td');const bar=el('span','bar');bar.appendChild(Object.assign(el('i'),{}));bar.firstChild.style.width=pct(m.task_success);c.appendChild(bar);c.appendChild(document.createTextNode(pct(m.task_success)));r.appendChild(c);
 r.appendChild(el('td','',Math.round(m.task_success_ci95[0]*100)+'–'+Math.round(m.task_success_ci95[1]*100)+'%'));
 r.appendChild(el('td','',pct(m.decision_accuracy)));r.appendChild(el('td','',m.wrong_money_decisions));
 r.appendChild(el('td','',m.latency_mean_s+' / '+m.latency_p95_s+' s'));r.appendChild(el('td','','$'+m.cost_per_ticket_usd.toFixed(4)));r.appendChild(el('td','',m.staff_minutes_per_ticket.toFixed(2)));tb.appendChild(r)});
const mr=el('tr');mr.appendChild(el('td','','Fully manual (assumed)'));for(let i=0;i<6;i++)mr.appendChild(el('td','',''));mr.appendChild(el('td','',S.manual.staff_minutes_per_ticket.toFixed(2)));tb.appendChild(mr);
if(D.interpretation){const p=el('p','note');p.textContent=D.interpretation;$('interp').appendChild(p)}

// explorer
let cur=S.agent?'agent':order[0],sel=null;
const so=$('sys');order.forEach(s=>{const o=el('option','',lab(s));o.value=s;so.appendChild(o)});so.value=cur;so.onchange=()=>{cur=so.value;sel=null;list()};
const rows=()=>D.rows.filter(r=>r.system===cur);
function list(){const L=$('list');L.textContent='';const rs=rows();if(!sel||!rs.find(r=>r.ticket_id===sel))sel=rs[0].ticket_id;
 rs.forEach(r=>{const b=el('button','item'+(r.ticket_id===sel?' on':''));const d=el('span','dot');d.style.background=r.score.success?'var(--ok)':'var(--bad)';b.appendChild(d);
  b.appendChild(el('span','',r.ticket_id+' · '+D.tickets[r.ticket_id].subject.slice(0,26)));b.appendChild(el('small','',DEC[r.result.decision]||r.result.decision));b.onclick=()=>{sel=r.ticket_id;list()};L.appendChild(b)});show()}
function show(){const r=rows().find(x=>x.ticket_id===sel),t=D.tickets[sel],x=r.result,P=$('detail');P.textContent='';
 P.appendChild(el('h3','',sel+' · '+t.subject));const meta=el('div','meta');const bd=el('span','badge',DEC[x.decision]||x.decision);bd.style.background='var(--c-'+x.decision+')';meta.appendChild(bd);
 if(x.refund_amount!=null)meta.appendChild(el('span','pill',x.refund_amount+' EUR'));(x.rules_cited||[]).forEach(k=>meta.appendChild(el('span','pill',k)));
 meta.appendChild(el('span','pill',r.latency_s+' s · $'+r.usage.cost_usd.toFixed(5)));P.appendChild(meta);
 const blk=(k,node)=>{const b=el('div','blk');b.appendChild(el('div','k',k));b.appendChild(node);P.appendChild(b)};
 blk('Customer email',el('div','box','From: '+t.from_email+'\n\n'+t.body));
 const f=el('div','');if(r.tool_calls.length){r.tool_calls.forEach(c=>{f.appendChild(el('div','pill mono',c.tool+'('+Object.values(c.input).join(', ')+')'));f.appendChild(el('div','box mono',JSON.stringify(c.output,null,1)))})}else f.appendChild(el('div','box','No lookups: this system has no tools.'));blk('Facts the system used',f);
 const dr=el('div','');dr.appendChild(el('div','box',x.draft_reply||'(no draft)'));if(x.internal_note)dr.appendChild(el('div','note','Note for reviewer: '+x.internal_note));(r.guardrail_notes||[]).forEach(g=>dr.appendChild(el('div','note','Guardrail: '+g)));
 if(r.reflection&&r.reflection.ok===false)dr.appendChild(el('div','note','The check revised the draft: '+(r.reflection.issues||[]).join('; ')));blk('Draft reply · review required',dr);
 const ck=el('div','checks');Object.entries(r.score.checks).forEach(([k,v])=>ck.appendChild(el('span','chip '+(v?'p':'f'),(v?'✓ ':'✗ ')+k.replace('_ok','').replace('_',' '))));blk('Automatic checks',ck);
 blk('Evaluation label (not shown to staff)',el('div','note','Expected: '+(DEC[t.expected.decision]||t.expected.decision)+' · rules '+t.expected.rules.join(', ')));
 const a=el('div','act');const msg=el('span','note','');[['Approve + send','p'],['Revise',''],['Escalate to manager','']].forEach(([l,c])=>{const b=el('button',c,l);b.onclick=()=>{msg.textContent='Recorded “'+l+'” (simulation, nothing sent)'};a.appendChild(b)});a.appendChild(msg);P.appendChild(a)}
list();
</script></body></html>
"""


def build(run: Path, out: Path, video: Path | None, preliminary: bool, interpretation: str = "") -> None:
    summary = json.loads((run / "summary.json").read_text())
    records = [json.loads(line) for line in (run / "records.jsonl").read_text().splitlines()]
    data = build_data(load_tickets(), records, summary)
    if interpretation:
        data["interpretation"] = interpretation
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "results.json").write_text(json.dumps(data, ensure_ascii=False))
    banner = ('<div class="banner"><b>Preliminary results.</b> These figures come from an early run and are being verified and updated. '
              'Treat them as provisional.</div>') if preliminary else ""
    if video and video.exists():
        shutil.copy(video, out / "demo.mp4")
        vhtml = '<video controls preload="metadata" src="demo.mp4"></video><p class="note">Narration is synthetic (text to speech).</p>'
    else:
        vhtml = '<div class="soon">The demo video will be added here.</div>'
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (PAGE.replace("__REPO__", REPO).replace("__BANNER__", banner).replace("__VIDEO__", vhtml).replace("__DATA__", payload))
    (out / "index.html").write_text(html)
    (out / ".nojekyll").write_text("")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--out", default=str(ROOT / "docs"))
    ap.add_argument("--video", default="")
    ap.add_argument("--preliminary", action="store_true")
    ap.add_argument("--interpretation", default="")
    a = ap.parse_args()
    build(Path(a.run), Path(a.out), Path(a.video) if a.video else None, a.preliminary, a.interpretation)
    print(f"site written to {a.out}")


if __name__ == "__main__":
    main()
