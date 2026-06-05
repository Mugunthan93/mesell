---
name: reference-namecheap-lookup
description: Reusable Playwright script for Namecheap domain lookup at scripts/namecheap-domain-lookup.mjs — env-var credentials, never persisted
metadata:
  type: reference
---

MeeSell project has a reusable Namecheap domain lookup script at `scripts/namecheap-domain-lookup.mjs` with full README at `scripts/namecheap-domain-lookup.README.md`. Use it whenever the user or an agent needs to inspect domain state (nameservers, expiration, auto-renew status) for `mesell.xyz` or other domains in the same Namecheap account.

**Invocation pattern (agent reuse):**
```
NAMECHEAP_USER=Mugunthan93 \
NAMECHEAP_PASS="$(<password from user / password manager>)" \
NAMECHEAP_TOTP=<6-digit current code> \
  node scripts/namecheap-domain-lookup.mjs <domain>
```

**Exit codes:** 0 success, 2 needs TOTP, 3 login fail, 4 domain not in account, 5 selector drift (UI changed), 6 Playwright error.

**Agent discipline:** never write the password into a dispatch prompt or memory file. If TOTP is needed, ask the user fresh each time (codes expire ~30s). For unattended automation, switch to the official Namecheap API instead — script is for human-supervised use only.

Domain `mesell.xyz` was registered 2026-06-04 for the MeeSell project. Registrar: Namecheap. Account: Mugunthan93.
