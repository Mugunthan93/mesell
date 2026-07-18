#!/usr/bin/env python3
"""tokcap Phase-2 first titration batch. Ceiling 95% with PRE-FLIGHT check:
before each dose, estimate its % cost (adaptive: max observed jump per model,
floor 1%; Fable floor 2.5%) and skip/stop unless it lands < ceiling.
Stops: ceiling | 05:35Z hard-stop | meter unreadable | 3 consecutive errors."""
import json, subprocess, time, datetime, urllib.request, getpass, sys, os

CEIL=95.0; LOG=os.path.expanduser('~/.tokcap/probe_batch_20260718.ndjson')
HARDSTOP=datetime.datetime(2026,7,18,5,35,tzinfo=datetime.timezone.utc)
UA="claude-cli/2.1.211 (external, cli)"
DOSES=(['claude-haiku-4-5']*30)
BUF={'claude-haiku-4-5':1.0,'claude-sonnet-4-6':1.0,'claude-fable-5':2.5}

def log(**kw):
    kw['t']=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    open(LOG,'a').write(json.dumps(kw)+'\n')

def token():
    raw=subprocess.run(["security","find-generic-password","-s","Claude Code-credentials","-a",getpass.getuser(),"-w"],capture_output=True,text=True,check=True).stdout.strip()
    return json.loads(raw)["claudeAiOauth"]["accessToken"]

def meter(retries=2):
    for i in range(retries+1):
        try:
            req=urllib.request.Request("https://api.anthropic.com/api/oauth/usage",headers={"Authorization":f"Bearer {token()}","User-Agent":UA,"anthropic-beta":"oauth-2025-04-20"})
            with urllib.request.urlopen(req,timeout=15) as r: d=json.loads(r.read().decode())
            bars={l['kind']:l.get('percent') for l in d.get('limits',[])}
            if d.get('limits'):
                for l in d['limits']:
                    if l['kind']=='weekly_scoped': bars['weekly_scoped']=l.get('percent')
            log(phase='meter',bars=bars)
            return bars
        except Exception as e:
            log(phase='meter_err',err=str(e)[:120]); time.sleep(30)
    return None

def dose(model):
    try:
        p=subprocess.run(["claude","-p","reply with exactly: ok","--model",model,"--output-format","json"],
                         cwd="/tmp/tokcap-probe",capture_output=True,text=True,timeout=180,stdin=subprocess.DEVNULL)
        d=json.loads(p.stdout); u=d.get('usage',{})
        log(phase='dose',model=model,cost=d.get('total_cost_usd'),
            usage={k:u.get(k) for k in ('input_tokens','cache_creation_input_tokens','cache_read_input_tokens','output_tokens')})
        return True
    except Exception as e:
        log(phase='dose_err',model=model,err=str(e)[:200]); return False

def main():
    log(phase='batch_start',ceiling=CEIL,doses=len(DOSES))
    errs=0; last=None; jump={m:0.0 for m in BUF}
    for i,m in enumerate(DOSES):
        if datetime.datetime.now(datetime.timezone.utc)>=HARDSTOP: log(phase='stop',why='hardstop'); break
        bars=meter()
        if bars is None: log(phase='stop',why='meter_unreadable'); break
        pct=bars.get('session')
        if pct is None: log(phase='stop',why='no_session_bar'); break
        if last is not None and lastm: jump[lastm]=max(jump[lastm],pct-last)
        need=max(BUF[m],jump[m])
        if pct>=CEIL or pct+need>=CEIL:
            log(phase='stop',why='preflight',pct=pct,need=need,model=m); break
        last, lastm = pct, m
        if not dose(m):
            errs+=1
            if errs>=3: log(phase='stop',why='errors'); break
        else: errs=0
        time.sleep(80)
    fb=meter(); log(phase='batch_end',final=fb)
    print("BATCH DONE", fb)

lastm=None
main()
