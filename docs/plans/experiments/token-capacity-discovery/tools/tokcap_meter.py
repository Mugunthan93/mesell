#!/usr/bin/env python3
"""tokcap meter_snapshotter — live % sensor (route b: OAuth usage endpoint).

Reads Claude Code's own OAuth token from the macOS Keychain (service
"Claude Code-credentials", acct=<login user> — NOT the stale acct=root item),
GETs https://api.anthropic.com/api/oauth/usage, and records every limit bar
into ~/.tokcap/ledger.db :: meter_snapshots. The token is never printed/stored.

Usage:
  tokcap_meter.py                  snapshot + print bars
  tokcap_meter.py --guard 90       also exit 1 if session bar >= 90% (spend guard)
  tokcap_meter.py --force          bypass the 60s courtesy floor (endpoint 429s on rapid polls)
  tokcap_meter.py --db PATH        alternate ledger
"""
import json, os, sqlite3, subprocess, sys, time, datetime, getpass, urllib.request

MIN_INTERVAL_S = 60
UA = "claude-cli/2.1.211 (external, cli)"

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def get_token():
    for acct in dict.fromkeys([getpass.getuser(), "mugunthansrinivasan"]):
        try:
            raw = subprocess.run(
                ["security","find-generic-password","-s","Claude Code-credentials","-a",acct,"-w"],
                capture_output=True, text=True, check=True).stdout.strip()
            o = json.loads(raw)["claudeAiOauth"]
            if o.get("expiresAt", 0) > time.time()*1000 + 60_000:
                return o["accessToken"]
        except Exception:
            continue
    sys.exit("ERROR: no fresh token in Keychain — run any `claude` command (refreshes it), then retry")

def fetch():
    req = urllib.request.Request("https://api.anthropic.com/api/oauth/usage", headers={
        "Authorization": f"Bearer {get_token()}",
        "User-Agent": UA, "anthropic-beta": "oauth-2025-04-20"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def ensure(con):
    con.execute("""CREATE TABLE IF NOT EXISTS meter_snapshots(
        snapshot_id INTEGER PRIMARY KEY, ts TEXT NOT NULL, kind TEXT NOT NULL,
        grp TEXT, percent REAL, severity TEXT, resets_at TEXT,
        scope_model TEXT, is_active INT, source TEXT NOT NULL DEFAULT 'oauth')""")

def rows_from(d):
    ts = now_iso(); out = []
    for l in d.get("limits") or []:
        sc = ((l.get("scope") or {}).get("model") or {})
        out.append((ts, l.get("kind"), l.get("group"), l.get("percent"), l.get("severity"),
                    l.get("resets_at"), sc.get("display_name"), 1 if l.get("is_active") else 0, "oauth"))
    if not out:  # fallback shape
        for k in ("five_hour","seven_day"):
            b = d.get(k)
            if isinstance(b, dict):
                out.append((ts, k, None, b.get("utilization"), None, b.get("resets_at"), None, None, "oauth"))
    return out

def main():
    a = sys.argv[1:]
    guard = float(a[a.index("--guard")+1]) if "--guard" in a else None
    force = "--force" in a
    db = os.path.expanduser(a[a.index("--db")+1] if "--db" in a else "~/.tokcap/ledger.db")
    os.makedirs(os.path.dirname(db), exist_ok=True)
    con = sqlite3.connect(db); ensure(con)

    last = con.execute("SELECT MAX(ts) FROM meter_snapshots WHERE source='oauth'").fetchone()[0]
    fresh_needed = True
    if last and not force:
        age = (datetime.datetime.now(datetime.timezone.utc)
               - datetime.datetime.fromisoformat(last)).total_seconds()
        if age < MIN_INTERVAL_S:
            print(f"(cache) last snapshot {age:.0f}s ago — reusing (courtesy floor {MIN_INTERVAL_S}s; --force to override)")
            fresh_needed = False
    if fresh_needed:
        con.executemany("INSERT INTO meter_snapshots(ts,kind,grp,percent,severity,resets_at,scope_model,is_active,source) VALUES(?,?,?,?,?,?,?,?,?)",
                        rows_from(fetch()))
        con.commit()

    ts, = con.execute("SELECT MAX(ts) FROM meter_snapshots WHERE source='oauth'").fetchone()
    bars = con.execute("""SELECT kind, grp, percent, severity, resets_at, scope_model
                          FROM meter_snapshots WHERE ts=? AND source='oauth'""",(ts,)).fetchall()
    print(f"METER @ {ts}")
    sess_pct = None
    for kind, grp, pct, sev, resets, scope in bars:
        tag = f" [{scope}]" if scope else ""
        print(f"  {kind:14s}{tag:9s} {pct if pct is not None else '?':>5}%  sev={sev or '-':8s} resets={resets or '?'}")
        if kind in ("session","five_hour") and pct is not None:
            sess_pct = pct
    if guard is not None:
        if sess_pct is None:
            print("GUARD: session bar missing -> PROCEED (warn)"); return
        verdict = "ABORT" if sess_pct >= guard else "PROCEED"
        print(f"GUARD: session {sess_pct}% vs {guard}% -> {verdict}")
        if verdict == "ABORT": sys.exit(1)

if __name__ == "__main__":
    main()
