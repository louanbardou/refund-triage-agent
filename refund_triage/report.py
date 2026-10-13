"""Static HTML review screen + results table. Self-contained, no server needed.

The screen shows what a support agent would see: the customer email, the facts the agent
retrieved, and the draft beside them, with Approve / Revise / Escalate buttons. The buttons
only record a choice in the browser (localStorage); nothing is ever sent.
"""
import json

from .scoring import score

_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Refund triage review</title>
<style>
:root{--bg:#f4f2ee;--card:#fff;--ink:#17233b;--mute:#667085;--line:#e3e0d8;--navy:#0f2a4d;--btn:#0f2a4d;--ok:#1d7a4d;--bad:#b3261e;--warn:#9a6700;
--approve:#1d7a4d;--store:#2b6cb0;--reject:#b3261e;--ask:#9a6700;--escalate:#6b3fa0}
@media (prefers-color-scheme:dark){:root{--bg:#111722;--card:#1a2332;--ink:#e8edf5;--mute:#9aa7bb;--line:#2a364a;--navy:#8fb4ff;--btn:#2f5fb8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif}
header{padding:20px 16px 8px;max-width:1200px;margin:0 auto}h1{font:600 22px Georgia,serif;margin:0;color:var(--navy)}
.sim{color:var(--mute);font-size:13px;margin-top:4px}
main{max-width:1200px;margin:0 auto;padding:0 16px 40px}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden;font-size:14px}
th,td{padding:8px 10px;text-align:right;border-bottom:1px solid var(--line)}th:first-child,td:first-child{text-align:left}
th{color:var(--mute);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:18px 0 10px}
.tab{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:6px 12px;border-radius:999px;cursor:pointer;font:inherit}
.tab.on{background:var(--btn);color:#fff;border-color:var(--btn)}
.filters{display:flex;gap:10px;align-items:center;color:var(--mute);font-size:13px;margin-bottom:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:12px 0;overflow:hidden}
.head{display:flex;gap:10px;align-items:center;padding:10px 14px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.id{font-weight:700}.sub{color:var(--mute)}
.badge{padding:2px 9px;border-radius:999px;color:#fff;font-size:12px;font-weight:600}
.cols{display:grid;grid-template-columns:1fr 1fr 1.2fr;gap:0}
.col{padding:12px 14px;border-right:1px solid var(--line);min-width:0}.col:last-child{border-right:0}
.col h3{margin:0 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute)}
pre{white-space:pre-wrap;word-break:break-word;margin:0;font:13px/1.5 ui-monospace,Menlo,monospace}
.draft{white-space:pre-wrap}
.note{margin-top:8px;font-size:13px;color:var(--mute)}
.pill{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:6px;padding:1px 6px;margin:2px 4px 2px 0}
.fail{color:var(--bad);font-weight:600}.pass{color:var(--ok);font-weight:600}
.actions{display:flex;gap:8px;padding:10px 14px;border-top:1px solid var(--line);align-items:center;flex-wrap:wrap}
button.act{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:6px 12px;border-radius:8px;cursor:pointer;font:inherit}
button.act.primary{background:var(--btn);color:#fff;border-color:var(--btn)}
.chosen{font-size:13px;color:var(--ok)}
@media (max-width:900px){.cols{grid-template-columns:1fr}.col{border-right:0;border-bottom:1px solid var(--line)}}
</style></head><body>
<header><h1>Refund triage: staff review</h1>
<div class="sim">Simulation on synthetic data. Approve / Revise / Escalate only record your choice in this browser; nothing is sent.</div></header>
<main>
<div id="summary"></div>
<div class="tabs" id="tabs"></div>
<div class="filters"><label><input type="checkbox" id="onlyfail"> show only tickets that failed a check</label></div>
<div id="cards"></div>
</main>
<script>
const DATA = __DATA__;
const COLORS={approve_refund:'var(--approve)',store_credit:'var(--store)',reject:'var(--reject)',ask_info:'var(--ask)',escalate:'var(--escalate)'};
const LABELS={b0_templates:'B0 templates',b1_access:'B1 access (paste)',b1_access_days:'B1d paste + day counts',agent:'Agent + check',agent_no_reflection:'Agent, no check'};
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
const store={get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
const H=new URLSearchParams(location.hash.slice(1));  // video frames: #view=summary | #view=card&only=T06&system=agent&zoom=1.4
let current=DATA.systems.includes('agent')?'agent':DATA.systems[0];
if(H.get('system')&&DATA.systems.includes(H.get('system')))current=H.get('system');

function summary(){
  const box=document.getElementById('summary');box.textContent='';
  const t=el('table');const cols=['system','task success [95% CI]','decision acc.','wrong $ decisions','latency mean / p95 (s)','cost / ticket ($)','staff min / ticket'];
  const hr=el('tr');cols.forEach(c=>hr.appendChild(el('th','',c)));t.appendChild(hr);
  const row=(n,v)=>{const r=el('tr');n.concat(v).forEach(x=>r.appendChild(el('td','',x)));t.appendChild(r)};
  DATA.systems.forEach(s=>{const m=DATA.summary[s];
    row([LABELS[s]||s],[(m.task_success*100).toFixed(0)+'% ['+(m.task_success_ci95[0]*100).toFixed(0)+'-'+(m.task_success_ci95[1]*100).toFixed(0)+']',(m.decision_accuracy*100).toFixed(0)+'%',m.wrong_money_decisions,m.latency_mean_s+' / '+m.latency_p95_s,m.cost_per_ticket_usd.toFixed(5),m.staff_minutes_per_ticket.toFixed(2)])});
  row(['Fully manual (assumption)'],['','','','','',DATA.summary.manual.staff_minutes_per_ticket.toFixed(2)]);
  box.appendChild(t);
}
function tabs(){const b=document.getElementById('tabs');b.textContent='';
  DATA.systems.forEach(s=>{const x=el('button','tab'+(s===current?' on':''),LABELS[s]||s);x.onclick=()=>{current=s;tabs();cards()};b.appendChild(x)})}
function cards(){
  const box=document.getElementById('cards');box.textContent='';
  const only=document.getElementById('onlyfail').checked;
  DATA.rows.filter(r=>r.system===current).forEach(r=>{
    if(only&&r.score.success)return;
    if(H.get('only')&&r.ticket_id!==H.get('only'))return;
    const t=DATA.tickets[r.ticket_id],res=r.result;
    const c=el('div','card');
    const h=el('div','head');h.appendChild(el('span','id',r.ticket_id));h.appendChild(el('span','sub',t.subject));
    const bd=el('span','badge',res.decision);bd.style.background=COLORS[res.decision]||'#555';h.appendChild(bd);
    if(res.refund_amount!=null)h.appendChild(el('span','pill',res.refund_amount+' EUR'));
    (res.rules_cited||[]).forEach(x=>h.appendChild(el('span','pill',x)));
    const ok=r.score.success;const v=el('span',ok?'pass':'fail',ok?'checks passed':'failed: '+r.score.failed.join(', '));v.style.marginLeft='auto';h.appendChild(v);c.appendChild(h);
    const cols=el('div','cols');
    const c1=el('div','col');c1.appendChild(el('h3','','Customer email'));const p=el('pre','','From: '+t.from_email+'\n\n'+t.body);c1.appendChild(p);cols.appendChild(c1);
    const c2=el('div','col');c2.appendChild(el('h3','','Facts the system used'));
    if(r.tool_calls.length){r.tool_calls.forEach(tc=>{c2.appendChild(el('div','pill',tc.tool+'('+Object.values(tc.input).join(',')+')'));c2.appendChild(el('pre','',JSON.stringify(tc.output,null,1)))})}
    else c2.appendChild(el('div','sub','No lookups (this system has no tools).'));
    (res.evidence||[]).forEach(x=>c2.appendChild(el('div','note','• '+x)));cols.appendChild(c2);
    const c3=el('div','col');c3.appendChild(el('h3','','Draft reply (review required)'));c3.appendChild(el('div','draft',res.draft_reply||'(no draft)'));
    if(res.internal_note)c3.appendChild(el('div','note','Note for reviewer: '+res.internal_note));
    (r.guardrail_notes||[]).forEach(x=>c3.appendChild(el('div','note fail','Guardrail: '+x)));
    if(r.reflection&&r.reflection.ok===false)c3.appendChild(el('div','note','Check revised the draft: '+(r.reflection.issues||[]).join('; ')));
    c3.appendChild(el('div','note','Evaluation label (not shown to staff in production): '+t.expected.decision+' ('+t.expected.rules.join(', ')+')'));
    cols.appendChild(c3);c.appendChild(cols);
    const a=el('div','actions');const key='choice:'+current+':'+r.ticket_id;const ch=el('span','chosen',store.get(key)?'Recorded: '+store.get(key):'');
    [['Approve + send','primary'],['Revise',''],['Escalate to manager','']].forEach(([lab,cls])=>{const b=el('button','act '+cls,lab);b.onclick=()=>{store.set(key,lab);ch.textContent='Recorded: '+lab+' (simulation, nothing sent)'};a.appendChild(b)});
    a.appendChild(ch);c.appendChild(a);box.appendChild(c)});
}
document.getElementById('onlyfail').onchange=cards;summary();tabs();cards();
(function(){const v=H.get('view'),hide=id=>{const e=document.getElementById(id);if(e)e.style.display='none'};
 if(v==='summary'){['tabs','cards'].forEach(hide);document.querySelector('.filters').style.display='none'}
 if(v==='card'){['summary','tabs'].forEach(hide);document.querySelector('.filters').style.display='none'}
 if(H.get('theme')==='light'){const st=document.createElement('style');st.textContent=':root{--bg:#f4f2ee;--card:#fff;--ink:#17233b;--mute:#667085;--line:#e3e0d8;--navy:#0f2a4d;--btn:#0f2a4d}';document.head.appendChild(st)}
 if(H.get('zoom'))document.body.style.zoom=H.get('zoom')})();
</script></body></html>"""


def build_data(tickets: list, records: list, summary: dict) -> dict:
    by_id = {t["ticket_id"]: t for t in tickets}
    rows = []
    for r in records:
        if r.get("repeat", 0) != 0:
            continue
        rows.append({"ticket_id": r["ticket_id"], "system": r["system"], "result": r["result"],
                     "tool_calls": r["tool_calls"], "guardrail_notes": r["guardrail_notes"],
                     "reflection": r.get("reflection"), "latency_s": r["latency_s"], "usage": r["usage"],
                     "score": score(by_id[r["ticket_id"]], r)})
    systems = [s for s in summary if not s.startswith("_") and s != "manual"]
    return {"tickets": by_id, "rows": rows, "summary": summary, "systems": systems}


def write_html(path, tickets: list, records: list, summary: dict) -> None:
    payload = json.dumps(build_data(tickets, records, summary), ensure_ascii=False).replace("</", "<\\/")
    path.write_text(_PAGE.replace("__DATA__", payload))
