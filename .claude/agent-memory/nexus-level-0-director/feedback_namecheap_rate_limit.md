---
name: feedback-namecheap-rate-limit
description: Namecheap device-verification has a low rate limit (~5 attempts/hour, ~45min lockout) — cap script debug iterations
metadata:
  type: feedback
---

Namecheap's "Device Verification" email flow rate-limits aggressively. After 4-5 failed/missed verification attempts within ~30 minutes, the account is locked for ~45 minutes with a visible "Limit exceeded, please try again in 44:02" message — even password is correct and codes are real.

**Why:** Each fresh browser session = new device fingerprint = new verification email. Repeated script debugging burns the quota fast. Once Namecheap shows the lockout banner, NO further attempts succeed until the timer expires.

**How to apply:** When scripting Namecheap login (via `scripts/namecheap-domain-lookup.mjs` or `scripts/namecheap-dns-set.mjs`):
1. STOP debugging after 2 wrong/missed codes — don't burn more attempts. Fix the selector locally without hitting Namecheap.
2. Persist the browser session across script runs (`launchPersistentContext` with a stable userDataDir) so Namecheap doesn't issue a fresh device-verification per run.
3. Or switch to the Namecheap API for write operations — no rate limit on signed HTTPS calls.
4. If lockout hits: wait the full 45 min before retrying; don't half-wait.

Related: see [[reference-namecheap-lookup]] for the script paths.
