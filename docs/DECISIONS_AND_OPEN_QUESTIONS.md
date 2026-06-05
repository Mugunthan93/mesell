# MeeSell — Decisions and Open Questions

**Last updated:** 2026-06-04
**Status:** Draft — Pre-execution checkpoint
**Owner:** Founder (Muguntha)
**Companions:** `docs/BUSINESS_STRATEGY.md` (canonical strategy), `docs/COST_ANALYSIS.md` (financial model)

---

## 1. Document Purpose

This document is a **living checkpoint** captured from the founder Q&A session that
preceded build start. It is not a final specification and it does not supersede
`BUSINESS_STRATEGY.md` or `COST_ANALYSIS.md`. Its job is to make the dialog-driven
refinements traceable: every confirmed constraint, every deferred decision, and every
open question that still needs founder input.

Use this file as the pre-execution gate. Before any infrastructure provisioning or
code is written for V1, the founder should walk this document top-to-bottom, convert
open questions into decisions, and sign off on the Decision Status Summary in
Section 8. After sign-off, this document becomes a historical record and the
canonical specs take over.

Nothing in this document should be interpreted as a new recommendation — it
captures only what was actually discussed.

---

## 2. Confirmed Strategic Constraints

Each row below records the question asked during the Q&A, the founder's answer,
and the immediate implication for execution.

### 2.1 Funding and Capital

| Question | Founder's Answer | Implication |
|----------|------------------|-------------|
| Bootstrap or VC funding? | **Bootstrap only.** No external capital. | All architecture and timelines must survive on founder capital + GCP credit until revenue exists. |
| Personal capital allocation during dev? | **Only Gemini API costs.** Profits fund growth post-launch. | Dev-phase spend ceiling is API usage; everything else stays on the $300 GCP credit. |
| When does the company need to be cash-positive? | Founder can deploy capital if forced, but the plan must not assume it. | Pricing and acquisition must aim for self-funding from Month 1 of launch. |

### 2.2 Team and Time

| Question | Founder's Answer | Implication |
|----------|------------------|-------------|
| Team structure? | **Solo founder + AI agents** (Claude, Gemini). No human hires. | All workflows must be solo-operable; no roles depend on a second human. |
| Time commitment? | All time available via Claude (always-on AI assistance). | Async, agent-driven SDLC is the default — not human handoffs. |
| Primary focus? | **MeeSell only.** Zenivo and Curl Candy come AFTER MeeSell generates profit. | No context-switching budget; other projects are paused, not parallel. |

### 2.3 Language and Geography

| Question | Founder's Answer | Implication |
|----------|------------------|-------------|
| Content languages? | **English only for V1.** Tamil and others later. | UI, marketing, and AI prompts are English-only at launch. |
| Geographic focus? | **Tamil Nadu sellers first** (Coimbatore, Tirupur, Salem, Madurai, Chennai), then pan-India. | Initial acquisition playbook is regional; product remains location-agnostic. |

### 2.4 Distribution Channels

| Question | Founder's Answer | Implication |
|----------|------------------|-------------|
| Existing seller network / WhatsApp group access? | **No.** | Cold acquisition only — no warm channel to seed Phase 1. |
| Tamil Nadu personal connections? | **Pending.** Needs founder to map existing contacts. | Open question — see Section 5. |
| Comfort with on-camera content (YouTube)? | **Pending.** | Open question — see Section 5. |

### 2.5 Business Operations

| Question | Founder's Answer | Implication |
|----------|------------------|-------------|
| Meesho TSP partnership program? | **No — stay under radar.** Apply later if/when needed. | Build product without depending on Meesho TSP status; avoid behaviors that would trigger detection. |
| Service marketplace (photographers, packagers)? | **Not mandatory.** Maybe Year 2. | V1 scope excludes marketplace; only the core SaaS ships. |
| Customer support model? | **AI chatbot only.** No human support team. | Support flows must be self-service; escalation path to founder defined later. |
| Brand name "MeeSell"? | **Locked for now.** | No further naming discussion until post-launch revisit. |
| Multi-marketplace appetite? | **Prove on Meesho first, then expand.** | V1 is Meesho-only; Flipkart / Amazon adapters are explicitly Phase 3+. |

### 2.6 Infrastructure

| Question | Founder's Answer | Implication |
|----------|------------------|-------------|
| GCP free tier only? | **Yes, using the $300 free credit.** | All infra sizing must respect the credit horizon (~4 months at planned spend). |
| VM strategy? | **Provision a NEW VM for actual MeeSell dev**, separate from existing `meesell-vm` (which becomes R&D). | New VM is `meesell-dev`; existing VM is preserved for experiments. |
| GCP project separation? | **Same GCP project** — credit is billing-account-level, not project-level. | One project, multiple VMs; no extra project setup needed. |
| K3s namespace strategy? | **dev -> staging -> prod** namespaces on the same VM. | Single-node K3s with three logical environments; vertical isolation only. |

### 2.7 Tech Stack

| Layer | Decision |
|-------|----------|
| Frontend | **Angular 18 + TypeScript** (enterprise, long-term maintainability) |
| Phase 2 frontend | **Module Federation** via `@angular-architects/module-federation` for micro-frontends |
| Mobile (Phase 2) | **Ionic + Capacitor** (reuses Angular code) |
| Backend | **Python + FastAPI** (REST, async, AI-friendly) |
| Database | **PostgreSQL self-hosted** via trimmed self-hosted Supabase |
| Cache / Queue | **Valkey** (license-clean Redis fork) |
| AI — text | **Gemini 2.5 Flash** |
| AI — image background removal | **rembg** |
| Payments | **Razorpay** (default for India) |
| Auth | **MSG91 OTP + JWT** (skip Supabase GoTrue; Twilio too expensive) |
| Storage | **GCS** (free 5 GB tier); skip Supabase Storage |

---

## 3. Pricing Strategy — Pending Final Confirmation

Three pricing scenarios are on the table. The founder stated that pricing depends
on a complete end-to-end cost analysis; that analysis is now complete (see
`docs/COST_ANALYSIS.md`) and Scenario B is the recommendation surfaced from it.
Final selection is the founder's call.

| Tier | Scenario A (Lean) | Scenario B (Balanced — recommended) | Scenario C (Premium) |
|------|-------------------|-------------------------------------|----------------------|
| Free | Free | Free | Free |
| Pro (monthly) | ₹299 | ₹499 | ₹999 |
| Business (monthly) | ₹999 | ₹1,999 | ₹2,999 |
| LTD (one-time) | ₹2,999 | ₹4,999 | ₹9,999 |

**Status:** Scenario B recommended by cost analysis. **Needs final founder approval
before launch.**

---

## 4. Infrastructure — Decided

### 4.1 New Dev VM

| Item | Decision |
|------|----------|
| VM name | `meesell-dev` |
| Machine type | e2-standard-2 (2 vCPU, 8 GB RAM) |
| Region / Zone | asia-south1-a |
| Boot disk | 30 GB SSD |
| Image | Ubuntu 22.04 LTS minimal |
| Cluster | K3s single-node (multi-node ready) |
| Ingress | Traefik (K3s default) |
| TLS | cert-manager + Let's Encrypt |
| Namespaces | `dev` -> `staging` -> `prod` |
| Domain | **TBD** (founder to confirm: meesell.in, meesell.com, etc.) |
| Cost during $300 credit | ₹0 for approximately 4 months |
| Cost post-credit | ₹5,900 / month at 8 GB, or ₹2,400 / month after downsize to 4 GB |

### 4.2 Existing VMs

| VM | Status | Disposition |
|----|--------|-------------|
| `meesell-vm` (e2-standard-2, RUNNING at 34.93.9.139) | Keep | Repurposed for **R&D only** — no production workloads. |
| `shotfox-platform` | RUNNING | Evaluate for shutdown later to extend credit horizon. |
| `shotfox-mvp1-alpha-dev` | RUNNING | Evaluate for shutdown later to extend credit horizon. |

---

## 5. Pre-Execution Open Questions

These items need founder input before execution begins. Items are grouped by
domain. Each is a hard gate for the affected workstream.

### 5.1 Strategic

- [ ] Final pricing scenario — A, B, C, or custom?
- [ ] Domain ownership — `meesell.in`, `meesell.com`, `meesell.co.in`, or other?
- [ ] Existing brand assets — logo, social handles, domain already secured?
- [ ] Legal entity status — sole proprietorship, Pvt Ltd, or LLP?
- [ ] GST registration — required from start (₹20L threshold) or deferred until crossed?
- [ ] Mission statement depends on subscription pricing — confirm Scenario B?

### 5.2 Tamil Nadu Connections

- [ ] CAs / accountants who serve sellers — any existing relationships?
- [ ] Tirupur Exporters Association — any contacts inside?
- [ ] Coimbatore / Madurai / Chennai seller relationships?
- [ ] Tamil YouTubers in the e-commerce space — any contacts?

### 5.3 Content and Marketing

- [ ] Comfort with on-camera YouTube content — founder-led vs faceless brand?
- [ ] Existing English content production capability — writing, editing, design?

### 5.4 Phase 1 Distribution

- [ ] Top three acquisition channels confirmed?
- [ ] Founder time commitment to Phase 1 hustle — Month 1-3, 50+ hours / week?

### 5.5 Tech Stack Confirmations

- [ ] Founder coding experience with Angular — comfortable, or learning curve acceptable?
- [ ] FastAPI / SQLAlchemy comfort level?
- [ ] Existing repo code (~1,400 LOC) — keep, refactor, or rewrite from scratch?

### 5.6 Infrastructure Specifics

- [ ] Provision `meesell-dev` VM now, or delay until other gates clear?
- [ ] When to stop the shotfox VMs to extend the $300 credit?
- [ ] Backup strategy for production PostgreSQL — GCS backup cronjob cadence and retention?

---

## 6. Confirmed Assets Already in Hand

These are existing assets that do not need to be re-built or re-acquired before V1.

| Asset | Detail |
|-------|--------|
| Meesho category templates | **3,772 templates scraped** at `data/meesho_templates/` (278 MB) |
| Category tree JSON | `backend/app/data/meesho_category_tree.json` (1.6 MB) |
| Scraper infrastructure | `meesho_batch_scraper.py` — hybrid Playwright + httpx, working |
| Existing repo code | ~1,400 LOC Python / FastAPI from prior agent work, K3s manifests, Terraform |
| Hair Accessories deep-dive | Sample XLSX studied; fields and dropdowns documented |
| GCP project + billing | `project-1f5cbf72-2820-4cdb-949`, $300 credit active |
| Existing `meesell-vm` | e2-standard-2 running, repurposed for R&D |
| Business strategy doc | `docs/BUSINESS_STRATEGY.md` (393 lines) |
| Cost analysis doc | `docs/COST_ANALYSIS.md` (806 lines) |
| Playwright MCP reference | `docs/PLAYWRIGHT_MCP_REFERENCE.md` (440 lines) |

---

## 7. Discussion Topics Still to Cover

The founder flagged that "many things" remain to be discussed before execution.
The following discussion areas were named or implied during the Q&A and are not
yet covered by any other document. Each item is a future conversation, not an
open decision.

- [ ] Product feature prioritization — which features ship in V1 vs V2
- [ ] User onboarding flow design
- [ ] Detailed acquisition playbook for Phase 1 — week-by-week breakdown
- [ ] LTD launch mechanics — when, how, who, marketing approach
- [ ] Content production schedule — YouTube cadence, blog cadence
- [ ] Legal compliance specifics — privacy policy, terms of service, GST invoicing
- [ ] Support workflow — when the AI chatbot escalates to the founder
- [ ] Metrics dashboard — what we track and when we review it
- [ ] Founder weekly schedule template
- [ ] First seller validation — interview 10 Tamil sellers before building

---

## 8. Decision Status Summary

| Domain | Status | Notes |
|--------|--------|-------|
| Funding model | Decided | Bootstrap only |
| Team | Decided | Solo founder + AI |
| Geography | Decided | Tamil Nadu first |
| Languages | Decided | English V1; Tamil later |
| Brand name | Decided | MeeSell (locked for now) |
| Frontend stack | Decided | Angular 18 + TypeScript |
| Backend stack | Decided | Python + FastAPI |
| Database | Decided | PostgreSQL via self-hosted Supabase |
| Auth | Decided | MSG91 OTP + JWT |
| Payments | Decided | Razorpay |
| AI provider | Decided | Gemini 2.5 Flash + rembg |
| Storage | Decided | GCS free tier |
| Cache / Queue | Decided | Valkey |
| Infrastructure | Decided | New `meesell-dev` VM + K3s; existing `meesell-vm` -> R&D |
| GCP project model | Decided | Single project, multi-VM |
| K3s namespaces | Decided | dev -> staging -> prod |
| Meesho TSP | Decided | No — stay under radar |
| Service marketplace | Decided | Out of scope for V1 |
| Customer support | Decided | AI chatbot only |
| Multi-marketplace | Decided | Meesho first; expand post-validation |
| Pricing | Pending | Scenario B recommended; awaiting founder approval |
| Domain | Open | Founder to confirm registration |
| Brand assets (logo, handles) | Open | Founder to confirm |
| Legal entity | Open | Founder to confirm |
| GST registration timing | Open | Founder to decide |
| Tamil Nadu connections | Open | Founder to map existing contacts |
| On-camera content comfort | Open | Founder to confirm |
| English content capability | Open | Founder to confirm |
| Phase 1 acquisition channels | Open | Top 3 to be selected |
| Phase 1 time commitment | Open | 50+ hrs / week confirmation needed |
| Angular comfort level | Open | Founder to confirm |
| FastAPI / SQLAlchemy comfort | Open | Founder to confirm |
| Existing repo disposition | Open | Keep / refactor / rewrite decision needed |
| Provision new VM | Open | Awaiting go-ahead |
| Shotfox VM shutdown timing | Open | Credit-runway driven |
| Prod DB backup strategy | Open | Cadence and retention TBD |

---

**End of pre-execution checkpoint.** All "Decided" rows are locked unless the
founder explicitly re-opens them. All "Open" and "Pending" rows must be resolved
before any infrastructure provisioning or production code is written for V1.
