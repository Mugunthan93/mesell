#!/usr/bin/env python3
"""Batch 2 — Sonnet effort/size sweep. Arms now, FIRES AFTER the 05:50Z reset.
Waits for reset, confirms fresh window (session<=20%), then doses with ceiling
15% of the fresh window (leave the day's budget intact). Same preflight logic."""
import json, subprocess, time, datetime, urllib.request, getpass, os
CEIL=45.0; LOG=os.path.expanduser('~/.tokcap/probe_batch2_20260718.ndjson')
UA="claude-cli/2.1.211 (external, cli)"; UTC=datetime.timezone.utc
def log(**kw):
    kw['t']=datetime.datetime.now(UTC).isoformat(timespec='seconds'); open(LOG,'a').write(json.dumps(kw)+'\n')
def token():
    raw=subprocess.run(["security","find-generic-password","-s","Claude Code-credentials","-a",getpass.getuser(),"-w"],capture_output=True,text=True,check=True).stdout.strip()
    return json.loads(raw)["claudeAiOauth"]["accessToken"]
def meter():
    for _ in range(3):
        try:
            req=urllib.request.Request("https://api.anthropic.com/api/oauth/usage",headers={"Authorization":f"Bearer {token()}","User-Agent":UA,"anthropic-beta":"oauth-2025-04-20"})
            with urllib.request.urlopen(req,timeout=15) as r: d=json.loads(r.read().decode())
            bars={l['kind']:l.get('percent') for l in d.get('limits',[])}; log(phase='meter',bars=bars); return bars
        except Exception as e: log(phase='meter_err',err=str(e)[:120]); time.sleep(45)
    return None
# effort flag support?
HELP=subprocess.run(["claude","--help"],capture_output=True,text=True).stdout
EFFORT_FLAG="--effort" in HELP
CELLS=([{"m":"claude-sonnet-4-6","tag":"son-default","args":[],"p":"reply with exactly: ok"}]*5
      +([{"m":"claude-sonnet-4-6","tag":"son-effort-high","args":["--effort","high"],"p":"solve step by step: 27*453"}]*5 if EFFORT_FLAG
        else [{"m":"claude-sonnet-4-6","tag":"son-bigout","args":[],"p":"count from 1 to 300, one number per line, no other text"}]*5))
def dose(c):
    try:
        p=subprocess.run(["claude","-p",c["p"],"--model",c["m"],"--output-format","json"]+c["args"],
                         cwd="/tmp/tokcap-probe",capture_output=True,text=True,timeout=240,stdin=subprocess.DEVNULL)
        d=json.loads(p.stdout); u=d.get('usage',{})
        log(phase='dose',tag=c['tag'],model=c['m'],cost=d.get('total_cost_usd'),
            usage={k:u.get(k) for k in ('input_tokens','cache_creation_input_tokens','cache_read_input_tokens','output_tokens')})
        return True
    except Exception as e: log(phase='dose_err',tag=c['tag'],err=str(e)[:200]); return False
def main():
    log(phase='armed',effort_flag=EFFORT_FLAG,cells=len(CELLS))
    pass
    b=meter()
    if not b or (b.get('session') or 100)>60: log(phase='abort',why='no fresh window',bars=b); return
    errs=0; last=None; jump=1.0
    for c in CELLS:
        b=meter()
        if b is None: log(phase='stop',why='meter_unreadable'); break
        pct=b.get('session')
        if pct is None: log(phase='stop',why='no_bar'); break
        if last is not None: jump=max(jump,pct-last)
        last=pct
        if pct+max(1.0,jump)>=CEIL: log(phase='stop',why='preflight',pct=pct); break
        if not dose(c):
            errs+=1
            if errs>=3: log(phase='stop',why='errors'); break
        else: errs=0
        time.sleep(80)
    log(phase='batch_end',final=meter())
    print("BATCH2 DONE")
main()
