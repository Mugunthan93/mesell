## §6 adapters CONSTRUCTED (2026-06-06)

### Scope
Solo sub-session `meesell-backend-construction-6-adapters-1`. Built the 5
vendor adapters per `BACKEND_ARCHITECTURE.md` §6.B–§6.G under
`backend/app/adapters/`. Zero touches outside §6 scope.

### Files created (6)
- `backend/app/adapters/__init__.py` — `AdapterError(MeesellError)` root +
  5 typed subclasses (`GeminiAdapterError`, `Msg91AdapterError`,
  `GcsAdapterError`, `RazorpayAdapterError`, `LangfuseAdapterError`).
  Default `status_code=502` + `validation_message_id=<vendor>.unavailable`.
- `backend/app/adapters/gemini.py` (~230 LOC) — async `generate_text` +
  `generate_vision`; `GeminiResponse` dataclass (text/in_tok/out_tok/
  finish_reason/raw); 3-retry exponential 1s/4s/16s on conn/5xx/429;
  `_call_sdk` is the single SDK touch point + mock target for tests; lazy
  per-model `GenerativeModel` cache; `genai.configure(api_key=...)` runs
  exactly once at first model construction.
- `backend/app/adapters/msg91.py` (~180 LOC) — async `send_otp(phone, otp,
  *, template_id)`; `Msg91Response(success, request_id, message)`; 1
  retry on conn/5xx/429; **LOCKED EXCEPTION: NEVER raises** — returns
  `success=False` on any failure (transport, vendor failure, unexpected).
  Phone `+` stripped (vendor requirement). OTP NEVER logged.
- `backend/app/adapters/gcs.py` (~200 LOC) — async `upload_bytes`,
  `download_bytes`, `generate_signed_url(ttl_seconds=3600 default,
  method="GET"|"PUT")`, `delete`; sync SDK wrapped in `asyncio.to_thread`;
  ADC creds; raises `GcsAdapterError(502)` on `_FATAL_SDK_EXC` =
  (NotFound, Forbidden, Unauthorized, BadRequest, GoogleAPICallError);
  signed URLs use `version="v4"`.
- `backend/app/adapters/razorpay.py` (~80 LOC) — **SYNC**
  `verify_webhook_signature(payload, signature, *, secret) -> bool`;
  HMAC-SHA256 + `hmac.compare_digest` constant-time; **LOCKED EXCEPTION:
  NEVER raises, NEVER async**; defensive bool returns on malformed
  payload/signature.
- `backend/app/adapters/langfuse.py` (~190 LOC) — async `trace` +
  `score`; **LOCKED: NEVER raises (drop-on-failure with WARNING)**;
  missing creds → no-op + 1-time WARNING via `_creds_warned` latch; httpx
  direct POST to `{LANGFUSE_HOST}/api/public/ingestion` with batch
  envelope `{batch: [{id, timestamp, type: "trace-create"|"score-create",
  body: {...}}]}`.

### Tests added (5 modules, 73 tests, all PASS)
- `tests/test_gemini_adapter.py` (17 tests) — exception hierarchy
  inheritance; happy path; max_output_tokens / response_mime_type
  propagation; generate_vision image bytes propagation; 503/429/
  ConnectionError transient retry then succeed; retry exhaustion → raise;
  non-retryable Unauthenticated / InvalidArgument → raise immediately;
  exception chained via `__cause__`; defensive `_envelope` on
  missing usage_metadata / missing text; no `from app.modules` imports;
  no `os.getenv`.
- `tests/test_msg91_adapter.py` (13 tests) — happy 2xx + `type=success`;
  4xx → success=False (no raise); 5xx → 1 retry then success=False;
  429 → 1 retry; success after one transient 5xx; connection error →
  success=False; timeout → success=False; phone `+` stripped; template_id
  override; defensive RuntimeError → success=False; no `os.getenv`;
  source-grep confirms OTP not interpolated into log format strings.
- `tests/test_gcs_adapter.py` (16 tests) — exception class inheritance;
  upload_bytes happy + image path + export path conventions; Forbidden /
  GoogleAPICallError → GcsAdapterError; download_bytes happy + NotFound
  → raise; signed URL default TTL=3600s (locked §10.8); custom TTL; PUT
  method; SDK error → raise; delete happy + NotFound → raise; bucket
  override; no `os.getenv`; no domain imports.
- `tests/test_razorpay_adapter.py` (14 tests) — `iscoroutinefunction`
  False (LOCKED sync); source-grep first line `def` not `async def`;
  RazorpayAdapterError class defined for V1.5; valid HMAC → True;
  invalid → False (no raise); wrong secret → False; uses settings when
  secret arg omitted; empty/None signature → False; non-bytes payload →
  False (defensive); bytearray accepted; constant-time `compare_digest`
  used; no `os.getenv`; razorpay SDK NOT imported in V1.
- `tests/test_langfuse_adapter.py` (13 tests) — LangfuseAdapterError
  defined for V1.5; trace + score POST to `/api/public/ingestion` with
  correct type discriminators; 5xx/ConnectError/Timeout/RuntimeError →
  drop-on-failure + WARNING log; missing creds → 0 network calls + 1
  WARNING per session (latch verified); UUID generated when trace_id
  omitted; user_id UUID serialised to str; no `os.getenv`; no domain
  imports.

### Acceptance gate result
- Ruff: ALL CHECKS PASSED on all 11 touched files (4 unused-import F401
  fixes applied during gate: `asyncio` in test_gcs/test_gemini,
  `timedelta` in test_gcs, `pytest` in test_razorpay).
- `python -c "from app.main import app; <import all 5 adapter modules>"`:
  imports clean, routes=9 unchanged.
- `pytest test_app_boot_integration test_shared_* test_core_* test_messages_en_id_regex test_resolver_fallback test_schema_jsonb_envelope_keys test_per_field_shape_keys`:
  216/216 PASS.
- `pytest test_<5 adapters>_adapter.py`: **73/73 PASS in 5.69s**.
- `pytest test_database.py` (live dev Postgres via SSH tunnel): **42/42 PASS in 153s**.
- Grand total this dispatch: **331/331 PASS**.

### Decisions FLAGGED (not in locked architecture)

D1 — **LangFuse implementation = httpx direct POST, NO new SDK dependency.**
`requirements.txt` has no `langfuse` package and I chose NOT to add one in
this dispatch. Rationale: (a) `httpx` is already pinned; (b) fire-and-
forget semantics make the SDK's batching value moot for V1 volume; (c)
SDK reintroduction is a single-file change in V1.5 if needed. FLAGGED in
the `adapters/langfuse.py` module docstring under "Decision flag D1".
ESCALATE to master if the SDK is preferred — the swap is trivial.

D2 — **`adapters/__init__.py` re-exports both `AdapterError` and the 5
typed subclasses** — `app.adapters import GeminiAdapterError` works
without touching the per-vendor module. The §19 CI linter can then test
the inheritance chain at the package import surface.

D3 — **`_reset_for_testing()` helper added to each adapter** (except
razorpay — no state). Pattern: clears the module-level singleton client
and `_init_lock`. Required because `asyncio.Lock()` is bound to the
loop that first awaits it; pytest-asyncio session loop-scope plus the
function-scope fixture pattern would otherwise hit "Future attached to
a different loop" on subsequent test runs. Test fixtures call this in
both setup and teardown.

D4 — **Gemini retry constants live in module-level `_RETRY_DELAYS_S =
(1.0, 4.0, 16.0)`** — exposed for monkeypatch overrides (tests zero it
to keep wall time low). The 4 attempts = 1 initial + 3 retries per §6.B
"3-retry exponential backoff" reading; the loop iterates
`range(len(_RETRY_DELAYS_S) + 1)`.

D5 — **`razorpay.verify_webhook_signature` source-grep test added.**
`test_verify_webhook_signature_signature_is_def_not_async_def` reads
the function's source first line and asserts it starts with `def ` and
NOT `async def `. Defensive against accidental rewrites.

### Hand-offs queued
- **§6A `ai_ops/client.py`** — sole consumer of `adapters/gemini.py` per
  §3.G boundary rule. Will call `gemini.generate_text(...)` /
  `gemini.generate_vision(...)` wrapped by cost tracker + 3-layer
  guardrail + LangFuse trace + budget cap.
- **§6A `ai_ops/client.py`** — sole consumer of `adapters/langfuse.py`.
  Wraps every Gemini call with `langfuse.trace(...)` after the call
  returns (success or failure).
- **§7 `iam.service.send_otp_for_login`** — consumes
  `adapters/msg91.send_otp(phone, otp)` after rate-limit gate per
  `MVP_ARCH §10.7`. Surfaces 503 to seller when `Msg91Response.success
  is False` (the adapter never raises — caller is the 5xx gateway).
- **§7 `iam.router.razorpay_webhook`** — consumes
  `adapters.razorpay.verify_webhook_signature(payload, signature)`;
  responds 401 when False. SYNC call (no await).
- **§11 `image.service.upload_image`** + **§11 `image.tasks.process_image`**
  — consume `adapters/gcs.upload_bytes`, `gcs.download_bytes`,
  `gcs.generate_signed_url`. Path convention enforced at service layer:
  `meesell-images/{user_id}/{product_id}/{idx}.jpg`.
- **§14 `export.service.build_xlsx`** + **§14 `export.tasks.generate_export`**
  — consume `adapters/gcs.upload_bytes` (XLSX + ZIP),
  `gcs.download_bytes` (image gather), `gcs.generate_signed_url`
  (download URL on poll). Path: `meesell-exports/{user_id}/{export_id}/
  {sheet.xlsx|images.zip}`.

### Pending Secret Manager values still queued (NOT a blocker)
- `razorpay-webhook-secret` — populated by `meesell-infra-builder`
  during §7 iam dispatch (per STATUS_BACKEND L2 latent).
- `langfuse-secret-key` — populated by `meesell-infra-builder` during
  §6A ai_ops dispatch (per STATUS_BACKEND L2 latent).
Both are consumed by the adapters from `settings.*` — the adapters do
not pre-validate; missing values surface as MSG91/Razorpay/LangFuse
runtime failures that the adapter's locked failure mode already covers
(msg91 → success=False; razorpay → False; langfuse → drop-on-failure).

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §6 adapters CONSTRUCTED | project | 5 adapter files + 1 `__init__.py` + 5 test modules (73 tests); 331 regression PASS |
| AdapterError(MeesellError) root | reference | `app.adapters.AdapterError` + 5 vendor subclasses; default status=502, code=`<vendor>.unavailable` |
| Gemini retry triple | reference | `_RETRY_DELAYS_S=(1.0,4.0,16.0)` — 1 initial + 3 retries on conn/5xx/429; non-retryable raises immediately |
| msg91 NEVER raises | reference | locked exception #1 to §6.G — returns `Msg91Response(success=False, ...)` on transport / vendor failure |
| razorpay sync + bool | reference | locked exceptions #2 + #3 — `verify_webhook_signature` is `def` (not `async def`) + returns bool (never raises) |
| langfuse drop-on-failure | reference | locked exception #4 to §6.G — `trace`/`score` always return None; failures logged WARNING; missing creds = no-op + 1 WARNING (latched) |
| GCS path convention | reference | `meesell-images/{user_id}/{product_id}/{idx}.jpg` + `meesell-exports/{user_id}/{export_id}/{sheet.xlsx\|images.zip}` per §6.D + MVP_ARCH §10.8 |
| GCS signed URL TTL=3600 | reference | locked default per `settings.GCS_SIGNED_URL_TTL_SECONDS = 3600` (MVP_ARCH §10.8) |
| Lazy singleton + asyncio.Lock + `_reset_for_testing` | reference | Required pattern for every async-stateful adapter to survive pytest-asyncio function-loop tests across module loads |
| LangFuse httpx-direct (no SDK) | reference | D1 decision — POST to `{LANGFUSE_HOST}/api/public/ingestion` with batch envelope; trace-create + score-create types |
| Boundary rule: gemini consumed only by ai_ops | reference | §3.G + §16.D — §19 import-linter rejects `from app.adapters.gemini` under `app/modules/` |

---
