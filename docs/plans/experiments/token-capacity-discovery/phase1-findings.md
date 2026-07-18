# Phase 1 — Meter-Sensor POC: findings

**Status:** DRAFT — POC done 2026-07-18. **Result: the live % sensor is the blocker.**

## Sensor routes tested
| route | outcome |
|---|---|
| 1. `/usage` in-app | ground truth, **manual only** |
| 2. agent-browser scrape of `claude.ai/settings/usage` | **BLOCKED by Cloudflare** bot-verification ("Just a moment…", Ray ID) — an automated browser cannot pass. Dead for unattended use. |
| 3. OAuth/Keychain endpoint | keychain item **exists** (`svce="Claude Code-credentials"`, `acct=root`); endpoint undocumented → **not pursued unattended** |
| 4. `anthropic-ratelimit-*` headers | subscription (OAuth) mode does **not** expose plan % — closed door |

## Consequence
- The 90% guard could **not** be enforced by live measurement tonight. Substitute: the **self-sourced ledger gauge** (current-window BW ÷ max-ever window BW). Current window ≈ 1.5% → tiny probes provably safe.
- **Tick/bounds capacity calibration (plan §4) is BLOCKED** until a % sensor exists — it needs paired (%, tokens) samples.

## What worked (different axis)
- **OTEL** (Group 2) delivers token receipts + cost + `query_source` locally — but that is the **numerator (tokens)**, not the **% meter (denominator)**. Complementary, not a substitute for the sensor.

## Capacity anchor — a real, sensor-free Phase-1 result
- Largest completed 5h window = **81.88M BW** with no reported hard stop → **capacity LOWER BOUND ≈ 81.88M BW**. One paired % reading later converts this to an exact constant.

## Founder decision needed — pick a % sensor
- **(a)** Seed agent-browser once via a **headed** logged-in claude.ai profile that has passed Cloudflare; persist it → unattended scrape thereafter.
- **(b)** Authorize the **OAuth-endpoint** route (identify the real usage endpoint + use the Keychain token) — fastest clean JSON, undocumented/fragile.
- **(c)** **Manual `/usage` bracketing** for Phase-2 probe batches (founder present) — no automation, simplest.
