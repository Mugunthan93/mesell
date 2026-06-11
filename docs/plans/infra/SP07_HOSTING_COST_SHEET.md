# SP07 — D13 Hosting Cost Sheet (remotes.mesell.xyz GCS + Cloud CDN + LB)

**Author:** `meesell-infra-builder` · **Session:** `mesell-mfe-cutover-infra-session-1` · **Date:** 2026-06-11
**Purpose:** the cost figure the FOUNDER signs off BEFORE infra provisions any billable resource (§5 of `SP07_CSP_AND_HOSTING.md`). Refreshed from GATE4 C-CDN-1.
**Region:** asia-south1 (Mumbai). FX assumption: 1 USD ≈ ₹84.
**Status:** ESTIMATE ONLY — nothing provisioned. **> ₹500/month → HARD FOUNDER COST GATE.**

---

## 1. Headline

**~₹1,600–1,800 / month, LB-dominated.** The single global external HTTPS load balancer forwarding rule is ~70% of the bill; everything else (GCS storage, CDN egress at MeeSell's V1 traffic, managed cert) is small.

This **exceeds the ₹500/month autonomous spend gate** → infra does NOT provision until the founder signs off this sheet.

---

## 2. Line items (monthly, steady-state V1 traffic)

| # | Resource | Basis | Est. USD/mo | Est. ₹/mo | Notes |
|---|---|---|---|---|---|
| 1 | Global external HTTPS LB — forwarding rule | standing charge ~$0.025/hr × ~730 hr | ~$18.25 | **~₹1,530** | THE cost driver. One forwarding rule covers both `remotes.mesell.xyz` + `remotes-staging.mesell.xyz` (one LB, two host rules in the URL map). A 2nd forwarding rule (e.g. separate prod/staging LBs) would roughly double this — recommend ONE LB, host-routed. |
| 2 | LB — data processed | first 5 rules + per-GB inbound; negligible at V1 | ~$0–1 | ~₹0–85 | tiny at launch volume |
| 3 | Cloud CDN — cache egress (Asia) | ~$0.09/GB after cache fill; V1 ≈ a few GB/mo of static JS/CSS | ~$0.50–2 | ~₹40–170 | static remotes are small + highly cacheable; egress is low. Scales with users. |
| 4 | Cloud CDN — cache fill / lookups | per-request + fill | ~$0–0.50 | ~₹0–40 | negligible at V1 |
| 5 | GCS — storage | 6 remotes × a few versions × ~5–20 MB each ≈ <1 GB; $0.020/GB-mo (standard, asia-south1) | ~$0.02–0.10 | ~₹2–8 | trivial; versioning keeps a few prior `{version}` builds for atomic rollback |
| 6 | GCS — operations | rsync writes on each build (Class A) + CDN reads (Class B) | ~$0.05–0.20 | ~₹4–17 | trivial |
| 7 | GCP-managed SSL cert | free | $0 | ₹0 | `google_compute_managed_ssl_certificate` is no-charge; covers both hosts |
| 8 | Namecheap A records | already-owned domain | $0 | ₹0 | founder-owned `mesell.xyz`; just new A records |
| | **TOTAL** | | **~$19–24** | **~₹1,600–1,800** | LB forwarding rule dominates |

---

## 3. Cost-reduction options (for the founder's decision)

| Option | Monthly | Trade-off |
|---|---|---|
| **A. Full LB + Cloud CDN (this sheet)** | ~₹1,600–1,800 | Best perf + global anycast + native CDN. The GATE4-recommended Option C path. |
| **B. GCS website hosting (no LB, no Cloud CDN)** | ~₹50–150 | Drops the ~₹1,530 LB charge. BUT: GCS static-website does NOT support HTTPS on a custom domain natively — needs a CDN/LB in front for TLS on `remotes.mesell.xyz`, OR Cloudflare (free tier) as the TLS/CDN edge. Cloudflare-in-front = ~₹0 extra but adds a non-GCP dependency + a 3rd-party in the pre-auth asset path (CSP `script-src` must then allowlist the Cloudflare-served origin — same host, so transparent). |
| **C. Defer staging host; prod-only LB at V1.5** | ~₹1,600–1,800 only when prod lights | Staging remotes served from localhost/dev during V1; the LB stands up only at the V1.5 prod cutover. Saves the standing charge during the V1 dev/staging window. **Recommended interim** — aligns with prod-namespace-deferred-to-V1.5 (master plan §3.1). |

**Infra recommendation:** Option **C** for V1 (no standing LB charge until prod lights at V1.5), then Option **A** at V1.5 prod. If the founder wants a live `remotes-staging.mesell.xyz` before V1.5, Option **B with Cloudflare** is the cheapest HTTPS-capable path (~₹0 extra) but adds a 3rd-party edge — founder's call.

---

## 4. What the founder is signing off

By approving this sheet, the founder authorizes infra to provision (in a SEPARATE post-sign-off session):
- 1 GCS bucket `gs://meesell-frontend` (asia-south1, versioned, world-read objects).
- 1 Cloud CDN backend-bucket + 1 global HTTPS LB (1 forwarding rule, host-routed for both `remotes` + `remotes-staging`).
- 1 GCP-managed SSL cert (both hosts).
- 1 `storage.objectAdmin` IAM grant for the Cloud Build compute SA on that bucket.

And to action (founder, Namecheap): A records `remotes.mesell.xyz` + `remotes-staging.mesell.xyz` → the LB IP (infra supplies the IP post-provision).

**Until that sign-off:** the `cloudbuild.yaml` `publish-remotes` step stays INERT (`_REMOTES_BUCKET=""`), all dev validation uses localhost remotes, and the frontend cleanup lands on develop in parallel (R-SP7-4). Per the >₹500/mo gate, this provisioning is NOT autonomous.

---

## 5. Presentation path

Per spec §4: infra presents this cost to the founder via `STATUS_MASTER.md` (or the agreed founder surface). This sheet is the artifact. The `feature_board_infra.md` Inter-lead-requests-open row (incoming, from frontend) carries the pointer; the `STATUS_INFRA.md` session entry links here. Escalation SLA 48h.
