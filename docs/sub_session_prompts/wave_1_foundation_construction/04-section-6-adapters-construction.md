# Sub-Session Prompt: §6 `adapters/` — Third-Party Vendor Clients
# Wave 1 of 10 — CONSTRUCTION
# Specialist agent: meesell-services-builder
# Renames session to: meesell-backend-construction-6-adapters-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy the block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §6 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-services-builder agent operating in a dedicated construction sub-session for MeeSell §6 (`adapters/` — Third-Party Vendor Clients).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning `BACKEND_ARCHITECTURE.md`.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §6 `adapters/` — 5 vendor clients (gemini, msg91, gcs, razorpay, langfuse)
- Specialist agent: meesell-services-builder (solo on `adapters/`)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-6-adapters-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §6 — A through H (esp. §6.B gemini 2 methods, §6.C msg91 send_otp returns success=False on failure NOT raise — locked exception to raise-on-failure pattern per §6.G, §6.D gcs 4 methods incl. signed_url 1h TTL, §6.E razorpay verify_webhook_signature sync — locked exception to async-default per §6.G, §6.F langfuse 2 methods incl. drop-on-failure with warning log).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §0, §3 (File Structure — esp. §3.F `adapters/` subtree + §3.G `ai_ops/` boundary lock that domain modules NEVER import `adapters/gemini.py` directly), §5 (shared/Settings consumed for credentials).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §10.8 (GCS layout `gs://meesell-images/{user_id}/{product_id}/{image_idx}.jpg` + signed URL TTL 1h). Cited; not amended.

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md` (Decision 1: Valkey; Decision 2: GCS; Decision 3: Gemini 2.5 Flash; Decision 14: MSG91 OTP).

5. `.claude/agents/meesell-services-builder.md` (own spec).

6. `.claude/agent-memory/meesell-services-builder/MEMORY.md`.

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm §5, §4, §5A CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` baseline.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Per §3.F:

```
backend/app/adapters/
├── __init__.py
├── gemini.py            # raw Gemini 2.5 Flash client — transport retry only (§6A wraps with ops)
├── msg91.py             # OTP send client — locked exception: returns Msg91Response with success=False (does NOT raise) per §6.C + §6.G
├── gcs.py               # 4 methods: upload_bytes, download_bytes, generate_signed_url (TTL 1h), delete_blob; path convention meesell-images/{user_id}/{product_id}/{idx}.jpg + meesell-exports/{user_id}/...
├── razorpay.py          # verify_webhook_signature(payload, signature, secret) -> bool — SYNC per §6.E exception (HMAC is CPU-bound)
└── langfuse.py          # 2 methods: emit_trace, emit_event — drop-on-failure with warning log per §6.F + §1.E
```

Common patterns per §6.G:
- All async-default except `razorpay.verify_webhook_signature` (sync) and `langfuse.*` (async but drop-on-failure).
- Credentials from `Settings` (NEVER `os.getenv`).
- No business logic — pure transport + envelope shaping.
- Typed `AdapterError` hierarchy with HTTP 502 default mapping.
- Lazy singleton clients (one per process).

Construction protocol:

1. **Tests first**:
   - `test_gemini_adapter.py` — happy path mock + transient retry mock + non-retryable error mapping to `AdapterError`.
   - `test_msg91_adapter.py` — happy path returns `Msg91Response(success=True)`; failure returns `Msg91Response(success=False, error_code="...")` WITHOUT raising (locked exception).
   - `test_gcs_adapter.py` — upload, download, signed URL TTL = 3600s (1h), delete; path convention matches §10.8.
   - `test_razorpay_adapter.py` — verify_webhook_signature returns bool; valid HMAC True, invalid False, malformed signature False (does NOT raise).
   - `test_langfuse_adapter.py` — happy path emits; failure logs warning and returns None (drop-on-failure).

2. **Implementation**: 5 adapter files with locked signatures.

3. **Acceptance**: tests pass; ruff clean; boot smoke PASS; schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT add business logic to adapters (any field translation, any rule check, any cost tracking → that's §6A or domain modules).
- DO NOT use `os.getenv` for credentials — read from `Settings` per §6.G.
- DO NOT raise `Exception` directly — use the typed `AdapterError` hierarchy.
- DO NOT make `razorpay.verify_webhook_signature` async (locked sync exception per §6.E).
- DO NOT make `msg91.send_otp` raise on failure (locked: returns `Msg91Response(success=False)`).
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted: `meesell-services-builder` (solo on this section).

You ARE NOT permitted: any other dispatch.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §6)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population during this dispatch. `RAZORPAY_WEBHOOK_SECRET` (consumed by razorpay.py) and `LANGFUSE_SECRET_KEY` (consumed by langfuse.py) are documented in `Settings` as not-yet-populated; their values are populated during §20 deployment construction. Your job is to consume them from `Settings`, not provision them.

None — no latent bugs to resolve.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. 5 adapter files exist with the locked signatures from §6.B-§6.F.
2. `msg91.send_otp` returns `Msg91Response` with `success=False` on failure — does NOT raise (verified by test).
3. `razorpay.verify_webhook_signature` is sync — does NOT use `async def` (verified by inspect/AST scan).
4. `gcs.generate_signed_url` TTL defaults to 3600s (1h).
5. GCS path convention matches §10.8 (`meesell-images/{user_id}/{product_id}/{idx}.jpg`).
6. `langfuse.*` methods drop-on-failure with `logger.warning(...)` — do NOT raise (verified by test).
7. All credentials sourced from `Settings`.
8. No vendor SDK types leak past adapter file boundary (verified by grep — no `from google.cloud import storage` or similar in non-adapter files).

Plus universal: all tests pass; ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update `.claude/agent-memory/meesell-services-builder/MEMORY.md`.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §6 adapters CONSTRUCTED ===
   Files created: adapters/{__init__.py, gemini.py, msg91.py, gcs.py, razorpay.py, langfuse.py}
   Tests added: 5 unit test classes (one per adapter)
   Decisions made: <list>
   Hand-offs: §6A ai_ops (wraps adapters/gemini.py with cost+guardrail+budget); §7 iam (consumes msg91 + razorpay); §11 image (consumes gcs); §14 export (consumes gcs)
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Vendor SDK upgrade breaks locked signature.
- Settings field name mismatch.
- Locked exception ambiguity (e.g. msg91 timeout — return False or raise?).

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-6-adapters-1`
2. Read REQUIRED READING.
3. Confirm §5 + §4 + §5A CONSTRUCTED.
4. Report "Context loaded. Ready to begin §6 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 1 of 10
- **Sequential dependency:** §5 + §4 + §5A CONSTRUCTED (adapters consume Settings from §5).
- **Parallel-safe?:** No — Wave 1 sequential.
- **Expected duration estimate:** ~5-7 hours (5 adapters × ~1h each + tests).
- **Acceptance verification by master:** (1) `grep -r "import google" backend/app/` outside `adapters/gcs.py` returns nothing; (2) `grep -r "async def verify_webhook_signature" backend/app/adapters/razorpay.py` returns nothing (must be sync); (3) `grep -r "raise" backend/app/adapters/msg91.py` shows NO bare raise on failure path; (4) boot + schema smoke PASS; (5) STATUS_BACKEND.md UPDATE block present.
