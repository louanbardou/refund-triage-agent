"""Generate the public project site (GitHub Pages) from a finished evaluation run.

  python3 -m refund_triage.site results/<run> [--video video/demo.mp4] [--out docs]

Writes docs/index.html (+ docs/data/results.json, docs/demo.mp4, docs/.nojekyll). Static: no server, no API key.
The "Platform" tab is a staff console that replays the recorded agent traces; it does not call a model.
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
<meta name="description" content="A bounded support agent that prepares a decision and a draft reply for staff review.">
<style>
:root{color-scheme:light;--bg:#f6f6f3;--card:#fff;--ink:#0b0b0b;--ink2:#52514e;--mute:#898781;--line:#e6e5df;--grid:#e1e0d9;--base:#c3c2b7;--soft:#f1f0ec;
--acc:#2a78d6;--acc-soft:#e8f1fc;--good:#0ca30c;--bad:#d03b3b;--gray:#b5b3aa;
--d-approve_refund:#2a78d6;--d-store_credit:#1baf7a;--d-reject:#eb6834;--d-ask_info:#eda100;--d-escalate:#6250d6;
--r:16px;--sh:0 1px 2px rgba(11,11,11,.04),0 8px 24px rgba(11,11,11,.05)}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--acc);text-decoration:none}button{font:inherit;color:inherit}
.wrap{max-width:1160px;margin:0 auto;padding:0 24px}
nav{position:sticky;top:0;z-index:30;background:rgba(246,246,243,.82);backdrop-filter:saturate(1.4) blur(14px);border-bottom:1px solid var(--line)}
nav .wrap{display:flex;align-items:center;gap:18px;height:60px}
.logo{font-weight:750;letter-spacing:-.02em;font-size:16px;color:var(--ink);display:flex;align-items:center;gap:9px;cursor:pointer;white-space:nowrap}
.logo i{width:22px;height:22px;border-radius:7px;background:linear-gradient(135deg,var(--acc),#6250d6);display:inline-block}
.tabs{display:flex;gap:2px;margin-left:18px;overflow-x:auto;scrollbar-width:none}.tabs::-webkit-scrollbar{display:none}
.tab{border:0;background:transparent;padding:8px 14px;border-radius:10px;color:var(--ink2);cursor:pointer;font-weight:550;font-size:14.5px;white-space:nowrap}
.tab:hover{background:var(--soft);color:var(--ink)}.tab.on{background:var(--ink);color:#fff}
.gh{margin-left:auto;border:1px solid var(--line);background:var(--card);color:var(--ink);padding:7px 13px;border-radius:10px;font-weight:550;font-size:14px;white-space:nowrap}
.clean nav{display:none}.clean .view{padding-top:14px}.clean .pf-head{display:none}
.view{display:none;padding:44px 0 80px;animation:fade .35s ease}.view.on{display:block}
@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
h1{font-size:clamp(40px,6.4vw,72px);line-height:1.02;letter-spacing:-.04em;margin:0 0 18px;font-weight:760}
h2{font-size:clamp(28px,3.6vw,40px);letter-spacing:-.03em;margin:0 0 6px;font-weight:720}
.sub{color:var(--ink2);font-size:clamp(16px,1.6vw,19px);max-width:620px;margin:0 0 26px}
.hero{position:relative;padding:34px 0 8px}
.hero:before{content:"";position:absolute;inset:-60px -20% auto auto;width:640px;height:420px;background:radial-gradient(closest-side,rgba(98,80,214,.16),transparent),radial-gradient(closest-side at 30% 70%,rgba(42,120,214,.18),transparent);filter:blur(10px);z-index:-1}
.btns{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:38px}
.btn{border:1px solid var(--line);background:var(--card);padding:11px 20px;border-radius:12px;font-weight:620;cursor:pointer;font-size:15px;color:var(--ink)}
.btn.p{background:var(--ink);color:#fff;border-color:var(--ink)}.btn:hover{transform:translateY(-1px);box-shadow:var(--sh)}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:20px 22px;box-shadow:var(--sh)}
.tile .l{color:var(--mute);font-size:13.5px;font-weight:550}.tile .v{font-size:40px;font-weight:740;letter-spacing:-.03em;line-height:1.1;margin-top:6px}
.tile .s{color:var(--mute);font-size:13px;margin-top:4px}
.steps{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:0 0 16px}
.stp{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:18px;box-shadow:var(--sh)}
.stp b{display:grid;place-items:center;width:30px;height:30px;border-radius:10px;background:var(--acc-soft);color:var(--acc);font-size:14px;margin-bottom:12px}
.stp.ai b{background:var(--acc);color:#fff}.stp strong{display:block;font-size:16px}.stp span{color:var(--mute);font-size:13.5px}
.chips{display:flex;gap:8px;flex-wrap:wrap}.chip{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:6px 13px;font-size:13.5px;color:var(--ink2)}
.lab{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--mute);margin:40px 0 12px}
.take{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:6px}.take .card{padding:16px 18px;box-shadow:none}.take b{display:block;font-size:15px;margin-bottom:3px}.take span{color:var(--ink2);font-size:13.5px}
.bento{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:24px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:22px;box-shadow:var(--sh);min-width:0}
.card.full{grid-column:1/-1}.card h3{margin:0;font-size:16px;font-weight:680}.card .cs{color:var(--mute);font-size:13.5px;margin:2px 0 16px}
.hrow{display:grid;grid-template-columns:132px 1fr 64px;align-items:center;gap:12px;height:34px;cursor:default;border-radius:8px}.hrow:hover{background:var(--soft)}
.hl{font-size:13.5px;color:var(--ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.hl.em{color:var(--ink);font-weight:650}
.htrack{position:relative;height:100%;display:flex;align-items:center}
.gl{position:absolute;top:0;bottom:0;width:1px;background:var(--grid)}
.hbar{position:relative;height:14px;border-radius:0 4px 4px 0;min-width:2px;transition:width .8s cubic-bezier(.2,.8,.2,1)}
.whisk{position:absolute;height:2px;background:var(--ink2);top:50%;margin-top:-1px;opacity:.7}
.whisk:before,.whisk:after{content:"";position:absolute;top:-4px;width:2px;height:10px;background:var(--ink2)}.whisk:before{left:0}.whisk:after{right:0}
.hv{font-weight:680;font-size:14px;font-variant-numeric:tabular-nums}
.axis{display:grid;grid-template-columns:132px 1fr 64px;gap:12px;margin-top:2px}.axis div:nth-child(2){position:relative;height:16px;border-top:1px solid var(--base)}
.axis span{position:absolute;top:3px;font-size:11.5px;color:var(--mute);transform:translateX(-50%)}
.heat{overflow-x:auto;padding-bottom:6px}.hg{display:grid;gap:3px;align-items:center;min-width:760px}
.hh{font-size:10.5px;color:var(--mute);text-align:center}.hn{font-size:13px;color:var(--ink2);padding-right:8px;white-space:nowrap}.hn.em{color:var(--ink);font-weight:650}
.cell{height:24px;border-radius:5px;display:grid;place-items:center;color:#fff;font-size:12px;font-weight:800;cursor:pointer;border:0;transition:transform .12s}
.cell:hover{transform:scale(1.18)}.cell.p{background:var(--good)}.cell.f{background:var(--bad)}
.legend{display:flex;gap:16px;color:var(--mute);font-size:13px;margin-top:12px;align-items:center}.legend i{display:inline-grid;place-items:center;width:16px;height:16px;border-radius:4px;color:#fff;font-size:10px;font-style:normal;font-weight:800;margin-right:6px;vertical-align:-3px}
details{margin-top:16px}summary{cursor:pointer;color:var(--ink2);font-weight:600;font-size:14px}
.tw{overflow-x:auto;margin-top:12px;border:1px solid var(--line);border-radius:12px;background:var(--card)}
table{border-collapse:collapse;width:100%;min-width:720px;font-size:13.5px}th,td{padding:10px 12px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}th:first-child,td:first-child{text-align:left}
th{font-size:11.5px;color:var(--mute);text-transform:uppercase;letter-spacing:.06em}tr:last-child td{border-bottom:0}
.tip{position:fixed;display:none;z-index:99;background:var(--ink);color:#fff;padding:7px 11px;border-radius:9px;font-size:12.5px;max-width:250px;pointer-events:none;box-shadow:0 8px 24px rgba(0,0,0,.2)}
.pf-head{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:14px}.pf-head h2{margin:0;font-size:28px}
.pf-head .grow{flex:1}
select{font:inherit;font-size:13.5px;padding:7px 10px;border-radius:10px;border:1px solid var(--line);background:var(--card)}
.tog{display:flex;gap:7px;align-items:center;color:var(--ink2);font-size:13.5px;cursor:pointer}
.bar{display:grid;grid-template-columns:repeat(5,auto) 1fr;gap:22px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:14px 20px;box-shadow:var(--sh);margin-bottom:14px}
.bar .k{font-size:12px;color:var(--mute);font-weight:600}.bar .n{font-size:22px;font-weight:730;letter-spacing:-.02em;line-height:1.15}
.prog{height:8px;background:var(--soft);border-radius:99px;overflow:hidden}.prog i{display:block;height:100%;background:var(--acc);border-radius:99px;transition:width .5s}
.app{display:grid;grid-template-columns:330px 1fr;gap:14px;align-items:start}
.inbox{background:var(--card);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--sh);overflow:hidden;position:sticky;top:76px}
.ftabs{display:flex;gap:4px;padding:10px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.ft{border:0;background:transparent;padding:5px 11px;border-radius:8px;font-size:13px;color:var(--ink2);cursor:pointer;font-weight:580}.ft.on{background:var(--soft);color:var(--ink)}
.ilist{max-height:calc(100vh - 230px);min-height:420px;overflow:auto}
.it{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;width:100%;text-align:left;border:0;border-bottom:1px solid var(--line);background:transparent;padding:11px 14px;cursor:pointer;transition:background .15s}
.it:hover{background:var(--soft)}.it.on{background:var(--acc-soft);box-shadow:inset 3px 0 0 var(--acc)}
.sd{width:9px;height:9px;border-radius:50%;background:var(--base)}.sd.sent{background:var(--good)}.sd.escalated{background:var(--d-escalate)}.sd.pending{background:var(--acc)}
.it .t{font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.it .f{font-size:12.5px;color:var(--mute);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.it.done{opacity:.55}
.dpill{font-size:11.5px;color:var(--ink2);display:flex;gap:5px;align-items:center;white-space:nowrap}.dpill i{width:8px;height:8px;border-radius:50%}
.work{display:flex;flex-direction:column;gap:14px;min-width:0}
.tl{display:flex;gap:6px;flex-wrap:wrap;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:14px 16px;box-shadow:var(--sh);align-items:center}
.ts{display:flex;gap:8px;align-items:center;font-size:13.5px;color:var(--mute);padding:5px 12px;border-radius:99px;background:var(--soft);transition:all .25s}
.ts b{display:grid;place-items:center;width:18px;height:18px;border-radius:50%;background:var(--base);color:#fff;font-size:10px}
.ts.run{background:var(--acc-soft);color:var(--acc)}.ts.run b{background:var(--acc);animation:pulse 1s infinite}.ts.ok{color:var(--ink2)}.ts.ok b{background:var(--good)}
@keyframes pulse{50%{transform:scale(1.25)}}
.tl .ar{color:var(--base)}.tl .rep{margin-left:auto;font-size:12.5px;color:var(--mute);border:0;background:transparent;cursor:pointer}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.pn{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:18px 20px;box-shadow:var(--sh);min-width:0}
.pn h4{margin:0 0 10px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);font-weight:700}
.mail{white-space:pre-wrap;word-break:break-word;font-size:14.5px}.from{font-size:13px;color:var(--mute);margin-bottom:8px}
.fact{border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:10px;background:var(--soft)}
.fr{display:flex;justify-content:space-between;gap:12px;font-size:13.5px;padding:3px 0}.fr span:first-child{color:var(--mute)}.fr span:last-child{font-weight:600;text-align:right}
.st{display:inline-block;padding:1px 9px;border-radius:99px;background:var(--acc-soft);color:var(--acc);font-weight:650;font-size:12px}
.err{border-color:#f0c4c0;background:#fdf1f0;color:#8a1f19;font-size:14px}
.rule{font-size:13.5px;color:var(--ink2);padding:6px 0;border-top:1px solid var(--line)}.rule b{color:var(--ink);margin-right:6px}
.rec{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.rec .dot{width:12px;height:12px;border-radius:50%}.rec .big{font-size:22px;font-weight:730;letter-spacing:-.02em}
.amt{margin-left:auto;font-size:22px;font-weight:730}
.note{margin-top:8px;color:var(--ink2);font-size:13.5px;background:var(--soft);border-radius:10px;padding:9px 12px}
textarea{width:100%;min-height:230px;resize:vertical;border:1px solid var(--line);border-radius:12px;padding:14px;font:14.5px/1.6 system-ui,sans-serif;color:var(--ink);background:#fff}
textarea:focus{outline:2px solid var(--acc);outline-offset:1px}
.acts{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:12px}
.go{border:0;background:var(--acc);color:#fff;padding:12px 20px;border-radius:12px;font-weight:650;cursor:pointer;font-size:15px}.go:hover{filter:brightness(1.07);transform:translateY(-1px)}
.go.vio{background:var(--d-escalate)}.go:disabled,.sec:disabled{opacity:.4;cursor:not-allowed;transform:none}
.sec{border:1px solid var(--line);background:var(--card);padding:12px 18px;border-radius:12px;font-weight:600;cursor:pointer}
kbd{font:11.5px ui-monospace,Menlo,monospace;background:rgba(0,0,0,.08);border-radius:5px;padding:0 5px;margin-left:8px}
.sec kbd{background:var(--soft)}
.hint{color:var(--mute);font-size:12.5px;margin-top:10px}.acts .hint{margin:0}
.skel{height:14px;border-radius:7px;margin:10px 0;background:linear-gradient(90deg,var(--soft),#fff,var(--soft));background-size:200% 100%;animation:sk 1.1s infinite}@keyframes sk{to{background-position:-200% 0}}
.evalbox{margin-top:12px;border:1px dashed var(--base);border-radius:12px;padding:10px 12px;font-size:13px;color:var(--ink2)}
.ck{display:inline-block;margin:3px 5px 0 0;padding:1px 8px;border-radius:7px;border:1px solid var(--line);font-size:12px}.ck.f{color:var(--bad);border-color:var(--bad);font-weight:700}
.toast{position:fixed;left:50%;bottom:28px;transform:translate(-50%,20px);background:var(--ink);color:#fff;padding:12px 20px;border-radius:12px;font-weight:580;opacity:0;pointer-events:none;transition:all .3s;z-index:90;box-shadow:0 12px 32px rgba(0,0,0,.25)}
.toast.on{opacity:1;transform:translate(-50%,0)}
.empty{display:grid;place-items:center;text-align:center;min-height:200px;color:var(--mute)}
video{width:100%;max-width:960px;border-radius:var(--r);border:1px solid var(--line);background:#000;box-shadow:var(--sh)}
.soon{background:var(--card);border:1px dashed var(--base);border-radius:var(--r);padding:60px;text-align:center;color:var(--mute);max-width:960px}
pre{background:#0f1623;color:#e6edf3;border-radius:14px;padding:20px 22px;overflow:auto;font:13.5px/1.7 ui-monospace,Menlo,Consolas,monospace;margin:0;max-width:860px}
ul.lim{margin:0;padding-left:18px;color:var(--ink2);max-width:760px}ul.lim li{margin:6px 0}
@media (max-width:900px){.take{grid-template-columns:1fr}.tiles{grid-template-columns:repeat(2,1fr)}.steps{grid-template-columns:1fr 1fr}.bento{grid-template-columns:1fr}.app{grid-template-columns:1fr}.inbox{position:static}.ilist{max-height:260px;min-height:0}.cols{grid-template-columns:1fr}.bar{grid-template-columns:repeat(2,1fr)}.gh{display:none}.tabs{margin-left:6px}}
</style></head><body>
<nav><div class="wrap"><div class="logo" onclick="go('overview')"><i></i>Refund Triage</div>
<div class="tabs" id="tabs"></div><a class="gh" href="__REPO__">GitHub ↗</a></div></nav>

<main class="wrap">
<section class="view" id="v-overview">
 <div class="hero">
  <h1>Refund emails,<br>handled automatically.</h1>
  <p class="sub">An agent reads each email, looks up the order, applies the returns policy and writes the reply. Staff only review and approve.</p>
  <div class="btns"><button class="btn p" onclick="go('platform')">Open the platform →</button><button class="btn" onclick="go('results')">See the results</button></div>
 </div>
 <div class="tiles" id="tiles"></div>
 <div class="lab">How it works</div>
 <div class="steps">
  <div class="stp"><b>1</b><strong>Read</strong><span>Email, any language</span></div>
  <div class="stp ai"><b>2</b><strong>Look up</strong><span>Order and day counts</span></div>
  <div class="stp ai"><b>3</b><strong>Decide</strong><span>Policy rules R1–R9</span></div>
  <div class="stp ai"><b>4</b><strong>Check</strong><span>Draft against facts</span></div>
  <div class="stp"><b>5</b><strong>Review</strong><span>Staff approve or escalate</span></div>
 </div>
 <div class="lab">Controls</div>
 <div class="chips"><span class="chip">Read-only tools</span><span class="chip">Identity check in code</span><span class="chip">Max 6 steps</span><span class="chip">Above 100 € → manager</span><span class="chip">Email = untrusted</span><span class="chip">Any failure → human</span></div>
</section>

<section class="view" id="v-results">
 <h2>Results</h2><p class="sub" id="rsub"></p>
 <div class="take" id="take"></div>
 <div class="bento">
  <div class="card"><h3>Task success</h3><div class="cs">Share of tickets passing every check. Whiskers: 95% interval.</div><div id="c-succ"></div></div>
  <div class="card"><h3>Staff time per ticket</h3><div class="cs">Minutes, modelled from assumed step times.</div><div id="c-time"></div></div>
  <div class="card"><h3>Cost per 1,000 tickets</h3><div class="cs">US dollars, model tokens only.</div><div id="c-cost"></div></div>
  <div class="card"><h3>Latency per ticket</h3><div class="cs">Seconds, mean over tickets.</div><div id="c-lat"></div></div>
  <div class="card full" id="heatcard"><h3>Where each system fails</h3><div class="cs">One cell per ticket. Hover for the failed checks; click to open the ticket in the platform.</div>
   <div class="heat"><div class="hg" id="heat"></div></div>
   <div class="legend"><span><i style="background:var(--good)">✓</i>All checks passed</span><span><i style="background:var(--bad)">✕</i>At least one check failed</span></div></div>
 </div>
 <details><summary>Table view</summary><div class="tw"><table id="restable"></table></div></details>
</section>

<section class="view" id="v-platform">
 <div class="pf-head"><h2>Staff platform</h2><span class="grow"></span>
  <label class="tog"><input type="checkbox" id="evaltog"> Evaluation labels</label>
  <select id="eng" aria-label="Engine"></select></div>
 <div class="bar" id="statbar"></div>
 <div class="app"><div class="inbox"><div class="ftabs" id="ftabs"></div><div class="ilist" id="ilist"></div></div><div class="work" id="work"></div></div>
</section>

<section class="view" id="v-video"><h2>Demo video</h2><p class="sub">Narration is synthetic (text to speech).</p>__VIDEO__</section>

<section class="view" id="v-run">
 <h2>Run it</h2><p class="sub">Python 3.10+ and <code>pip install anthropic</code>. Tests and the template baseline need no key.</p>
<pre>git clone __REPO__.git
cd refund-triage-agent

python3 -m unittest discover -s tests -t .      # offline checks
python3 run_eval.py --systems b0                # offline baseline

export ANTHROPIC_API_KEY=...                    # live runs
python3 triage.py T06                           # one ticket, full trace
python3 run_eval.py --systems b0,b1,b1d,agent_nr,agent --label main</pre>
 <div class="lab">Limits</div>
 <ul class="lim"><li>Fictional shop, author-written tickets, hand-labelled and cross-checked with a rule-based oracle.</li><li>One small model; deterministic regex checks, no LLM judge.</li><li>Staff time is modelled from assumptions, not measured.</li><li>The platform replays recorded runs and calls no model.</li></ul>
</section>
</main>
<div class="toast" id="toast"></div>

<script>
const D=__DATA__,S=D.summary;
const $=(s,r)=>(r||document).querySelector(s);
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
const NAME={b0_templates:'B0 · Templates',b1_access:'B1 · Paste + one call',b1_access_days:'B1d · Paste + days',agent_no_reflection:'Agent · no check',agent:'Agent · with check'};
const SHORT={b0_templates:'B0 templates',b1_access:'B1 paste',b1_access_days:'B1d paste + days',agent_no_reflection:'Agent, no check',agent:'Agent + check'};
const DEC={approve_refund:'Approve refund',store_credit:'Offer store credit',reject:'Reject',ask_info:'Ask for information',escalate:'Escalate to manager'};
const RULES={R1:'Unused item, within 30 days of delivery: full refund',R2:'Final-sale item: not returnable unless damaged',R3:'Days 31–45: store credit only; after 45: refused',R4:'Damaged or defective: within 14 days with photo, refund; no photo, ask; later, manager',R5:'Processing orders can be cancelled; shipped orders cannot',R6:'Shipped: up to 10 days late is in transit; beyond, a manager investigates',R7:'Refund above 100 EUR needs manager approval',R8:'Sender email must match the order; reveal nothing otherwise',R9:'Explicit exception request: a manager decides'};
const CHK={decision_ok:'decision',rules_ok:'rules',amount_ok:'amount',language_ok:'language',forbidden_ok:'claims',leak_ok:'leak',promise_ok:'promises',amounts_ok:'figures',no_error:'no error'};
const ORDER=['b0_templates','b1_access','b1_access_days','agent_no_reflection','agent'].filter(s=>S[s]);
const ACCENT='#2a78d6',GRAY='#b5b3aa';
const colorOf=s=>s==='agent'?ACCENT:GRAY;
const pct=x=>Math.round(x*100)+'%';
const MAN=S.manual.staff_minutes_per_ticket;

const tipEl=el('div','tip');document.body.appendChild(tipEl);
function tip(n,t){n.addEventListener('mousemove',e=>{tipEl.textContent=t;tipEl.style.display='block';tipEl.style.left=Math.min(e.clientX+14,innerWidth-270)+'px';tipEl.style.top=(e.clientY+16)+'px'});n.addEventListener('mouseleave',()=>tipEl.style.display='none');n.setAttribute('aria-label',t)}
let tt;function toast(m){const t=$('#toast');t.textContent=m;t.classList.add('on');clearTimeout(tt);tt=setTimeout(()=>t.classList.remove('on'),2200)}

const VIEWS=[['overview','Overview'],['results','Results'],['platform','Platform'],['video','Video'],['run','Run it']];
const tabs=$('#tabs');VIEWS.forEach(([k,l])=>{const b=el('button','tab',l);b.id='tab-'+k;b.onclick=()=>go(k);tabs.appendChild(b)});
function go(k){if(!VIEWS.find(v=>v[0]===k))k='overview';VIEWS.forEach(([v])=>{$('#v-'+v).classList.toggle('on',v===k);$('#tab-'+v).classList.toggle('on',v===k)});history.replaceState(null,'','#'+k);scrollTo({top:0});if(k==='platform')renderPlatform();if(k==='results')drawResults()}
function parseHash(){const p=location.hash.slice(1).split('&'),o={};p.slice(1).forEach(x=>{const [a,b]=x.split('=');o[a]=b});return [p[0],o]}
addEventListener('hashchange',()=>boot());

const A=S.agent||S[ORDER[ORDER.length-1]];
[[pct(A.task_success),'Task success',D.summary._meta.n_tickets+' tickets'],[A.staff_minutes_per_ticket.toFixed(1)+' min','Staff time per ticket','vs '+MAN.toFixed(1)+' min manual (modelled)'],['$'+A.cost_per_ticket_usd.toFixed(4),'Model cost per ticket','tokens only'],[A.latency_mean_s+' s','Latency per ticket','mean']]
 .forEach(([v,l,s])=>{const t=el('div','tile');t.appendChild(el('div','l',l));t.appendChild(el('div','v',v));t.appendChild(el('div','s',s));$('#tiles').appendChild(t)});

const niceMax=v=>{if(v<=0)return 1;const e=Math.pow(10,Math.floor(Math.log10(v))),f=v/e,n=f<=1?1:f<=2?2:f<=2.5?2.5:f<=5?5:10;return n*e};
function hbar(host,items,max,fmtTick){host.textContent='';const ticks=[0,.25,.5,.75,1];
 items.forEach(it=>{const row=el('div','hrow');row.appendChild(el('div','hl'+(it.em?' em':''),it.label));const tr=el('div','htrack');
  ticks.forEach(t=>{const g=el('div','gl');g.style.left=(t*100)+'%';tr.appendChild(g)});
  const b=el('div','hbar');b.style.background=it.color;b.style.width='0%';tr.appendChild(b);requestAnimationFrame(()=>requestAnimationFrame(()=>{b.style.width=Math.min(100,it.value/max*100)+'%'}));
  if(it.lo!=null){const w=el('div','whisk');w.style.left=(it.lo/max*100)+'%';w.style.width=((it.hi-it.lo)/max*100)+'%';tr.appendChild(w)}
  row.appendChild(tr);row.appendChild(el('div','hv',it.text));tip(row,it.tip);host.appendChild(row)});
 const ax=el('div','axis');ax.appendChild(el('div'));const m=el('div');ticks.forEach(t=>{const s=el('span','',fmtTick(t*max));s.style.left=(t*100)+'%';m.appendChild(s)});ax.appendChild(m);ax.appendChild(el('div'));host.appendChild(ax)}
function drawResults(){
 $('#rsub').textContent=D.summary._meta.n_tickets+' labelled tickets'+(D.summary._meta.repeats>1?' × '+D.summary._meta.repeats+' runs':'')+' · '+D.summary._meta.model;
 const it=(fn)=>ORDER.map(s=>Object.assign({label:SHORT[s],color:colorOf(s),em:s==='agent'},fn(S[s],s)));
 hbar($('#c-succ'),it(m=>({value:m.task_success,lo:m.task_success_ci95[0],hi:m.task_success_ci95[1],text:pct(m.task_success),tip:pct(m.task_success)+' task success (95% interval '+pct(m.task_success_ci95[0])+' to '+pct(m.task_success_ci95[1])+')'})),1,v=>Math.round(v*100)+'%');
 const tm=it(m=>({value:m.staff_minutes_per_ticket,text:m.staff_minutes_per_ticket.toFixed(1),tip:m.staff_minutes_per_ticket.toFixed(2)+' modelled staff minutes per ticket'}));
 tm.unshift({label:'Fully manual',color:'#52514e',value:MAN,text:MAN.toFixed(1),tip:'Assumed manual handling time: '+MAN.toFixed(1)+' min'});
 hbar($('#c-time'),tm,niceMax(MAN*1.05),v=>v.toFixed(v%1?1:0));
 const cm=Math.max(...ORDER.map(s=>S[s].cost_per_ticket_usd*1000),.01);
 hbar($('#c-cost'),it(m=>({value:m.cost_per_ticket_usd*1000,text:'$'+(m.cost_per_ticket_usd*1000).toFixed(2),tip:'$'+(m.cost_per_ticket_usd*1000).toFixed(2)+' per 1,000 tickets ($'+m.cost_per_ticket_usd.toFixed(5)+' each)'})),niceMax(cm*1.05),v=>'$'+(Number.isInteger(v)?v:v.toFixed(2)));
 const lm=Math.max(...ORDER.map(s=>S[s].latency_p95_s),.5);
 hbar($('#c-lat'),it(m=>({value:m.latency_mean_s,text:m.latency_mean_s.toFixed(1)+' s',tip:'Mean '+m.latency_mean_s+' s, 95th percentile '+m.latency_p95_s+' s'})),niceMax(lm*1.05),v=>v.toFixed(v%1?1:0)+'s');
 takeaways();heat();
}
function takeaways(){const T=$('#take');T.textContent='';const llm=ORDER.filter(s=>s!=='b0_templates');if(!llm.length)return;
 const ks=llm.map(s=>Math.round(S[s].task_success*S[s].n)),n=S[llm[0]].n,lo=Math.min(...ks),hi=Math.max(...ks);
 const items=[['Accuracy is at the ceiling','Every model system passes '+(lo===hi?lo:lo+'–'+hi)+' of '+n+' tickets, so these checks cannot rank them.']];
 if(S.agent&&S.b1_access){items.push(['The gap is staff time','Modelled '+S.agent.staff_minutes_per_ticket.toFixed(1)+' min with the agent vs '+S.b1_access.staff_minutes_per_ticket.toFixed(1)+' min pasting by hand. It rests on an assumed 2.5 min manual lookup.']);
  items.push(['It costs more and is slower',(S.agent.cost_per_ticket_usd/S.b1_access.cost_per_ticket_usd).toFixed(1)+'× the cost and '+S.agent.latency_mean_s+' s vs '+S.b1_access.latency_mean_s+' s per ticket.'])}
 items.forEach(([h,t])=>{const c=el('div','card');c.appendChild(el('b','',h));c.appendChild(el('span','',t));T.appendChild(c)})}
function heat(){const H=$('#heat');H.textContent='';const ids=[...new Set(D.rows.map(r=>r.ticket_id))].sort();H.style.gridTemplateColumns='128px repeat('+ids.length+',1fr)';
 H.appendChild(el('div'));ids.forEach(i=>H.appendChild(el('div','hh',String(+i.slice(1)))));
 ORDER.forEach(s=>{H.appendChild(el('div','hn'+(s==='agent'?' em':''),SHORT[s]));
  ids.forEach(id=>{const r=D.rows.find(x=>x.system===s&&x.ticket_id===id);if(!r){H.appendChild(el('div'));return}const c=el('button','cell '+(r.score.success?'p':'f'),r.score.success?'✓':'✕');
   tip(c,id+' · '+D.tickets[id].subject+(r.score.success?': all checks passed':': failed '+r.score.failed.map(k=>CHK[k]||k).join(', '))+(D.tickets[id].label_note?' · '+D.tickets[id].label_note:''));
   c.onclick=()=>{eng=s;sel=id;go('platform')};H.appendChild(c)})});
 const tb=$('#restable');tb.textContent='';const hr=el('tr');['System','Task success','95% interval','Decision acc.','Wrong-money','Reply flags','Latency mean / p95','Cost / ticket','Staff min'].forEach(h=>hr.appendChild(el('th','',h)));tb.appendChild(hr);
 ORDER.forEach(s=>{const m=S[s],r=el('tr');[NAME[s],pct(m.task_success),pct(m.task_success_ci95[0])+' – '+pct(m.task_success_ci95[1]),pct(m.decision_accuracy),m.wrong_money_decisions,m.reply_flag_tickets,m.latency_mean_s+' / '+m.latency_p95_s+' s','$'+m.cost_per_ticket_usd.toFixed(5),m.staff_minutes_per_ticket.toFixed(2)].forEach(v=>r.appendChild(el('td','',String(v))));tb.appendChild(r)})}

let eng=S.agent?'agent':ORDER[0],sel=null,filter='all',timer=null,typer=null;
const status={},processed={},edited={};
const key=()=>eng+'|'+sel;
const rowsOf=()=>D.rows.filter(r=>r.system===eng).sort((a,b)=>a.ticket_id<b.ticket_id?-1:1);
const st=r=>status[eng+'|'+r.ticket_id]||'pending';
const engSel=$('#eng');ORDER.forEach(s=>{const o=el('option','',SHORT[s]);o.value=s;engSel.appendChild(o)});engSel.onchange=()=>{eng=engSel.value;sel=null;renderPlatform()};
$('#evaltog').onchange=()=>{if(sel)renderTicket()};
function bar(){const rs=rowsOf(),n=rs.length,sent=rs.filter(r=>st(r)==='sent').length,esc=rs.filter(r=>st(r)==='escalated').length,ed=rs.filter(r=>edited[eng+'|'+r.ticket_id]).length;
 const saved=rs.reduce((a,r)=>a+(st(r)==='sent'?MAN-(edited[eng+'|'+r.ticket_id]?2.5:1.0):0),0);
 const B=$('#statbar');B.textContent='';[['Pending',n-sent-esc],['Sent',sent],['Escalated',esc],['Edited',ed],['Time saved',saved.toFixed(1)+' min']].forEach(([k,v])=>{const d=el('div');d.appendChild(el('div','k',k));d.appendChild(el('div','n',String(v)));B.appendChild(d)});
 const p=el('div','prog');const i=el('i');i.style.width=((sent+esc)/n*100)+'%';p.appendChild(i);B.appendChild(p)}
function inbox(){const L=$('#ilist');L.textContent='';const F=$('#ftabs');F.textContent='';
 [['all','All'],['pending','Pending'],['mgr','Manager'],['done','Done']].forEach(([k,l])=>{const b=el('button','ft'+(filter===k?' on':''),l);b.onclick=()=>{filter=k;inbox()};F.appendChild(b)});
 const rs=rowsOf().filter(r=>filter==='all'||(filter==='pending'&&st(r)==='pending')||(filter==='mgr'&&r.result.decision==='escalate')||(filter==='done'&&st(r)!=='pending'));
 rs.forEach(r=>{const b=el('button','it'+(r.ticket_id===sel?' on':'')+(st(r)!=='pending'?' done':''));b.appendChild(el('span','sd '+st(r)));
  const m=el('div');m.appendChild(el('div','t',D.tickets[r.ticket_id].subject));m.appendChild(el('div','f',r.ticket_id+' · '+D.tickets[r.ticket_id].from_email));b.appendChild(m);
  const p=el('span','dpill');const dot=el('i');dot.style.background=processed[eng+'|'+r.ticket_id]?'var(--d-'+r.result.decision+')':'var(--base)';p.appendChild(dot);p.appendChild(document.createTextNode(processed[eng+'|'+r.ticket_id]?(DEC[r.result.decision]||'').split(' ')[0]:'New'));b.appendChild(p);
  b.onclick=()=>{sel=r.ticket_id;inbox();renderTicket()};L.appendChild(b)});
 if(!rs.length)L.appendChild(el('div','empty','Nothing here.'))}
function renderPlatform(){if(!rowsOf().length)return;engSel.value=eng;if(!sel)sel=(rowsOf().find(r=>st(r)==='pending')||rowsOf()[0]).ticket_id;bar();inbox();renderTicket()}
function steps(r){const s=['Read email'];r.tool_calls.forEach(c=>s.push(c.tool==='lookup_order'?'Look up '+(c.input.order_id||'order'):'List orders'));s.push('Apply '+((r.result.rules_cited||[]).join(', ')||'policy'));s.push('Draft reply');if(r.reflection)s.push('Check draft');return s}
function factsNode(r){const f=el('div');if(!r.tool_calls.length){f.appendChild(el('div','fact','This engine has no tools: no order lookup.'));return f}
 r.tool_calls.forEach(c=>{const o=c.output;if(o.error){f.appendChild(el('div','fact err','✕ '+o.error));return}
  if(o.orders){const d=el('div','fact'),q=el('div','fr');q.appendChild(el('span','','Orders for this sender'));q.appendChild(el('span','',o.orders.map(x=>x.order_id+' ('+x.status+')').join(', ')||'none'));d.appendChild(q);f.appendChild(d);return}
  const d=el('div','fact');const row=(k,v,pill)=>{const q=el('div','fr');q.appendChild(el('span','',k));q.appendChild(el('span',pill?'st':'',v));d.appendChild(q)};
  row('Order',o.order_id);row('Status',o.status,true);if(o.delivered_date)row('Delivered',o.delivered_date+' · '+o.days_since_delivery+' days ago');
  if(o.days_past_estimated_delivery!=null)row('Estimated',o.estimated_delivery+' · '+o.days_past_estimated_delivery+' days late');
  o.items.forEach(i=>row(i.name+(i.final_sale?' (final sale)':''),i.price.toFixed(2)+' EUR'));if(o.items.length>1)row('Total',o.order_total.toFixed(2)+' EUR');f.appendChild(d)});return f}
function renderTicket(){const r=rowsOf().find(x=>x.ticket_id===sel);if(!r)return;const t=D.tickets[sel],x=r.result,W=$('#work');clearInterval(timer);clearInterval(typer);W.textContent='';
 const done=!!processed[key()];
 const tl=el('div','tl');const nodes=steps(r).map((s,i)=>{if(i)tl.appendChild(el('span','ar','›'));const n=el('span','ts'+(done?' ok':''));n.appendChild(el('b','',done?'✓':String(i+1)));n.appendChild(document.createTextNode(s));tl.appendChild(n);return n});
 const rep=el('button','rep','↻ Replay');rep.onclick=()=>{delete processed[key()];inbox();renderTicket()};tl.appendChild(rep);W.appendChild(tl);
 const cols=el('div','cols');W.appendChild(cols);
 const left=el('div','pn');left.appendChild(el('h4','','Customer email'));left.appendChild(el('div','from',t.from_email+' · '+sel));left.appendChild(el('div','mail',t.body));
 const leftF=el('div','pn');leftF.appendChild(el('h4','','Facts retrieved'));
 const l2=el('div');l2.style.cssText='display:flex;flex-direction:column;gap:14px;min-width:0';l2.appendChild(left);l2.appendChild(leftF);cols.appendChild(l2);
 const rr=el('div');rr.style.cssText='display:flex;flex-direction:column;gap:14px;min-width:0';cols.appendChild(rr);
 const rec=el('div','pn'),drf=el('div','pn');rr.appendChild(rec);rr.appendChild(drf);
 function reveal(instant){leftF.appendChild(factsNode(r));(x.rules_cited||[]).forEach(k=>{const q=el('div','rule');q.appendChild(el('b','',k));q.appendChild(document.createTextNode(RULES[k]||''));leftF.appendChild(q)});
  rec.textContent='';rec.appendChild(el('h4','','Recommendation'));const rc=el('div','rec');const dot=el('span','dot');dot.style.background='var(--d-'+x.decision+')';rc.appendChild(dot);rc.appendChild(el('span','big',DEC[x.decision]||x.decision));
  if((x.decision==='approve_refund'||x.decision==='store_credit')&&x.refund_amount!=null)rc.appendChild(el('span','amt',x.refund_amount.toFixed(2)+' €'));rec.appendChild(rc);
  if(x.internal_note)rec.appendChild(el('div','note','For the reviewer: '+x.internal_note));(r.guardrail_notes||[]).forEach(g=>rec.appendChild(el('div','note','Guardrail: '+g)));
  if(r.reflection&&r.reflection.ok===false)rec.appendChild(el('div','note','The draft check revised the reply: '+(r.reflection.issues||[]).join('; ')));
  drf.textContent='';drf.appendChild(el('h4','','Draft reply · editable'));const ta=el('textarea');ta.setAttribute('aria-label','Draft reply');drf.appendChild(ta);
  const full=x.draft_reply||'';
  if(instant||!full){ta.value=full}else{let i=0;ta.value='';typer=setInterval(()=>{i+=3;ta.value=full.slice(0,i);if(i>=full.length)clearInterval(typer)},8)}
  ta.onfocus=()=>{clearInterval(typer);if(ta.value.length<full.length&&full.startsWith(ta.value))ta.value=full};
  const a=el('div','acts');const esc=x.decision==='escalate';
  const primary=el('button','go'+(esc?' vio':''),esc?'Send to manager':'Approve & send');primary.appendChild(el('kbd','',esc?'E':'A'));
  const alt=el('button','sec',esc?'Approve & send anyway':'Escalate to manager');alt.appendChild(el('kbd','',esc?'A':'E'));
  const st0=status[key()];if(st0){primary.disabled=true;alt.disabled=true;a.appendChild(el('span','hint',st0==='sent'?'Sent (simulation).':'Sent to manager (simulation).'))}
  primary.onclick=()=>act(esc?'escalated':'sent',ta,full);alt.onclick=()=>act(esc?'sent':'escalated',ta,full);a.appendChild(primary);a.appendChild(alt);drf.appendChild(a);
  drf.appendChild(el('div','hint','Nothing is really sent. Keys: J / K move between tickets.'));
  if($('#evaltog').checked){const e=el('div','evalbox');e.appendChild(el('div','','Evaluation label: expected '+(DEC[t.expected.decision]||t.expected.decision)+' · rules '+t.expected.rules.join(', ')));if(t.label_note)e.appendChild(el('div','',t.label_note));if((r.reply_flags||[]).length)e.appendChild(el('div','','Reply flags: '+r.reply_flags.join(', ')));Object.entries(r.score.checks).forEach(([k,v])=>e.appendChild(el('span','ck'+(v?'':' f'),(v?'✓ ':'✕ ')+(CHK[k]||k))));drf.appendChild(e)}}
 function skeleton(){rec.appendChild(el('h4','','Recommendation'));[60,90,40].forEach(w=>{const s=el('div','skel');s.style.width=w+'%';rec.appendChild(s)});drf.appendChild(el('h4','','Draft reply'));[100,95,90,60].forEach(w=>{const s=el('div','skel');s.style.width=w+'%';drf.appendChild(s)})}
 if(done){reveal(true)}else{skeleton();let i=0;nodes[0].className='ts run';timer=setInterval(()=>{nodes[i].className='ts ok';nodes[i].firstChild.textContent='✓';i++;if(i<nodes.length){nodes[i].className='ts run'}else{clearInterval(timer);processed[key()]=true;inbox();reveal(false)}},330)}}
function act(kind,ta,orig){const k=key();status[k]=kind;edited[k]=ta.value.trim()!==orig.trim();
 toast(kind==='sent'?'Reply sent'+(edited[k]?' (edited)':'')+' · simulation':'Sent to manager · simulation');bar();inbox();
 const rs=rowsOf(),i=rs.findIndex(r=>r.ticket_id===sel),nx=rs.slice(i+1).concat(rs.slice(0,i)).find(r=>st(r)==='pending');
 if(nx){sel=nx.ticket_id;setTimeout(()=>{inbox();renderTicket();const it=document.querySelector('.it.on');if(it)it.scrollIntoView({block:'nearest'})},350)}else renderTicket()}
addEventListener('keydown',e=>{if(!$('#v-platform').classList.contains('on'))return;const tg=e.target.tagName;if(tg==='TEXTAREA'||tg==='SELECT'||tg==='INPUT'||e.metaKey||e.ctrlKey)return;
 const rs=rowsOf(),i=rs.findIndex(r=>r.ticket_id===sel);
 if(e.key==='j'||e.key==='k'){const n=rs[Math.max(0,Math.min(rs.length-1,i+(e.key==='j'?1:-1)))];sel=n.ticket_id;inbox();renderTicket();const it=document.querySelector('.it.on');if(it)it.scrollIntoView({block:'nearest'})}
 if(e.key==='a'||e.key==='e'){const b=[...document.querySelectorAll('.acts .go,.acts .sec')].filter(b=>!b.disabled).find(b=>b.textContent.endsWith(e.key.toUpperCase()));if(b)b.click()}});

function boot(){const [k,o]=parseHash();if(o.e&&S[o.e])eng=o.e;if(o.t)sel=o.t;if(o.clean)document.body.classList.add('clean');if(o.z)document.body.style.zoom=o.z;if(o.ev)$('#evaltog').checked=true;go(k||'overview');if(o.sc)setTimeout(()=>{const t=document.getElementById(o.sc);if(t)t.scrollIntoView({block:'start'})},60)}
boot();
</script></body></html>
"""


def build(run: Path, out: Path, video: Path | None) -> None:
    summary = json.loads((run / "summary.json").read_text())
    records = [json.loads(line) for line in (run / "records.jsonl").read_text().splitlines()]
    data = build_data(load_tickets(), records, summary)
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "results.json").write_text(json.dumps(data, ensure_ascii=False))
    if video and video.exists():
        shutil.copy(video, out / "demo.mp4")
        vhtml = '<video controls preload="metadata" src="demo.mp4"></video>'
    else:
        vhtml = '<div class="soon">The demo video will be added here.</div>'
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = PAGE.replace("__REPO__", REPO).replace("__VIDEO__", vhtml).replace("__DATA__", payload)
    (out / "index.html").write_text(html)
    (out / ".nojekyll").write_text("")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--out", default=str(ROOT / "docs"))
    ap.add_argument("--video", default="")
    a = ap.parse_args()
    build(Path(a.run), Path(a.out), Path(a.video) if a.video else None)
    print(f"site written to {a.out}")


if __name__ == "__main__":
    main()
