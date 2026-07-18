#!/usr/bin/env python3
"""CLEAN combined batch — haiku & sonnet interleaved, default effort.
Decides: is the meter $-weighted or token-weighted? Ceiling = start+10.
Human-readable live log -> ~/.tokcap/clean_batch_live.log (tail -f it)."""
import json, subprocess, time, datetime, urllib.request, getpass, os
ND=os.path.expanduser('~/.tokcap/probe_batch3_20260718.ndjson')
HL=os.path.expanduser('~/.tokcap/clean_batch_live.log')
UA="claude-cli/2.1.211 (external, cli)"; UTC=datetime.timezone.utc
def now(): return datetime.datetime.now(UTC).strftime('%H:%M:%S')
def nd(**kw):
    kw['t']=datetime.datetime.now(UTC).isoformat(timespec='seconds'); open(ND,'a').write(json.dumps(kw)+'\n')
def hl(line):
    open(HL,'a').write(f"{now()}  {line}\n")
def token():
    raw=subprocess.run(["security","find-generic-password","-s","Claude Code-credentials","-a",getpass.getuser(),"-w"],capture_output=True,text=True,check=True).stdout.strip()
    return json.loads(raw)["claudeAiOauth"]["accessToken"]
def meter():
    for _ in range(3):
        try:
            req=urllib.request.Request("https://api.anthropic.com/api/oauth/usage",headers={"Authorization":f"Bearer {token()}","User-Agent":UA,"anthropic-beta":"oauth-2025-04-20"})
            with urllib.request.urlopen(req,timeout=15) as r: d=json.loads(r.read().decode())
            bars={l['kind']:l.get('percent') for l in d.get('limits',[])}; nd(phase='meter',bars=bars); return bars
        except Exception as e: nd(phase='meter_err',err=str(e)[:120]); time.sleep(45)
    return None
def dose(model,short):
    try:
        p=subprocess.run(["claude","-p","reply with exactly: ok","--model",model,"--output-format","json"],
                         cwd="/tmp/tokcap-probe",capture_output=True,text=True,timeout=240,stdin=subprocess.DEVNULL)
        d=json.loads(p.stdout); u=d.get('usage',{})
        nd(phase='dose',model=model,cost=d.get('total_cost_usd'),usage={k:u.get(k) for k in ('input_tokens','cache_creation_input_tokens','cache_read_input_tokens','output_tokens')})
        cw='cold' if u.get('cache_read_input_tokens',0)==0 else 'warm'
        hl(f"DOSE  {short:6s} {cw}  in={u.get('input_tokens')} cacheWrite={u.get('cache_creation_input_tokens')} cacheRead={u.get('cache_read_input_tokens')} out={u.get('output_tokens')}  cost=${d.get('total_cost_usd'):.4f}")
        return d.get('total_cost_usd') or 0
    except Exception as e:
        nd(phase='dose_err',model=model,err=str(e)[:200]); hl(f"DOSE  {short} ERROR {str(e)[:80]}"); return None
def main():
    open(HL,'w').write("=== tokcap CLEAN BATCH (haiku+sonnet interleaved) — QUARANTINE: no other Claude usage! ===\n")
    b=meter()
    if not b: hl("ABORT: meter unreadable"); return
    start=b.get('session'); ceil=start+10
    hl(f"START session={start}%  weekly={b.get('weekly_all')}%  ceiling={ceil}%  plan=6x haiku + 6x sonnet interleaved, 80s spacing")
    doses=[("claude-haiku-4-5","haiku"),("claude-sonnet-4-6","sonnet")]*6
    last=start; jump=1.0; since_tick=0.0; errs=0
    for i,(m,s) in enumerate(doses,1):
        b=meter()
        if b is None: hl("STOP: meter unreadable"); break
        pct=b.get('session')
        if pct!=last:
            hl(f"TICK  session {last}%→{pct}%   (doses since last tick: ${since_tick:.4f})")
            jump=max(jump,pct-last); since_tick=0.0; last=pct
        if pct+max(1.0,jump)>=ceil:
            hl(f"STOP: pre-flight — {pct}% + buffer {max(1.0,jump)} would reach ceiling {ceil}%"); break
        c=dose(m,s)
        if c is None:
            errs+=1
            if errs>=3: hl("STOP: 3 consecutive errors"); break
        else: errs=0; since_tick+=c
        time.sleep(80)
    b=meter(); hl(f"END   session={b.get('session') if b else '?'}%  weekly={b.get('weekly_all') if b else '?'}%")
    hl("BATCH COMPLETE — master session will analyze now.")
main()
