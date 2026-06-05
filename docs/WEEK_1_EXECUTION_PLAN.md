# Mesell V1 — Week 1 Execution Plan

Last updated: 2026-06-04
Status: 7-day sprint plan v1
Sprint dates: 2026-06-04 to 2026-06-10

---

## Section 1 — Week Overview

**Goal:** V1 deployable to `staging.meesell.in` by end of Tuesday June 10, with a working end-to-end demo (signup → category pick → form → AI fill → image precheck → preview → price calc → XLSX export).

**Operating model:** Solo founder + "always-on Claude" + Nexus agents. Founder is the integrator, reviewer, and decision-maker. Agents write ~80% of code; founder spends ~10-12 hrs/day on prompts, reviews, integration, manual testing, and infra approvals.

**Critical path:**
VM provisioned (Day 1) → DB schema + auth backend (Day 2) → core AI/product APIs (Day 3) → Angular shell + auth UI (Day 4) → catalog creation UI (Day 5) → preview/price/export (Day 6) → polish + staging deploy (Day 7).

**Hard locks (no changes this week):** Angular 18, FastAPI + SQLAlchemy async, PostgreSQL 16 on K3s, Valkey 8, MSG91 OTP + JWT, Razorpay deferred to V1.5, Gemini 2.5 Flash + rembg, GCS direct, GitLab CI + kubectl.

**Out of scope this week:** Razorpay, multi-tenant billing, email notifications beyond OTP, marketing campaigns, mobile app, LTD launch.

**Total AI dev cost budget:** ₹500-2,000 for the week (Gemini 2.5 Flash dev traffic + Vertex free credit).

---

## Section 2 — Day-by-Day Plan

### DAY 1 — WEDNESDAY June 4 (TODAY)

**Goal:** Infrastructure foundation locked — K3s cluster live with PostgreSQL + Valkey in `dev` namespace.

**Critical path:**
1. Provision `meesell-dev` VM: `e2-standard-2`, `asia-south1-a`, Ubuntu 22.04, 50 GB SSD, static IP.
2. Install K3s (single-node), `cert-manager`, Traefik ingress; create `dev`, `staging`, `prod` namespaces.
3. Deploy PostgreSQL 16 pod (StatefulSet, 20 GB PVC) and Valkey 8 pod into `dev`.
4. Buy/configure domain (`meesell.in`); point `*.meesell.in` A-record to VM static IP.
5. Apply for MSG91 account + Razorpay account (parallel — both need ~24-48 hr KYC).
6. Create GCS bucket `meesell-dev-uploads` (asia-south1, uniform access).

**Agent dispatches:**
- `nexus:level-3:infra-builder` — VM provisioning script, K3s install, namespace bootstrap.
- `nexus:level-3:database-builder` — PostgreSQL StatefulSet + initial role/db creation.

**Success criteria (end of day):**
- [ ] `kubectl get nodes` returns Ready from local kubeconfig over SSH tunnel.
- [ ] `kubectl get pods -n dev` shows `postgres-0` and `valkey-0` Running.
- [ ] `psql` connects via `kubectl port-forward` and `CREATE DATABASE meesell_dev` succeeds.
- [ ] `meesell.in` resolves to VM IP (propagation may be partial; check from 2 networks).
- [ ] MSG91 + Razorpay application emails submitted.

**Risks for this day:**
- GCP quota for `e2-standard-2` in `asia-south1` (mitigation: request increase if denied, or fall back to `asia-south2`).
- DNS propagation delay (mitigation: start within first 2 hrs; not blocking other work).
- K3s + cert-manager version mismatch (mitigation: pin K3s `v1.30.x` + `cert-manager v1.15.x`).

**What to do if stuck:** If K3s install loops on TLS, fall back to plain `k3sup install` and skip Traefik IngressClass until Day 2. If VM provisioning fails, run a local Docker Compose stack (`docker-compose.dev.yml` already exists) and continue Day 2 against `localhost`.

**Hand-off to next day:** Working kubeconfig in `~/.kube/meesell-dev`; PostgreSQL connection string; Valkey connection string; GCS bucket name and service-account key path.

---

### DAY 2 — THURSDAY June 5

**Goal:** Backend scaffold with working phone-OTP auth and category catalogue loaded.

**Critical path:**
1. FastAPI project scaffold under `backend/` (Pydantic v2, structured logging, settings via env, Dockerfile).
2. SQLAlchemy 2.0 async + Alembic; initial migration creates `users`, `catalogs`, `products`, `categories`, `category_schemas`, `images`.
3. MSG91 OTP integration: `POST /auth/otp/send`, `POST /auth/otp/verify` returning JWT (HS256, 7-day expiry).
4. `GET /me` protected endpoint via JWT dependency.
5. Seed script: load 3,772 categories from `data/` into `categories` table; load per-category JSON schemas into `category_schemas`.
6. Build + push Docker image to GitLab registry; deploy to `dev` namespace as `meesell-api` (1 replica).
7. Health checks: `/healthz` (liveness), `/readyz` (db + valkey ping).

**Agent dispatches:**
- `nexus:level-3:api-routes-builder` — auth routes + `/me`.
- `nexus:level-3:services-builder` — MSG91 client wrapper, JWT issue/verify service.
- `nexus:level-3:database-builder` — Alembic baseline migration + seed script.
- `nexus:level-3:unit-test-builder` — auth flow tests (OTP mock, JWT roundtrip).

**Success criteria (end of day):**
- [ ] `curl POST /auth/otp/send` to founder's phone delivers an SMS.
- [ ] `curl POST /auth/otp/verify` returns a JWT.
- [ ] `curl GET /me` with the JWT returns the user record.
- [ ] `SELECT COUNT(*) FROM categories` = 3,772.
- [ ] `kubectl get pods -n dev` shows `meesell-api-*` Running with passing readiness probe.

**Risks for this day:**
- MSG91 KYC not yet approved (mitigation: dev-mode endpoint that returns OTP in response body when `ENV=dev`; switch to live SMS once KYC clears).
- Alembic async config friction (mitigation: use the published `async_engine` template; do not invent).
- Category JSON schemas missing fields (mitigation: store raw schema as `JSONB`; fail-open in renderer).

**What to do if stuck:** If MSG91 not approved by EOD, ship the dev-mode OTP path and keep going; auth UI on Day 4 still works against the dev endpoint. If Alembic refuses to autogenerate, write the first migration by hand — there is only one.

**Hand-off to next day:** Backend pod live in `dev` with auth working; DB has all 3,772 categories with schemas; Docker image tag pinned for rollback.

---

### DAY 3 — FRIDAY June 6

**Goal:** All core backend APIs callable — category picker, product CRUD, AI auto-fill, image upload + precheck.

**Critical path:**
1. `POST /categories/suggest` — Gemini 2.5 Flash; takes product description, returns top-3 categories from 3,772 with confidence scores.
2. `GET /categories/{id}/schema` — returns dynamic form schema (fields, types, required, options).
3. Product CRUD: `POST/GET/PATCH /catalogs/{id}/products` (draft state machine: `draft → ready → exported`).
4. `POST /products/{id}/autofill` — Gemini fills missing fields from name + 1 image.
5. `POST /images/upload` — signed GCS upload URL flow (client uploads direct to GCS, backend records key).
6. `POST /images/{id}/precheck` — Celery task: rembg background removal → CMYK detection (Pillow ICC profile check) → watermark heuristic → white-BG verification → returns pass/warn/fail with reasons.
7. Wire Celery worker + beat as separate K8s Deployment in `dev`; Valkey is broker + result backend.

**Agent dispatches:**
- `nexus:level-3:api-routes-builder` — products, categories, images routes.
- `nexus:level-3:services-builder` — Gemini client wrapper with retry + cost logging.
- `nexus:level-3:prompt-engineer` — category-suggest prompt and autofill prompt (locked + versioned).
- `nexus:level-3:python-developer-agent` — rembg + Pillow precheck pipeline as Celery task.
- `nexus:level-3:unit-test-builder` — fixtures for category suggest (3 sample descriptions) and precheck (CMYK sample, watermark sample, clean sample).

**Success criteria (end of day):**
- [ ] `curl POST /categories/suggest` with "cotton kurti for women" returns 3 plausible category IDs.
- [ ] `GET /categories/{id}/schema` returns a usable schema for at least 5 sampled categories.
- [ ] Create draft → patch fields → list drafts via curl works end-to-end.
- [ ] Upload an image via signed URL, run precheck, receive structured result.
- [ ] Celery worker pod Running; precheck round-trip < 8 s for a 2 MB JPEG.

**Risks for this day:**
- Gemini latency spikes (mitigation: set 12 s timeout, surface fallback "try again" to UI).
- rembg model download bloats image size (mitigation: bake model into Docker image at build time, not first-run).
- Signed-URL CORS issues from browser (mitigation: configure GCS bucket CORS on Day 1; verify with curl today).

**What to do if stuck:** If Gemini quotas hit, switch the dev key to a second Google account; if precheck is flaky, ship only CMYK detection today and defer watermark/white-BG to Day 6 polish.

**Hand-off to next day:** All backend endpoints documented in a single `backend/API.md` table (path, method, payload, response) so the frontend agent can wire UI without reading code.

---

### DAY 4 — SATURDAY June 7

**Goal:** Angular app scaffolded, auth UI works against live backend, empty dashboard rendered.

**Critical path:**
1. `ng new` Angular 18 standalone-components app under `frontend/`; add Tailwind, Angular Material (with theming), Angular Router.
2. Global HTTP interceptor: attach `Authorization: Bearer <jwt>`, refresh on 401, surface error toasts.
3. Auth pages: phone number entry → OTP entry → success redirect; matches existing wireframes in `docs/03-wireframes/`.
4. Dashboard skeleton: top nav (logo, user menu), left nav (Catalogs, Products, Settings), empty-state hero with "Create your first catalog" CTA.
5. Route guards: `/auth/*` public, everything else requires JWT.
6. Dockerize Angular (multi-stage build → nginx); deploy to `dev` namespace as `meesell-web`.
7. Traefik IngressRoute: `dev.meesell.in` → `meesell-web`, `api.dev.meesell.in` → `meesell-api`.

**Agent dispatches:**
- `nexus:level-3:nextjs-developer-agent` — adapt for Angular; pair-prompt with founder for Angular-specific patterns (standalone components, signals where appropriate).
- `nexus:level-3:infra-builder` — Traefik IngressRoute + cert-manager ClusterIssuer (staging Let's Encrypt to avoid rate limits).

**Success criteria (end of day):**
- [ ] `https://dev.meesell.in` loads the Angular app (self-signed or staging cert OK).
- [ ] Phone number entry → OTP entry → dashboard works against live backend.
- [ ] JWT persists across refresh (stored in `localStorage`, validated by interceptor).
- [ ] `/me` data renders in user menu.
- [ ] Lighthouse mobile score ≥ 70 on dashboard (sanity check — not a blocker).

**Risks for this day:**
- Angular agent fluency lower than Next.js (mitigation: founder writes the first 2 components by hand as patterns, then agents follow).
- cert-manager rate limits if retried (mitigation: start with Let's Encrypt staging; switch to prod only on Day 7).
- CORS between `dev.meesell.in` and `api.dev.meesell.in` (mitigation: explicit `CORSMiddleware` allowlist in FastAPI).

**What to do if stuck:** If Angular Material theming eats more than 90 minutes, skip Material for now and use raw Tailwind components; theme can be retrofitted Day 7. If Traefik IngressRoute fights cert-manager, use `kubectl port-forward` for the day and ship the ingress on Day 5.

**Hand-off to next day:** Logged-in user lands on dashboard; backend reachable from frontend; shared `models.ts` types generated from FastAPI OpenAPI schema (`openapi-typescript`).

---

### DAY 5 — SUNDAY June 8

**Goal:** Full catalog creation flow in the UI — pick category, fill form, AI auto-fill, image upload with precheck.

**Critical path:**
1. "New Catalog" flow: name + description input → calls `/categories/suggest` → renders 3 chips + "search all 3,772" fallback.
2. Dynamic form renderer: reads `category_schemas` JSON, renders Material inputs by type (text, number, select, multiselect, textarea), enforces required.
3. AI Auto-fill button: sends current product state + first image → fills empty fields → diff highlight on changed fields (user must confirm).
4. Image upload component: drag-drop, multi-image, progress, calls signed URL flow, triggers precheck, displays per-image badges (pass / warn / fail with reasons).
5. Draft autosave every 5 s to `/catalogs/{id}/products/{id}` (PATCH).

**Agent dispatches:**
- `nexus:level-3:nextjs-developer-agent` — catalog flow components (with Angular adaptation).
- `nexus:level-3:prompt-engineer` — refine autofill prompt based on real category schemas (likely 2-3 iterations today).
- `nexus:level-3:unit-test-builder` — schema-renderer tests for the 5 most common field types.

**Success criteria (end of day):**
- [ ] Founder creates a draft catalog end-to-end through the UI: name → category pick → form fill → 2 images → autofill → save.
- [ ] Draft persists across reload (autosave proven).
- [ ] Image precheck badges render with reason text, not just colours.
- [ ] AI Auto-fill diff is visible and reversible per field.

**Risks for this day:**
- Schema variance across 3,772 categories breaks renderer (mitigation: renderer falls back to generic text input for unknown types; log unknown types for triage).
- Autofill returns wrong types (e.g., string for number) (mitigation: server-side coercion + client-side validation; reject with user-visible reason).
- Mobile keyboard covers form on small screens (mitigation: `scrollIntoView` on focus; not perfect but acceptable for V1).

**What to do if stuck:** If the schema renderer can't handle 3 field types by EOD, restrict V1 to the top 50 categories (covers ~80% of sellers per the R&D doc) and document the limitation in `docs/05-specs/`.

**Hand-off to next day:** End-to-end catalog draft creation works; at least 3 categories tested top-to-bottom; autofill produces usable output on 8/10 attempts.

---

### DAY 6 — MONDAY June 9

**Goal:** Preview, price calculator, tracking dashboard, XLSX export — closing the user journey.

**Critical path:**
1. Live Product Preview component: side-by-side card showing how listing renders (title, price, primary image, key attributes) — matches Meesho card style.
2. Price Calculator UI: inputs (cost, target margin %, Meesho commission %, GST %), outputs (MRP, your earning, breakdown table); persisted to product.
3. Tracking Dashboard: table of catalogs with status (draft / ready / exported), product count, last-edited; row-click → catalog detail.
4. XLSX Export: `GET /catalogs/{id}/export.xlsx` — server-side build using `openpyxl` in Meesho's import format; UI button triggers download.
5. End-to-end smoke test: signup → suggest category → create catalog → add 3 products → autofill → upload images → preview → price → export → download XLSX → manually open in Excel.

**Agent dispatches:**
- `nexus:level-3:api-routes-builder` — XLSX export endpoint.
- `nexus:level-3:services-builder` — Meesho XLSX serialiser.
- `nexus:level-3:nextjs-developer-agent` — preview, price calc, dashboard components.
- `nexus:level-3:e2e-test-builder` — one Playwright happy-path test recording the full journey.

**Success criteria (end of day):**
- [ ] XLSX downloads and opens cleanly in Excel; matches Meesho's required headers (verified against `mesell_MEESHO_FORM_RND.md`).
- [ ] Price calculator math checks out for 3 sample rows.
- [ ] Tracking dashboard reflects state changes in real time after edits.
- [ ] Playwright happy-path test passes locally.

**Risks for this day:**
- Meesho XLSX format mismatch breaks import on their side (mitigation: cross-check against the R&D file; if uncertain, use Meesho's downloadable template as source of truth).
- Preview component diverges from real Meesho rendering (mitigation: it's a preview, not a guarantee — label it "approximate preview").
- Founder fatigue (Day 6 of 7) (mitigation: agents do 90% today; founder reviews + integrates only).

**What to do if stuck:** If the Playwright test fights Angular hydration, ship a manual checklist for the demo instead and add automated E2E in Week 2.

**Hand-off to next day:** All V1 features functional in `dev`; one passing E2E test; XLSX validated against Meesho format.

---

### DAY 7 — TUESDAY June 10

**Goal:** Polish, deploy to `staging`, V1 demoable on `staging.meesell.in`.

**Critical path:**
1. Landing page at `meesell.in` (single page: hero, 3 feature blocks, "Join waitlist" form → stores email in DB).
2. Privacy Policy + Terms of Service pages (use a standard template, customise for Mesell + India jurisdiction).
3. Bug-fix pass from Day 6 E2E run: top 10 issues only — defer the rest to Week 2 backlog.
4. Promote `dev` image tags to `staging` namespace; verify config (separate DB, separate GCS bucket `meesell-staging-uploads`).
5. Switch cert-manager to Let's Encrypt prod issuer; obtain real certs for `meesell.in`, `staging.meesell.in`, `api.staging.meesell.in`.
6. Deploy Prometheus + Grafana via kube-prometheus-stack Helm chart in `monitoring` namespace; one dashboard (API p95, error rate, DB connections, pod restarts).
7. Internal testing checklist (Section 6 below); founder demos to one friend / seller (in person or video call) to validate flow.

**Agent dispatches:**
- `nexus:level-3:nextjs-developer-agent` — landing page, legal pages.
- `nexus:level-3:technical-writer` — Privacy + ToS content (India-specific clauses).
- `nexus:level-3:infra-builder` — staging promotion + monitoring stack.
- `nexus:level-3:e2e-test-builder` — re-run happy path against `staging.meesell.in`.

**Success criteria (end of day):**
- [ ] `https://meesell.in` serves landing page with valid HTTPS.
- [ ] `https://staging.meesell.in` serves the app with valid HTTPS.
- [ ] Privacy + ToS pages linked from landing footer.
- [ ] Grafana dashboard reachable (internal only, basic auth or VPN).
- [ ] One external person completes the demo flow with founder observing.
- [ ] All Definition-of-Done items (Section 6) checked.

**Risks for this day:**
- Let's Encrypt prod rate limits if Day 4 staging was misconfigured (mitigation: verify staging cert worked before flipping to prod; max 5 issuances/week per domain).
- Last-minute bug list explodes past 10 (mitigation: triage ruthlessly — anything not blocking demo goes to Week 2).
- Demo friend cancels (mitigation: record a self-narrated Loom as fallback proof of demo-ability).

**What to do if stuck:** If staging deploy breaks at the cert step, demo from `dev` with self-signed cert + browser warning bypass. Shipping the flow matters more than shipping the cert today.

**Hand-off to next day (Week 2):** V1 is live on `staging.meesell.in`; landing page captures waitlist; founder has a demo recording; Week 2 backlog is groomed from Day 6-7 deferred issues.

---

## Section 3 — Agent Dispatch Strategy

| Domain | Primary agent | Used on days |
|---|---|---|
| VM, K3s, ingress, cert-manager, monitoring | `nexus:level-3:infra-builder` | 1, 4, 7 |
| PostgreSQL schema, migrations, seeds | `nexus:level-3:database-builder` | 1, 2 |
| FastAPI routes (auth, catalogs, products, categories, images, export) | `nexus:level-3:api-routes-builder` | 2, 3, 6 |
| Service layer (MSG91, JWT, Gemini, GCS, XLSX builder) | `nexus:level-3:services-builder` | 2, 3, 6 |
| Gemini prompts (category suggest, autofill) | `nexus:level-3:prompt-engineer` | 3, 5 |
| Celery tasks, rembg, Pillow image pipeline | `nexus:level-3:python-developer-agent` | 3 |
| Angular components (auth, dashboard, catalog flow, preview, price, landing) | `nexus:level-3:nextjs-developer-agent` (adapted for Angular) | 4, 5, 6, 7 |
| Unit tests | `nexus:level-3:unit-test-builder` | 2, 3, 5 |
| E2E (Playwright happy path) | `nexus:level-3:e2e-test-builder` | 6, 7 |
| Privacy, ToS, internal docs | `nexus:level-3:technical-writer` | 7 |

**Adaptation note:** `nextjs-developer-agent` is the closest fit for frontend work; every dispatch prompt MUST start with "Angular 18 standalone components, not Next.js" to prevent React drift. If output drifts twice in a row, escalate to founder-written scaffolds.

---

## Section 4 — Daily Standup Template

Run this with Claude at the start of each day (5-10 min).

```
What did I/we ship yesterday:
-
-

What's blocking right now:
-

What's the focus today (max 3 items):
- 1.
- 2.
- 3.

How am I feeling about the week pace (1-10, and why):
-

What I will NOT do today (to protect the critical path):
-
```

Log answers in `docs/04-documents/` as `STANDUP_YYYY-MM-DD.md` so trends are visible by Day 5.

---

## Section 5 — Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| VM provisioning fails (quota / region) | Low | High | Pre-warm: request quota Day 0; fallback to Cloud Run for API + Cloud SQL for DB |
| MSG91 KYC delays past Day 4 | Medium | Medium | Ship dev-mode OTP path Day 2; switch to live SMS when approved |
| Gemini API rate limits or cost spike | Medium | Medium | Dual-key rotation; Vertex free credit as second pool; cache responses where idempotent |
| Founder fatigue / burnout (solo + 7 days) | High | High | Agents own 80% of code; founder = reviewer + integrator; one half-day off planned for Day 6 evening |
| Angular fluency gap vs. Next.js agents | Medium | Medium | Founder writes first 2 components as patterns; explicit "Angular 18, not React" preamble in every dispatch |
| Domain DNS propagation delay | Low | Low | Buy + configure Day 1 morning; use IP-based access as fallback |
| K3s upgrade / cert-manager mismatch | Low | Medium | Pin versions; staging issuer before prod issuer |
| Meesho XLSX format drift | Medium | High | Cross-check `mesell_MEESHO_FORM_RND.md`; download Meesho's own template as ground truth Day 6 |
| Schema variance across 3,772 categories | Medium | Medium | Generic-text fallback in renderer; restrict V1 to top 50 categories if needed |
| GCS CORS misconfig blocks browser upload | Low | Medium | Configure + curl-test Day 1; do not defer |
| Razorpay KYC delay (V1.5 only) | Medium | Low | Apply Day 1 anyway so it's ready before V1.5 |

---

## Section 6 — Definition of Done (End of Week)

- [ ] `meesell-dev` VM live, K3s healthy, `dev` + `staging` + `prod` namespaces created.
- [ ] Backend deployed to `dev` and `staging` (separate DBs, separate GCS buckets).
- [ ] Frontend deployed to `dev` and `staging`.
- [ ] Landing page live at `https://meesell.in` with waitlist capture.
- [ ] Privacy Policy and Terms of Service pages live.
- [ ] Phone OTP signup + login works end-to-end with live MSG91 (or dev-mode if KYC pending — document which).
- [ ] Smart Category Picker returns 3 relevant suggestions from 3,772 for 5 sample descriptions.
- [ ] Dynamic catalog form renders for any of the top 50 categories (V1 floor); generic-text fallback for the rest.
- [ ] AI Auto-fill produces a usable result on at least 8/10 sampled products.
- [ ] Image pre-check returns CMYK / watermark / white-BG verdict with reason text.
- [ ] Live Product Preview renders with image + key fields.
- [ ] Price Calculator math is correct on 3 sample rows.
- [ ] Tracking Dashboard lists all of a user's catalogs with status.
- [ ] XLSX Export produces a file that opens in Excel and matches Meesho headers.
- [ ] HTTPS works via Let's Encrypt prod certs on `meesell.in` + `staging.meesell.in` + `api.staging.meesell.in`.
- [ ] Grafana dashboard shows API p95, error rate, DB connections, pod restarts.
- [ ] Founder has demoed the flow to at least one external person.
- [ ] Week 2 backlog file exists at `docs/04-documents/WEEK_2_BACKLOG.md` with deferred items.

---

## Section 7 — Week 2 Preview (Direction Only)

- Invite 10-20 sellers from the validated pain-points list; collect structured feedback after each.
- Razorpay subscription integration (V1.5): plans, webhooks, paywall on export.
- Fix the top issues surfaced by beta sellers in Days 8-10.
- LTD launch prep: pricing page, FAQ, refund policy.
- Initial marketing assets: 90-second YouTube demo, landing page polish, 3 SEO posts.
- Promote `staging` → `prod`, switch DNS for `app.meesell.in`.

Week 2 is explicitly out of scope of this document — its only purpose here is to make sure Week 1 deferrals land somewhere visible.
