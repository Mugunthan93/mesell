#!/usr/bin/env python3
"""tokcap dashboard v2 — tabs: Overview + one per model. Self-contained, offline, no deps."""
import subprocess, re, datetime, sqlite3, os, html as H

METER="/tmp/mesell-wt/tokcap/docs/plans/experiments/token-capacity-discovery/tools/tokcap_meter.py"
DB=os.path.expanduser("~/.tokcap/ledger.db")

def live():
    out=subprocess.run(["python3",METER,"--force"],capture_output=True,text=True).stdout
    bars={}
    for ln in out.splitlines():
        m=re.match(r'\s+(session|weekly_all|weekly_scoped)\s+(?:\[(\w+)\]\s+)?([\d.]+)%.*resets=\S*T(\d\d:\d\d)',ln)
        if m: bars[m.group(1)]=(float(m.group(3)),m.group(4))
    return bars
B=live(); ses,srst=B.get('session',(0,'?')); wk,_=B.get('weekly_all',(0,'?')); fb,_=B.get('weekly_scoped',(0,'?'))
ts=datetime.datetime.utcnow().strftime('%d %b %Y · %H:%M UTC')

HELP={
 "tank5":"Your 5-hour budget. It opens at your first message and refills 5 hours later. Every model draws from this same tank.",
 "tankw":"The bigger weekly budget sitting above the 5-hour tanks. Even with refills every 5h, the week has its own ceiling. Resets weekly.",
 "tankf":"Fable-class models have their OWN weekly ceiling in addition to the shared weekly tank.",
 "ruler":"Our common yardstick: 1% of the 5-hour tank ≈ 5–6 cents of work. Every bar shows the SAME action, priced as % of the tank.",
 "pin":"API price per million tokens READ (input) and WRITTEN (output). The meter charges by these prices — that's the $-weighted rule.",
 "warmact":"Cost of one typical request while the session cache is WARM: your context is re-served at 0.1× price, so it's tiny.",
 "coldact":"The first request after the cache expired: the whole context must be re-written at 1.25× price. This is the expensive event.",
 "apt":"How many warm actions fit inside one full 5-hour tank if you did nothing else.",
 "otpt":"If you spent an entire tank ONLY on this model writing text — this many output tokens.",
 "drain":"How much faster this model empties the tank than Haiku, for identical work. Comes from the price ratio.",
 "pct1":"Measured price of one meter tick: moving the bar by 1% consumes ≈ $0.05–0.065 of API-equivalent work.",
 "tankfull":"What one whole window is worth if you paid per-use: about $5–6.5. That's your 100%.",
 "wmult":"The weekly ceiling is roughly 8–9 five-hour tanks worth of work (≈ $42–55).",
 "rule":"Proven in batch 4: two very different models paid the SAME dollars per 1% — so the bar counts dollars, not raw tokens.",
 "warmfree":"Cache reads are billed at one-tenth price, so continuing a live session barely moves the bar. Keep sessions alive.",
 "coldtax":"Restarting cold on Fable reloads your 78K-token workspace ≈ $1 ≈ one fifth of a tank — before any real work happens. This caused your original 40% jump.",
 "reqs":"How many API calls this model family has made on this Mac, from the local ledger (every call leaves a receipt).",
 "usd":"What all those calls would have cost if paid per-use. Your flat subscription covered it.",
 "share":"This model's slice of everything ever spent on this Mac.",
 "meas":"Solid bars: we actually fired this action on your account and watched the meter (titration batches).",
 "est":"Hatched bars: computed from the price rule — not yet fired for real. One cheap batch turns them solid.",
 "buys":"Same tank, different mileage: how far 100% goes if spent purely on each model's output.",
}
def i(k): return f'<sup class="i" data-help="{H.escape(HELP[k])}">i</sup>'


def ledger(fam_like):
    try:
        c=sqlite3.connect(DB)
        n,usd,bw=c.execute("SELECT COUNT(*),COALESCE(SUM(usd),0),COALESCE(SUM(bw),0) FROM requests WHERE model LIKE ?",(fam_like,)).fetchone()
        tot=c.execute("SELECT COALESCE(SUM(usd),1) FROM requests").fetchone()[0]
        return n,usd,bw,100*usd/tot
    except Exception: return 0,0,0,0

FAM={
 "haiku": dict(nice="Haiku", like="%haiku%", pin=1, pout=5, measured=True,
   blurb="The economy engine — chat, drafts, bulk and automation work. Nearly impossible to drain the tank with it.",
   rows=[("warm cache","27K",0.057,1,"$0.0033 · measured (batches 1/3)"),("cold start","28K",0.97,1,"$0.056 · measured (batch 1)")],
   tiles=[("$ in / $ out per 1M","$1 / $5"),("one warm action","$0.0033 → 0.057%"),("one cold start","$0.056 → ~1%"),
          ("warm actions per tank","≈ 1,700"),("output tokens per tank","≈ 1,000K"),("drain vs Haiku","1× (baseline)")]),
 "sonnet": dict(nice="Sonnet", like="%sonnet%", pin=3, pout=15, measured=True,
   blurb="The daily workhorse — solid quality at one-third of Opus drain. Best default for most work.",
   rows=[("warm cache","26K",0.139,1,"$0.0080 · measured (batches 2/3)"),("warm · effort HIGH","27K",0.243,1,"$0.0140 · measured (batch 2) — effort just writes more"),("cold start","27K",2.8,1,"$0.159 · measured (batch 2)")],
   tiles=[("$ in / $ out per 1M","$3 / $15"),("one warm action","$0.008 → 0.14%"),("one cold start","$0.159 → 2.8%"),
          ("warm actions per tank","≈ 700"),("output tokens per tank","≈ 350K"),("drain vs Haiku","≈ 3×")]),
 "opus": dict(nice="Opus", like="%opus%", pin=5, pout=25, measured=False,
   blurb="Heavy lifting — big builds, deep reviews, agent dispatches. Five times the Haiku drain; budget it.",
   rows=[("warm cache","27K",0.30,0,"~$0.017 · estimated (price rule)"),("cold start","28K",3.3,0,"~$0.19 · estimated")],
   tiles=[("$ in / $ out per 1M","$5 / $25"),("one warm action","~$0.017 → 0.3%"),("one cold start","~$0.19 → 3.3%"),
          ("warm actions per tank","≈ 340"),("output tokens per tank","≈ 210K"),("drain vs Haiku","≈ 5×")]),
 "fable": dict(nice="Fable", like="%fable%", pin=10, pout=50, measured=False,
   blurb="Maximum intelligence, maximum drain — thinking is always on and bills as output. Reserve for the hardest problems; keep it warm.",
   rows=[("warm · thinking","29K",2.3,0,"~$0.13 · estimated — thinking bills as output"),("cold start · thinking","30K",7.3,0,"~$0.42 · estimated — the 40%-mystery ingredient")],
   tiles=[("$ in / $ out per 1M","$10 / $50"),("one warm turn","~$0.13 → 2.3%"),("one cold start","~$0.42 → 7.3%"),
          ("turns per tank","≈ 44 warm"),("output tokens per tank","≈ 100K"),("drain vs Haiku","≈ 10×")]),
}
XMAX=8.0
def rrow(v,t,p,m,d,name=""):
    w=100*p/XMAX
    fit=(f"≈{round(1/p):d}× fit in 1%" if p<0.9 else ("≈ 1%" if p<1.15 else f"= {p:g}% each"))
    return (f'<div class="rr" data-tip="{H.escape((name+" · " if name else "")+v+" — "+d)}">'
            f'<div class="rl"><b>{name or v.split(" ")[0].title()}</b><span>{v}</span>{"" if m else "<em>est</em>"}</div>'
            f'<div class="rt"><div class="rf{"" if m else " dash"}" style="width:{w:.2f}%"></div></div>'
            f'<div class="rv"><b>{p:g}%</b><span>{t} tok · {fit}</span></div></div>')

overview_rows="\n".join(rrow(v,t,p,m,d,FAM[k]["nice"]) for k in FAM for (v,t,p,m,d) in FAM[k]["rows"])
AXIS='<div class="axis"><i style="left:0">0%</i><i style="left:12.5%;color:var(--mark)">1%</i><i style="left:25%">2%</i><i style="left:50%">4%</i><i style="left:75%">6%</i><i style="left:100%">8%</i></div>'
LEGEND=('<div class="legend"><span><i style="background:var(--acc)"></i>measured<sup class="i" data-help="__MEAS__">i</sup></span>'
 '<span><i style="background:repeating-linear-gradient(45deg,var(--acc2) 0 4px,transparent 4px 7px);border:1px solid var(--acc2)"></i>estimated<sup class="i" data-help="__EST__">i</sup></span>'
 '<span><i style="background:var(--mark)"></i>1% line</span></div>')

def model_tab(k):
    f=FAM[k]; n,usd,bw,share=ledger(f["like"])
    TH={"$ in / $ out per 1M":"pin","one warm action":"warmact","one warm turn":"warmact","one cold start":"coldact",
   "warm actions per tank":"apt","turns per tank":"apt","output tokens per tank":"otpt","drain vs Haiku":"drain"}
    tiles="".join(f'<div class="tile"><div class="k">{a}{i(TH[a]) if a in TH else ""}</div><div class="v" style="font-size:19px">{b}</div></div>' for a,b in f["tiles"])
    rows="\n".join(rrow(v,t,p,m,d) for (v,t,p,m,d) in f["rows"])
    extra=(f'<div class="g" style="margin-top:14px"><div class="t"><span>Weekly tank · Fable only (live){i("tankf")}</span><b>{fb:g}%</b></div>'
           f'<div class="tr"><div class="fl" style="width:{fb}%"></div></div></div>') if k=="fable" else ""
    badge='<span class="ok">measured</span>' if f["measured"] else '<span class="est2">estimated — not yet dosed</span>'
    return f"""<section id="tab-{k}" class="tab">
<h2>{f["nice"]} {badge}</h2>
<p class="desc">{f["blurb"]}</p>
<div class="tiles">{tiles}</div>
<h3>The same action on {f["nice"]} vs the 1% line</h3>
<div class="panel">{AXIS}{rows}{LEGEND}</div>
<h3>Lifetime on this Mac (from the ledger)</h3>
<div class="tiles">
 <div class="tile"><div class="k">requests{i("reqs")}</div><div class="v">{n:,}</div></div>
 <div class="tile"><div class="k">work done ($-equiv){i("usd")}</div><div class="v">${usd:,.0f}</div></div>
 <div class="tile"><div class="k">share of all spend{i("share")}</div><div class="v">{share:.0f}%</div></div>
</div>{extra}</section>"""

model_tabs="\n".join(model_tab(k) for k in FAM)
mrows="\n".join(f'<div class="rr"><div class="rl"><b>{n}</b><span>output tokens / tank</span></div>'
 f'<div class="rt"><div class="rf" style="width:{w}%"></div></div><div class="rv"><b>{v}</b></div></div>'
 for n,w,v in [("Haiku",100,"≈ 1,000K"),("Sonnet",35,"≈ 350K"),("Opus",21,"≈ 210K"),("Fable",10,"≈ 100K")])

HEAD="""<title>tokcap · Token Discovery</title>
<style>
:root { --bg:#f7f6f3; --card:#fff; --ink:#191919; --mut:#6d6963; --line:#e5e2dc; --acc:#3d6fe0; --acc2:#9db9f2;
 --track2:#efede8; --mark:#c2410c; --chip:#f1efe9; --good:#2e7d4f; }
@media (prefers-color-scheme:dark) { :root { --bg:#141416; --card:#1e1e21; --ink:#ebebeb; --mut:#9d9a94; --line:#2d2d32;
 --acc:#7aa2ff; --acc2:#44577e; --track2:#26262b; --mark:#f59e0b; --chip:#26262b; --good:#5ec98a; } }
:root[data-theme="dark"] { --bg:#141416; --card:#1e1e21; --ink:#ebebeb; --mut:#9d9a94; --line:#2d2d32; --acc:#7aa2ff; --acc2:#44577e; --track2:#26262b; --mark:#f59e0b; --chip:#26262b; --good:#5ec98a; }
* { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 -apple-system,system-ui,"Segoe UI",sans-serif; }
.wrap { max-width:900px; margin:0 auto; padding:24px 20px 60px; }
header { display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 16px; }
header h1 { font-size:24px; margin:0; } header .sub { color:var(--mut); font-size:13px; }
nav { display:flex; gap:6px; margin:16px 0 20px; flex-wrap:wrap; }
nav button { font:600 13.5px/1 inherit; padding:9px 15px; border-radius:20px; border:1px solid var(--line);
 background:var(--card); color:var(--mut); cursor:pointer; }
nav button.on { background:var(--acc); border-color:var(--acc); color:#fff; }
.tab { display:none; } .tab.on { display:block; }
.gauges { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:10px; margin:0 0 26px; }
.g { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px 14px; }
.g .t { display:flex; justify-content:space-between; font-size:12.5px; color:var(--mut); margin-bottom:7px; }
.g .t b { color:var(--ink); font-size:15px; font-variant-numeric:tabular-nums; }
.g .tr { height:10px; background:var(--track2); border-radius:5px; overflow:hidden; }
.g .fl { height:100%; background:var(--acc); border-radius:0 5px 5px 0; }
h2 { font-size:18px; margin:6px 0 4px; } h3 { font-size:14.5px; margin:26px 0 8px; }
.desc { color:var(--mut); font-size:13.5px; margin:0 0 14px; }
.panel { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 16px 10px; }
.axis { position:relative; height:20px; margin:0 172px 4px 178px; color:var(--mut); font-size:11px; }
.axis i { position:absolute; transform:translateX(-50%); font-style:normal; }
.rr { display:grid; grid-template-columns:170px 1fr 164px; gap:8px 14px; align-items:center; padding:7px 0; border-top:1px solid var(--line); }
.rr:first-of-type { border-top:none; }
.rl b { font-size:14px; } .rl span { display:block; color:var(--mut); font-size:12px; }
.i { cursor:help; display:inline-block; min-width:13px; height:13px; line-height:13px; text-align:center;
 font:600 9.5px/13px inherit; color:var(--mut); border:1px solid var(--line); border-radius:50%; margin-left:6px; vertical-align:2px; }
.i:hover { color:#fff; background:var(--acc); border-color:var(--acc); }
.rl em { font-style:normal; font-size:10.5px; color:var(--mut); background:var(--chip); border-radius:4px; padding:1px 5px; margin-left:6px; }
.rt { position:relative; height:16px; background:var(--track2); border-radius:4px; }
.rt::after { content:""; position:absolute; left:12.5%; top:-5px; bottom:-5px; width:2px; background:var(--mark); }
.rf { position:absolute; inset:0 auto 0 0; background:var(--acc); border-radius:0 4px 4px 0; min-width:2px; }
.rf.dash { background:repeating-linear-gradient(45deg,var(--acc2) 0 6px,transparent 6px 10px); border:1px solid var(--acc2); }
.rv { text-align:right; font-variant-numeric:tabular-nums; } .rv b { font-size:14.5px; }
.rv span { display:block; color:var(--mut); font-size:11.5px; }
.legend { display:flex; gap:18px; color:var(--mut); font-size:12px; margin:10px 2px 2px; flex-wrap:wrap; }
.legend i { display:inline-block; width:11px; height:11px; border-radius:3px; margin-right:5px; vertical-align:-1px; }
.tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:10px; }
.tile { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:13px 15px; }
.tile .k { color:var(--mut); font-size:11.5px; text-transform:uppercase; letter-spacing:.05em; }
.tile .v { font-size:22px; font-weight:650; margin:3px 0 1px; font-variant-numeric:tabular-nums; }
.tile .n { color:var(--mut); font-size:12.5px; }
.ok { font-size:11px; color:var(--good); border:1px solid var(--good); border-radius:5px; padding:2px 7px; vertical-align:3px; margin-left:8px; }
.est2 { font-size:11px; color:var(--mut); border:1px solid var(--line); border-radius:5px; padding:2px 7px; vertical-align:3px; margin-left:8px; }
#tip { position:fixed; display:none; max-width:300px; background:var(--ink); color:var(--bg); font-size:12.5px; padding:8px 11px; border-radius:8px; pointer-events:none; z-index:9; }
footer { color:var(--mut); font-size:12px; margin-top:34px; }
@media (max-width:680px) { .rr { grid-template-columns:1fr; gap:4px; } .rv { text-align:left; } .axis { display:none; } }
</style>"""

SCRIPT="""<div id="tip"></div>
<script>
const tip=document.getElementById('tip');
function wireI(){document.querySelectorAll('.i[data-help]').forEach(s=>{
 const show=e=>{tip.style.display='block';tip.textContent=s.dataset.help;
  tip.style.left=Math.min(e.clientX+14,innerWidth-310)+'px';tip.style.top=(e.clientY+14)+'px';e.stopPropagation();};
 s.onmousemove=show; s.onclick=show; s.onmouseleave=()=>tip.style.display='none';});}
document.body.addEventListener('click',()=>tip.style.display='none');
function wire(){wireI();document.querySelectorAll('.rr[data-tip]').forEach(r=>{
 r.onmousemove=e=>{tip.style.display='block';tip.textContent=r.dataset.tip;
  tip.style.left=Math.min(e.clientX+14,innerWidth-310)+'px';tip.style.top=(e.clientY+14)+'px';};
 r.onmouseleave=()=>tip.style.display='none';});}
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('nav button').forEach(x=>x.classList.remove('on'));
 document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
 b.classList.add('on'); document.getElementById('tab-'+b.dataset.t).classList.add('on');
 tip.style.display='none';});
wire();
</script>"""

body=f"""<div class="wrap">
<header><h1>tokcap</h1><div class="sub">Token Discovery · Pro plan · fitted 18 Jul 2026 · refreshed {ts}</div></header>
<nav>
 <button class="on" data-t="overview">Overview</button>
 <button data-t="haiku">Haiku</button><button data-t="sonnet">Sonnet</button>
 <button data-t="opus">Opus</button><button data-t="fable">Fable</button>
</nav>

<section id="tab-overview" class="tab on">
<div class="gauges">
 <div class="g"><div class="t"><span>Session tank (5h){i("tank5")} · refills {srst} UTC</span><b>{ses:g}%</b></div><div class="tr"><div class="fl" style="width:{ses}%"></div></div></div>
 <div class="g"><div class="t"><span>Weekly tank · all models{i("tankw")}</span><b>{wk:g}%</b></div><div class="tr"><div class="fl" style="width:{wk}%"></div></div></div>
 <div class="g"><div class="t"><span>Weekly tank · Fable only{i("tankf")}</span><b>{fb:g}%</b></div><div class="tr"><div class="fl" style="width:{fb}%"></div></div></div>
</div>
<h2>📏 The 1% Ruler {i("ruler")}</h2>
<p class="desc">The <b style="color:var(--mark)">orange line = 1%</b> of your 5-hour tank (≈ 5–6¢ of work). Same identical action on every row — only model &amp; settings change. Hover rows for details; click a model tab for the deep dive.</p>
<div class="panel">{AXIS}{overview_rows}{LEGEND}</div>
<h3>⛽ What one full tank buys {i("buys")}</h3>
<div class="panel">{mrows}</div>
<h3>🎯 Constants</h3>
<div class="tiles">
 <div class="tile"><div class="k">1% of the tank{i("pct1")}</div><div class="v">$0.0575</div><div class="n">5–6 cents of work</div></div>
 <div class="tile"><div class="k">Full 5h tank{i("tankfull")}</div><div class="v">$5 – 6.5</div><div class="n">per-use value of one window</div></div>
 <div class="tile"><div class="k">Weekly tank{i("wmult")}</div><div class="v">8 – 9×</div><div class="n">≈ $42–55 / week</div></div>
 <div class="tile"><div class="k">Meter rule{i("rule")}</div><div class="v">$-weighted</div><div class="n">charges by price (ratio 1.04)</div></div>
 <div class="tile"><div class="k">Warm session{i("warmfree")}</div><div class="v">≈ free</div><div class="n">cache reads 0.1×</div></div>
 <div class="tile"><div class="k">Cold start (Fable){i("coldtax")}</div><div class="v">~20%</div><div class="n">78K reload ≈ $1 — the 40% mystery</div></div>
</div>
</section>
{model_tabs}
<footer>Measured from server receipts + live meter · 4 batches, 33 doses, ≈ $1.20 · branch <code>chore/token-capacity-discovery/plan</code></footer>
</div>"""
page=HEAD+body+SCRIPT
page=page.replace("__MEAS__",H.escape(HELP["meas"])).replace("__EST__",H.escape(HELP["est"]))
open('/tmp/tokcap-poc/tokcap_dashboard.html','w').write(page)
print("v2 tabs written · live:",ses,wk,fb,srst)
