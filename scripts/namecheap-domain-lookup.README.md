# Namecheap Domain Lookup — Reusable Flow

A headless Playwright script that logs into Namecheap and extracts domain
details. Designed for agent reuse and operator one-off lookups.

## Why this exists

The MeeSell domain `mesell.xyz` is registered at Namecheap. Future operations
(DNS record audit, expiration check, nameserver inspection, registrar transfer)
may need to read this state programmatically. Namecheap's retail API requires
IP whitelisting and a separate API key — for one-off reads from a single
laptop, this script is the lighter path.

**For production DNS automation, switch to the Namecheap API.** This script is
for human-supervised use, not unattended cron jobs.

## Security model

| Concern | Mitigation |
|---------|-----------|
| Password leakage | Read from env var only. NEVER stored in this repo. Recommend pulling from a password manager CLI (`op`, `bw`, `pass`). |
| Session persistence | None. Each invocation is a fresh browser, no cookie/state save. |
| 2FA code leakage | Read from env var (preferred) or interactive stdin. Codes are time-bound and useless after ~30s. |
| Output redaction | The script's stdout JSON contains domain metadata only — no credentials, no session tokens. |
| Headed mode for debugging | `NAMECHEAP_HEADLESS=false` shows the browser. Use only on a machine you trust. |

**NEVER commit credentials.** The script reads from env vars exactly so they
never touch git history.

## Prerequisites

```bash
# In the mesell repo root
npm install playwright   # first time only
npx playwright install chromium   # downloads the headless browser
```

Node.js ≥ 18 required. macOS, Linux, or WSL.

## Usage

### One-off interactive lookup

```bash
export NAMECHEAP_USER='Mugunthan93'
export NAMECHEAP_PASS="$(read -s -p 'Namecheap password: ' p && echo "$p")"
export NAMECHEAP_TOTP='123456'   # current TOTP from your authenticator app
node scripts/namecheap-domain-lookup.mjs mesell.xyz
```

Output is JSON on stdout:

```json
{
  "found": true,
  "domain": "mesell.xyz",
  "rawText": "mesell.xyz Active Expires: Jun 04, 2027 Auto-renew: On Nameservers: dns1.namecheap.com dns2.namecheap.com ...",
  "expirationCandidate": "Jun 04, 2027",
  "autoRenew": true,
  "nameservers": ["dns1.namecheap.com", "dns2.namecheap.com"]
}
```

### From a password manager (recommended)

```bash
# 1Password CLI
NAMECHEAP_USER='Mugunthan93' \
NAMECHEAP_PASS="$(op read 'op://Personal/Namecheap/password')" \
NAMECHEAP_TOTP="$(op item get 'Namecheap' --otp)" \
  node scripts/namecheap-domain-lookup.mjs mesell.xyz
```

```bash
# Bitwarden CLI
NAMECHEAP_USER='Mugunthan93' \
NAMECHEAP_PASS="$(bw get password 'Namecheap')" \
NAMECHEAP_TOTP="$(bw get totp 'Namecheap')" \
  node scripts/namecheap-domain-lookup.mjs mesell.xyz
```

### Debugging selector drift

If Namecheap updates their HTML, the script may fail. Run in headed mode:

```bash
NAMECHEAP_HEADLESS=false \
NAMECHEAP_USER='Mugunthan93' \
NAMECHEAP_PASS='...' \
NAMECHEAP_TOTP='...' \
  node scripts/namecheap-domain-lookup.mjs mesell.xyz
```

The browser stays open on error. Inspect the failing selector, update the
script at the `SELECTOR CHECKPOINT` comments, recommit.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success — JSON on stdout |
| 1 | Usage error (missing arg or required env var) |
| 2 | 2FA prompted but `NAMECHEAP_TOTP` not set — re-run with fresh code |
| 3 | Login failed (wrong credentials, account locked, expired TOTP) |
| 4 | Domain not found in this account |
| 5 | Selector drift — Namecheap UI changed, script needs update |
| 6 | Network or Playwright launch error |

## Agent reuse pattern

An orchestrating agent (e.g., Director or `nexus:level-3:infra-builder`) can
invoke this script like any other CLI tool. The recommended flow:

1. Agent asks user for credentials via env vars (or pulls from password
   manager via the user's shell).
2. Agent runs the script.
3. If exit code 2: agent asks user for a fresh TOTP code, re-runs immediately
   (within the ~30s TOTP window).
4. If exit code 5: agent flags selector drift, leaves it for an operator —
   does not attempt auto-repair.
5. Output JSON is parsed by the agent and used downstream (e.g., to write a
   DNS record via a different API).

**The agent must NEVER:**
- Persist the password to disk or to its memory store
- Echo the password back to the user in plain text
- Include the password in a dispatch prompt to another agent (agent prompts
  are typically logged)
- Try to derive a TOTP secret from a one-time code (mathematically impossible
  and wrong)

## When to switch to the Namecheap API

This script is fine for ad-hoc reads. Switch to the API when:

- You need to make DNS record changes programmatically (the API supports it)
- You want unattended cron-style runs (the API doesn't need 2FA)
- You hit selector drift more than once in a quarter

API setup: [namecheap.com/Profile/Tools/ApiAccess](https://www.namecheap.com/Profile/Tools/ApiAccess/).
Requires whitelisting your egress IP and generating an API key. The same
domain-detail call becomes a single signed HTTPS request.

## Related project files

- `/Users/mugunthansrinivasan/Project/mesell/docs/INFRASTRUCTURE_PLAYBOOK.md` — section §9 (ingress) consumes the domain
- `/Users/mugunthansrinivasan/Project/mesell/docs/INFRASTRUCTURE_TERRAFORM_PLAN.md` — sections §8, §9, §20 reference domain for cert-manager + Ingress
- `/Users/mugunthansrinivasan/Project/mesell/infra/terraform/environments/dev.tfvars` — `var.domain` is set here when Pass 2b activates
