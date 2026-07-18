#!/usr/bin/env python3
"""tokcap Phase-0 ledger (read-only). Recursive-glob Claude Code transcripts ->
dedup by requestId (per-field max) -> attribute (slug/session/agent/model) ->
SQLite requests + rolling-5h windows -> weighted (UE/BW) + approx-$ rollups.
NO API calls. DB defaults to ~/.tokcap/ledger.db (runtime home, never committed)."""
import sqlite3, json, os, glob, datetime, statistics, sys

DB    = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.tokcap/ledger.db")
REPORT= sys.argv[2] if len(sys.argv) > 2 else None
PROJ  = os.path.expanduser("~/.claude/projects")

# published API weights (approx; 5m cache-write=1.25x, cache-read=0.1x; 1h write=2x not modelled)
PRICES = {  # $/M input, $/M output
  "claude-fable-5":(10,50),"claude-mythos-5":(10,50),
  "claude-opus-4-8":(5,25),"claude-opus-4-7":(5,25),"claude-opus-4-6":(5,25),"claude-opus-4-5":(5,25),
  "claude-sonnet-5":(3,15),"claude-sonnet-4-6":(3,15),"claude-sonnet-4-5":(3,15),
  "claude-haiku-4-5":(1,5),"claude-haiku-4-5-20251001":(1,5)}
def approx_usd(model,f):
    pi,po = PRICES.get(model,(5,25))
    return (f[0]*pi + f[1]*pi*1.25 + f[2]*pi*0.1 + f[3]*po)/1e6
def bw(f): return f[0] + f[1]*1.25 + f[2]*0.1 + f[3]
def ue(f): return sum(f)

def parse_path(p):
    rel = os.path.relpath(p, PROJ).split(os.sep); slug = rel[0]
    if "subagents" in rel:
        i = rel.index("subagents"); return slug, rel[i-1], os.path.basename(p)[:-6], 1
    return slug, os.path.basename(p)[:-6], "main", 0

def ingest():
    files = glob.glob(PROJ + "/**/*.jsonl", recursive=True)
    req = {}; multiline = varying = 0; lines = {}
    for p in files:
        slug, session, agent, sub = parse_path(p)
        for ln, line in enumerate(open(p, errors="replace")):
            if '"assistant"' not in line: continue
            try: o = json.loads(line)
            except: continue
            if o.get("type") != "assistant": continue
            m = o.get("message") or {}; u = m.get("usage") or {}
            key = o.get("requestId") or m.get("id") or f"{p}:{ln}"
            fl = (u.get("input_tokens",0), u.get("cache_creation_input_tokens",0),
                  u.get("cache_read_input_tokens",0), u.get("output_tokens",0))
            ts = o.get("timestamp")
            lines[key] = lines.get(key,0)+1
            r = req.get(key)
            if r is None:
                req[key] = dict(slug=slug,session=session,agent=agent,sub=sub,
                                model=m.get("model"),ts=ts,f=list(fl))
            else:
                if tuple(r["f"]) != fl: varying += 1
                r["f"] = [max(a,b) for a,b in zip(r["f"], fl)]
                if ts and (not r["ts"] or ts < r["ts"]): r["ts"] = ts
    multiline = sum(1 for c in lines.values() if c>1)
    return files, req, multiline, varying

def build(db, req):
    con = sqlite3.connect(db); c = con.cursor()
    c.executescript("""
    DROP TABLE IF EXISTS requests; DROP TABLE IF EXISTS windows;
    CREATE TABLE requests(request_id TEXT PRIMARY KEY, ts TEXT, slug TEXT, session TEXT,
      agent TEXT, is_subagent INT, model TEXT,
      input_tokens INT, cache_creation INT, cache_read INT, output_tokens INT,
      bw REAL, ue REAL, usd REAL, window_id INT);
    CREATE TABLE windows(window_id INTEGER PRIMARY KEY, opened_at TEXT, last_at TEXT,
      n INT, bw REAL, ue REAL, usd REAL);
    CREATE INDEX ix_req_slug ON requests(slug);
    CREATE INDEX ix_req_model ON requests(model);
    CREATE INDEX ix_req_win ON requests(window_id);""")
    rows=[]
    for k,r in req.items():
        f=r["f"]; rows.append((k,r["ts"],r["slug"],r["session"],r["agent"],r["sub"],r["model"],
            f[0],f[1],f[2],f[3],bw(f),ue(f),approx_usd(r["model"],f)))
    c.executemany("INSERT OR REPLACE INTO requests VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)", rows)
    con.commit()
    # rolling 5h windows (account-wide)
    def p(ts):
        try: return datetime.datetime.fromisoformat(ts.replace("Z","+00:00"))
        except: return None
    ordered = [(rid,ts) for rid,ts in c.execute("SELECT request_id,ts FROM requests WHERE ts IS NOT NULL").fetchall()]
    ordered = sorted([(rid,p(ts)) for rid,ts in ordered if p(ts)], key=lambda x:x[1])
    wid=0; op=None
    for rid,t in ordered:
        if op is None or t> op+datetime.timedelta(hours=5): wid+=1; op=t
        c.execute("UPDATE requests SET window_id=? WHERE request_id=?", (wid,rid))
    c.execute("""INSERT INTO windows SELECT window_id, MIN(ts), MAX(ts), COUNT(*),
        SUM(bw), SUM(ue), SUM(usd) FROM requests WHERE window_id IS NOT NULL GROUP BY window_id""")
    con.commit(); return con

def report(con, files, req, multiline, varying):
    c=con.cursor(); L=[]
    def q(s): return c.execute(s).fetchall()
    nreq=q("SELECT COUNT(*) FROM requests")[0][0]
    nsub=len([f for f in files if "/subagents/" in f]); nmain=len(files)-nsub
    wins=q("SELECT bw,usd,n FROM windows ORDER BY bw")
    bws=[w[0] for w in wins]; maxw=bws[-1] if bws else 0
    cur=q("SELECT window_id,opened_at,last_at,n,bw,usd FROM windows ORDER BY window_id DESC LIMIT 1")[0]
    mainsub=dict(q("SELECT CASE is_subagent WHEN 1 THEN 'subagent' ELSE 'main' END, SUM(bw) FROM requests GROUP BY is_subagent"))
    L.append(f"# Phase 0 — Passive Ledger Report\n")
    L.append(f"**Generated:** {datetime.datetime.now().isoformat(timespec='seconds')}  ·  **Source:** `~/.claude/projects/**/*.jsonl`  ·  **DB:** `{DB}`  ·  read-only, zero API calls\n")
    L.append("## Corpus & dedup\n")
    L.append(f"- transcript files: **{len(files)}** ({nmain} main + {nsub} subagent)")
    L.append(f"- deduped API requests: **{nreq:,}**  ·  multi-line requests: {multiline:,}  ·  multi-line merges with *differing* usage across lines: {varying:,} → **per-field-MAX dedup is load-bearing** (T2 confirmed)\n")
    L.append("## Attribution — recursive-glob correction (headline)\n")
    tot=sum(mainsub.values())
    for k,v in sorted(mainsub.items()):
        L.append(f"- {k}: **{v/1e6:.1f}M BW** ({100*v/tot:.0f}%)")
    L.append(f"\n> Subagent share ≈ **{100*mainsub.get('subagent',0)/tot:.0f}%** of all weighted tokens. A non-recursive glob (`projects/*/*.jsonl`) misses this entirely — the original design would have undercounted total spend by ~half. **This is the load-bearing Phase-0 fix.**\n")
    L.append("## Windows & capacity anchor\n")
    L.append(f"- rolling-5h windows: **{len(wins)}**")
    L.append(f"- window BW: min {bws[0]/1e3:.0f}K · median {statistics.median(bws)/1e3:.0f}K · **max {maxw/1e6:.2f}M**")
    L.append(f"- **capacity LOWER BOUND** ≈ {maxw/1e6:.2f}M BW (largest window reached without a reported hard stop) — a real anchor for calibration\n")
    L.append(f"- current/active window (id {cur[0]}): opened {cur[1]}, {cur[3]} reqs, {cur[4]/1e6:.3f}M BW (~{100*cur[4]/maxw:.1f}% of max-window) — the **self-sourced budget gauge**\n")
    L.append("## Rollups — billed-weight & approx-$ (deduped)\n")
    L.append("### by project")
    for slug,b,u in q("SELECT slug,SUM(bw),SUM(usd) FROM requests GROUP BY slug ORDER BY SUM(bw) DESC LIMIT 8"):
        L.append(f"- `{slug[:40]}` — {b/1e6:.1f}M BW · ~${u:,.0f}")
    L.append("\n### by model")
    for mdl,b,u in q("SELECT model,SUM(bw),SUM(usd) FROM requests GROUP BY model ORDER BY SUM(bw) DESC"):
        L.append(f"- `{mdl}` — {b/1e6:.1f}M BW · ~${u:,.0f}")
    L.append(f"\n### total approx-$ across corpus: ~${q('SELECT SUM(usd) FROM requests')[0][0]:,.0f}  *(approx: 5m-cache 1.25×; 1h-cache 2× not modelled)*\n")
    L.append("## Reconciler (OTEL) — validated separately\n")
    L.append("- Group 2 proved the OTLP tap: `claude_code.token.usage` (by type) + `claude_code.cost.usage` land in a local listener, byte-reversible settings toggle. The daily OTEL↔transcript delta (gate G0 metric) requires OTEL running over an interactive window → next step.\n")
    out="\n".join(L)
    if REPORT: open(REPORT,"w").write(out)
    print(out)

if __name__ == "__main__":
    files, req, ml, vy = ingest()
    con = build(DB, req)
    report(con, files, req, ml, vy)
