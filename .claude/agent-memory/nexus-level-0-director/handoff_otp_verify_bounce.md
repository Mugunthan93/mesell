---
name: handoff-otp-verify-bounce
description: HANDED to master session 2026-06-20 — develop-wide login bug (OTP verify bounces to /login, no network call); diagnosis done, partial fix on branch fix/otp-verify-pending-phone (service layer only), one open decision before completion
metadata:
  type: project
---

**OTP-verify bounce-to-login bug — handed to the master session (2026-06-20).** Do NOT continue this in the Razorpay session.

**Symptom:** local login, enter phone → OTP page renders → enter `000000` → Verify fires **NO network request**, **no console error**, app **bounces to /login**. Hard-reload + incognito did NOT help.

**Root cause (diagnosed, develop-wide — code byte-identical to origin/develop):** `frontend/apps/mfe-auth/src/app/otp-verify.component.ts` `ngOnInit` L176 hard-redirects to `/login` when the pending phone is absent from BOTH `router.getCurrentNavigation().extras.state` AND `history.state`. The phone is carried from `login.component.ts` L251 only via `history.state` (`router.navigate(['/otp-verify'], { state: { phone } })`). That state is lost when the OTP step is re-mounted / the document reloads. No authGuard on /otp-verify (it's public). `onSubmit` always calls the verify API, so "no network" proves the bounce came from `ngOnInit`, not the handler. Full diagnosis in `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md`.

**Partial fix (pushed, WIP):** branch `fix/otp-verify-pending-phone` (off develop), commit `e7e919c` = service layer only: added in-memory `setPendingPhone/pendingPhone/clearPendingPhone` signal to `@mesell/core` AuthService (+6 spec cases, tsc clean). Component wiring NOT done.

**⚠️ OPEN DECISION before completing (this is why it wasn't finished):** the in-memory signal fixes the bug ONLY if the OTP step re-mounts within the SAME JS context. If the trigger is a **full-document reload** onto `/otp-verify` (static SPA-fallback serving index.html fresh at that URL), then an in-memory signal is wiped too — same as history.state — and the fix must use **sessionStorage** instead (phone is not a token; FE-D5 governs tokens, so sessionStorage for a transient phone is defensible). DECIDE by checking the live browser: on the OTP page, `history.state` content + whether the Network tab shows a top-level **Document** request (real reload) during login→OTP. No reload → finish with the signal (dispatch angular-component-builder to wire login write + otp-verify read+soften-bounce + specs). Reload present → switch to sessionStorage AND investigate why a federated nav full-reloads.

Worktree `/tmp/mesell-wt/otp-fix` holds the WIP. Unblocks: the founder cannot manually test the Razorpay dev-mock ([[razorpay-integration-merged]]) until login works.
