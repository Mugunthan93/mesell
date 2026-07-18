#!/usr/bin/env python3
"""MONO-MODEL DECIDER — Phase A: haiku-only until 2 interior ticks; Phase B: sonnet-only same.
Separates $-weighted vs token-weighted metering. Live log: ~/.tokcap/clean_batch_live.log"""
import json, subprocess, time, datetime, urllib.request, getpass, os
ND=os.path.expanduser('~/.tokcap/probe_batch4_20260718.ndjson'); HL=os.path.expanduser('~/.tokcap/clean_batch_live.log')
UA="claude-cli/2.1.211 (external, cli)"; UTC=datetime.timezone.utc
PROMPT="count from 1 to 500, one number per line, no other text"
def now(): return datetime.datetime.now(UTC).strftime('%H:%M:%S')
def nd(**kw): kw['t']=datetime.datetime.now(UTC).isoformat(timespec='seconds'); open(ND,'a').write(json.dumps(kw)+'\n')
def hl(s): open(HL,'a').write(f"{now()}  {s}\n")
def token():
    raw=subprocess.run(["security","find-generic-password","-s","Claude Code-credentials","-a",getpass.getuser(),"-w"],capture_output=True,text=True,check=True).stdout.strip()
    return json.loads(raw)["claudeAiOauth"]["accessToken"]
def meter():
    for _ in range(3):
        try:
            req=urllib.request.Request("https://api.anthropic.com/api/oauth/usage",headers={"Authorization":f"Bearer {token()}","User-Agent":UA,"anthropic-beta":"oauth-2025-04-20"})
            with urllib.request.urlopen(req,timeout=15) as r: d=json.loads(r.read().decode())
            bars={l['kind']:l.get('percent') for l in d.get('limits',[])}; nd(phase='meter',bars=bars); return bars
        except Exception as e: nd(phase='meter_err',err=str(e)[:100]); time.sleep(45)
    return None
def bwf(u): return u['input_tokens']+u['cache_creation_input_tokens']*1.25+u['cache_read_input_tokens']*0.1+u['output_tokens']
def dose(model,short):
    try:
        p=subprocess.run(["claude","-p",PROMPT,"--model",model,"--output-format","json"],cwd="/tmp/tokcap-probe",capture_output=True,text=True,timeout=300,stdin=subprocess.DEVNULL)
        d=json.loads(p.stdout); u=d.get('usage',{}); c=d.get('total_cost_usd') or 0
        nd(phase='dose',model=model,cost=c,usage={k:u.get(k) for k in ('input_tokens','cache_creation_input_tokens','cache_read_input_tokens','output_tokens')})
        hl(f"DOSE  {short:6s} {'cold' if u.get('cache_read_input_tokens',0)==0 else 'warm'}  out={u.get('output_tokens')}  cost=${c:.4f}")
        return c,bwf(u)
    except Exception as e: nd(phase='dose_err',model=model,err=str(e)[:150]); hl(f"DOSE {short} ERROR"); return None,None
def phase(model,short,ceil):
    hl(f"— PHASE {short.upper()}: dosing until 2 interior ticks (max 25 doses) —")
    b=meter(); last=b.get('session'); jump=1.0
    acc=[0.0,0.0]; intervals=[]; seen_first=False; n=0
    while n<25 and len(intervals)<2:
        if last+max(1.0,jump)>=ceil: hl(f"STOP {short}: preflight {last}%+{max(1.0,jump)}≥{ceil}%"); break
        c,bb=dose(model,short); n+=1
        if c is not None: acc[0]+=c; acc[1]+=bb
        time.sleep(65)
        b=meter()
        if b is None: hl("STOP: meter unreadable"); break
        p=b.get('session')
        if p!=last:
            if not seen_first:
                hl(f"TICK  {last}%→{p}%  (partial — discarded)"); seen_first=True
            else:
                per_d=acc[0]/(p-last); per_b=acc[1]/(p-last)
                intervals.append((per_d,per_b)); hl(f"TICK  {last}%→{p}%  INTERIOR: ${acc[0]:.4f} / {acc[1]/1e3:.1f}K tok-BW over {p-last}% → per-1%: ${per_d:.4f} / {per_b/1e3:.1f}K")
            jump=max(jump,p-last); last=p; acc=[0.0,0.0]
    return intervals
def main():
    open(HL,'a').write(f"\n=== MONO-MODEL DECIDER BATCH — QUARANTINE! ===\n")
    b=meter()
    if not b: hl("ABORT: meter unreadable"); return
    start=b.get('session'); ceil=start+12
    hl(f"START session={start}%  ceiling={ceil}%  prompt='count to 500'")
    H=phase("claude-haiku-4-5","haiku",ceil)
    S=phase("claude-sonnet-4-6","sonnet",ceil)
    hl("═══ VERDICT ═══")
    if H and S:
        import statistics as st
        dh=st.mean(x[0] for x in H); bh=st.mean(x[1] for x in H)
        ds=st.mean(x[0] for x in S); bs=st.mean(x[1] for x in S)
        hl(f"haiku : per-1% = ${dh:.4f} / {bh/1e3:.1f}K tokens")
        hl(f"sonnet: per-1% = ${ds:.4f} / {bs/1e3:.1f}K tokens")
        r_d=ds/dh if dh else 0; r_b=bs/bh if bh else 0
        hl(f"ratios: $-per-tick sonnet/haiku = {r_d:.2f}   tokens-per-tick = {r_b:.2f}")
        if 0.6<=r_d<=1.6 and r_b<0.65: hl("VERDICT: $-WEIGHTED — meter charges by API price; model choice = real cost lever")
        elif 0.6<=r_b<=1.6 and r_d>1.6: hl("VERDICT: TOKEN-WEIGHTED — meter model-agnostic per token; cheap models DON'T save plan budget")
        else: hl("VERDICT: INCONCLUSIVE — mixed ratios; needs repetition")
    else: hl(f"VERDICT: insufficient ticks (haiku {len(H)}, sonnet {len(S)})")
    b=meter(); hl(f"END session={b.get('session') if b else '?'}%")
    hl("BATCH COMPLETE")
main()
