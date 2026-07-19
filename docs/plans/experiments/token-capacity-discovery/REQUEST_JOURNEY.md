# The Journey of a Request — Where Every Token Goes

**A Claude Code architectural walkthrough · tokcap · 2026-07-19**

This document traces ONE deliberately complex request from keystroke to receipt,
stopping at every place a token is consumed. Numbers are illustrative but use the
constants tokcap measured (context ≈ 78K, 1% of a 5h tank ≈ $0.0575, Fable $10 in /
$50 out per 1M, cache-write 1.25×, cache-read 0.1×).

---

## 0. The one law everything obeys

```
        ┌──────────────────────────────────────────────────────────┐
        │  THE SERVER HAS NO MEMORY.                                │
        │  Claude Code re-sends your ENTIRE world on every turn.    │
        └──────────────────────────────────────────────────────────┘
```

The intelligence is a **stateless function**: text in → text out → forgets
everything. To feel continuous, the app resends all prior context each time. That
single fact is the root of warm/cold, of why long sessions cost more, and of the
whole meter.

---

## 1. The cast — who holds what

```
        YOUR MAC (the messenger + hands)           ANTHROPIC (the brain)
  ┌───────────────────────────────────┐      ┌──────────────────────────────┐
  │  Claude Code app                  │      │  Stateless model              │
  │   • assembles the "package"       │ ───▶ │   • reads the whole package   │
  │   • runs tools LOCALLY            │ HTTPS│   • thinks, writes, or asks   │
  │      (Bash, Read, Edit, Grep…)    │ ◀─── │      for a tool               │
  │   • writes the transcript (.jsonl)│      │                               │
  │  Your files · CLAUDE.md · memory  │      │  CACHE STORE (1-hour TTL)     │
  │                                   │      │   • keeps your prefix warm    │
  │                                   │      │  METER  • counts $-weight → % │
  └───────────────────────────────────┘      └──────────────────────────────┘
```

- **The app cannot think.** It packages, ships, and executes returned instructions.
- **The cache store is on the server, not your Mac.** You cannot keep it warm by
  wishing — only by sending a request before its 1-hour timer expires.
- **The meter** sums each request's dollar-weight into the % bar tokcap reads.

---

## 2. The request we will trace

> On a **Fable** session that has been **idle 92 minutes**, you type:
> **"Review the auth module and fix the login bug."**

Chosen because it hits *everything*: a **cold** cache (idle > 1h), **thinking**
(Fable always thinks), an **agentic tool loop** (Read → Grep → Edit), a
**subagent** (its own fresh cold world), and **multiple round-trips** (history
grows and is resent each time).

---

## 3. What is inside the "package" (resent every round-trip)

```
  THE PACKAGE  =  four stacked layers, sent as ONE request
  ┌─────────────────────────────────────────────┬───────────────┐
  │ 1  System prompt + CLAUDE.md + agent memory  │  ~78,000 tok  │ ← stable,
  │ 2  Tool definitions (Bash, Read, Edit, …)    │   ~8,000 tok  │   cacheable
  ├─────────────────────────────────────────────┼───────────────┤   PREFIX
  │ 3  Conversation so far (grows every turn)    │  grows ↑      │
  │ 4  Your NEW message                          │   ~20 tok     │ ← the only
  └─────────────────────────────────────────────┴───────────────┘   new bytes
                                                   ≈ 86K + history
```

Layers 1–2 are (almost) identical every turn → the server can **cache** them.
Layer 4 is tiny. **You pay to move ~86K tokens on every single turn** — the only
question is whether that 86K is priced **warm (0.1×)** or **cold (1.25×)**.

---

## 4. The cache fork — the same step, two prices

```
                 request arrives at server
                          │
              ┌───────────┴────────────┐
     prefix still in cache?    prefix expired / changed?
        (asked < 1h ago,          (idle > 1h, OR model
         nothing changed)          switched, OR CLAUDE.md
              │                    /memory/tools edited)
              ▼                            ▼
        ┌───────────┐              ┌───────────────┐
        │  WARM     │              │  COLD         │
        │ cache_read│              │ cache_creation│
        │  × 0.10   │              │  × 1.25       │
        └─────┬─────┘              └───────┬───────┘
              │                            │
   86K → ~$0.086 (Fable)        86K → ~$1.075 (Fable)   ← ~12.5× more
   ≈ 1.5% of tank               ≈ 19% of tank            for the SAME bytes
```

Our idle-92-min request takes the **COLD** branch on its first round-trip.

---

## 5. The full journey (top = start, arrows = time; the loop repeats)

```
 ROUND 1  (COLD — the expensive entry)
 ─────────────────────────────────────────────────────────────────────
  you type ──▶ APP assembles package (86K cold) ──▶ SERVER
                                                      │ reads 86K (cache_creation)
                                                      │ THINKS  ← thinking tokens,
                                                      │          billed as output
                                                      │ decides: "I must read auth
                                                      │          files first"
                                    ◀───────────────── emits  tool_use: Read(auth.py)
   APP runs Read LOCALLY on your Mac                  │
   (no tokens — it's your disk)                       │
   receipt#1: in≈20 · cacheCreate≈86K · out≈1.5K  →  cost ≈ $1.15  ≈ 20% of tank
 ─────────────────────────────────────────────────────────────────────
 ROUND 2  (now WARM — history + file result resent)
 ─────────────────────────────────────────────────────────────────────
  APP appends the file (5K) as tool_result ──▶ package ──▶ SERVER
                                                      │ reads 86K (cache_READ, cheap)
                                                      │ + 5K new (cached now)
                                                      │ THINKS, wants to search
                                    ◀───────────────── tool_use: Grep("login")
   APP runs Grep locally                              │
   receipt#2: cacheRead≈86K · cacheCreate≈5K · out≈1K → cost ≈ $0.20 ≈ 3.5%
 ─────────────────────────────────────────────────────────────────────
 ROUND 3  (DELEGATION — a subagent is a whole NEW cold journey)
 ─────────────────────────────────────────────────────────────────────
  SERVER decides the fix is isolated ──▶ tool_use: Task(subagent)
                                    │
        ┌───────────────────────────┴──────────────────────────────┐
        │  SUBAGENT = a brand-new conversation.                     │
        │  It builds its OWN package from ZERO: its own 78K system  │
        │  + CLAUDE.md + memory  →  its own COLD start (~$1 again).  │
        │  Runs its own Read→Edit loop, its own receipts.           │
        │  ►► THIS is why subagents were 49% of all our spend. ◄◄   │
        └───────────────────────────┬──────────────────────────────┘
   subagent returns a short result ─┘  (only the RESULT comes back, not its 78K)
   subagent receipts: ≈ $1.30 total (its cold start + its loop)
 ─────────────────────────────────────────────────────────────────────
 ROUND 4  (FINISH — the visible answer)
 ─────────────────────────────────────────────────────────────────────
  APP feeds subagent result back ──▶ package (warm) ──▶ SERVER
                                                      │ THINKS, writes the final
                                    ◀───────────────── answer (streamed) + Edit
   APP applies the Edit locally                       │
   receipt#4: cacheRead≈91K · out≈3K (answer+think) → cost ≈ $0.25 ≈ 4%
 ─────────────────────────────────────────────────────────────────────
                                       ▼
                        final answer shown to you
```

---

## 6. Where each of the 4 token fields is born

```
  ┌────────────────────────┬───────────────────────────────────────────┐
  │ input_tokens           │ your new typed message + fresh tool text   │
  │                        │ that isn't cached yet · small · full price │
  ├────────────────────────┼───────────────────────────────────────────┤
  │ cache_creation  (COLD) │ the 86K prefix written into cache the 1st  │
  │                        │ time / after expiry · ×1.25 · the COLD TAX │
  ├────────────────────────┼───────────────────────────────────────────┤
  │ cache_read      (WARM) │ the same 86K re-served from cache · ×0.10  │
  │                        │ · nearly free · what "warm" means          │
  ├────────────────────────┼───────────────────────────────────────────┤
  │ output_tokens          │ everything the model WRITES — the visible  │
  │                        │ answer AND its hidden thinking · ×output$  │
  │                        │ · effort/thinking only grow THIS number    │
  └────────────────────────┴───────────────────────────────────────────┘
   The receipt (response.usage) carries all four. tokcap harvests it → ledger.
```

---

## 7. Effort & thinking — not a surcharge, just more of layer 4

```
   low effort   ──▶  output = [ short answer ]                 small
   high effort  ──▶  output = [ ═══ long thinking ═══ ][ answer ]  bigger
                                └── billed as output_tokens ──┘
   No hidden fee. Higher effort/thinking = more output tokens = more cost,
   priced by that model's output rate ($50/M on Fable, $5/M on Haiku).
```

---

## 8. The receipt meets the meter

```
   SERVER ── response.usage {in, cacheCreate, cacheRead, out} ──▶ YOUR MAC
      │                                                              │
      │ same numbers ──▶ METER sums $-weight ──▶ the % bar           │ transcript
      ▼                                            │                 ▼ (.jsonl)
   /api/oauth/usage  ◀── tokcap reads this ◀───────┘        tokcap ledger reads
   session 55% · weekly 47% …                                the receipt too
```

The meter counts **dollars of work** (tokcap batch-4 verdict: $-weighted), so a
Haiku turn and a Fable turn of equal dollar-cost move the bar equally — even though
Fable used far fewer tokens to get there.

---

## 9. Cost tally of THIS one request

```
  Round 1  main, COLD entry ................ ~$1.15   ≈ 20% of the 5h tank
  Round 2  main, warm loop ................. ~$0.20   ≈  3.5%
  Round 3  SUBAGENT (its own cold world) ... ~$1.30   ≈ 23%
  Round 4  main, warm finish ............... ~$0.25   ≈  4%
  ─────────────────────────────────────────────────────────────
  TOTAL  ................................... ~$2.90   ≈ 50% of ONE 5h tank
```

> One "simple-sounding" complex request ate **half a window** — because it paid
> **two cold starts** (main + subagent) on the most expensive model. This is
> literally the anatomy of your original "40% gone" surprise.

**Every lever we found, visible in this tally:**
- **Cold → warm** would erase most of Round 1 (~$1.15 → ~$0.09).
- **Model choice**: the same journey on Sonnet ≈ 1/3 the cost; on Haiku ≈ 1/10.
- **Fewer subagents**: Round 3's $1.30 is an entire second cold world — dispatch
  only when the isolation is worth it.
- **Effort**: only Rounds' output portions; cheap relative to the cold tax.

---

## 10. Legend

```
  package .......... everything resent to the server in one request
  prefix ........... the stable, cacheable top of the package (layers 1–2)
  warm / cold ...... prefix served from cache (0.1×) vs re-written (1.25×)
  round-trip ....... one request→response; a complex task loops several
  tool_use ......... the server ASKS the app to run a tool; app runs it locally
  subagent ......... a second conversation with its OWN fresh 78K cold world
  receipt .......... response.usage: the 4 token fields, the source of truth
  meter ............ server's running $-weighted % bar (session + weekly tanks)
  1% ............... ≈ $0.0575 of API-equivalent work (tokcap-measured)
```

*Companion docs: ARCHITECTURE.md (the tokcap system) · phase2-report.md (how the
constants were measured).*
