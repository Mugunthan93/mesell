#!/usr/bin/env python3
"""tokcap Phase-3: predictor + validation-pair logger.
  predict --model M --out N [--cold]   -> % of session window this work will cost
  session start                        -> snapshot meter as session baseline
  session end [--predicted P]          -> snapshot, print actual Δ%, log validation pair
Constants from ~/.tokcap/constants.json (auto-seeded from Phase-2 fit)."""
import json, os, sys, subprocess, datetime
CONST=os.path.expanduser('~/.tokcap/constants.json')
VAL=os.path.expanduser('~/.tokcap/validation_log.ndjson')
BASE=os.path.expanduser('~/.tokcap/session_baseline.json')
METER=os.path.join(os.path.dirname(os.path.abspath(__file__)),'tokcap_meter.py')
SEED={"fit_date":"2026-07-18","pct_usd":0.0575,"pct_usd_range":[0.05,0.065],
 "C_session_usd":5.75,"weekly_mult":8.5,
 "prices_out_per_M":{"fable":50,"opus":25,"sonnet":15,"haiku":5},
 "prices_in_per_M":{"fable":10,"opus":5,"sonnet":3,"haiku":1},
 "cold_context_writes_tok":78000,"note":"meter is $-weighted (batch-4 verdict)"}
def consts():
    if not os.path.exists(CONST): json.dump(SEED,open(CONST,'w'),indent=1)
    return json.load(open(CONST))
def meter_bars():
    out=subprocess.run(["python3",METER,"--force"],capture_output=True,text=True).stdout
    bars={}
    for ln in out.splitlines():
        t=ln.split()
        if t and t[0] in ("session","weekly_all","weekly_scoped"):
            try: bars[t[0]]=float([x for x in t if x.endswith('%')][0][:-1])
            except: pass
    return bars
def main():
    c=consts(); a=sys.argv[1:]
    if a[:1]==["predict"]:
        m=a[a.index("--model")+1] if "--model" in a else "sonnet"
        out=int(a[a.index("--out")+1]) if "--out" in a else 2000
        usd=out/1e6*c["prices_out_per_M"].get(m,15)
        if "--cold" in a: usd+=c["cold_context_writes_tok"]*1.25/1e6*c["prices_in_per_M"].get(m,3)
        pct=100*usd/c["C_session_usd"]
        print(f"predict: {m} out≈{out} {'cold' if '--cold' in a else 'warm'} → ≈${usd:.3f}-equiv → ≈{pct:.1f}% of session window (weekly: {pct/c['weekly_mult']:.2f}%)")
    elif a[:2]==["session","start"]:
        b=meter_bars(); json.dump({"t":datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),"bars":b},open(BASE,'w'))
        print(f"baseline saved: {b}")
    elif a[:2]==["session","end"]:
        b=meter_bars(); base=json.load(open(BASE)); d=b.get('session',0)-base['bars'].get('session',0)
        pred=float(a[a.index("--predicted")+1]) if "--predicted" in a else None
        rec={"t":datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
             "start":base,"end":b,"actual_delta_pct":d,"predicted_pct":pred,
             "err_pct":(None if pred is None else round(abs(pred-d),2))}
        open(VAL,'a').write(json.dumps(rec)+"\n")
        print(f"actual Δsession = {d}%"+(f"  predicted {pred}%  |err|={rec['err_pct']}" if pred is not None else "")+"  → logged")
    else: print(__doc__)
main()
