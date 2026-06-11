# Legal Docs — Placeholders & Outstanding Items Tracker

**Owner:** `meesell-legal-writer`
**Last updated:** 2026-06-05 (after Turn 6 — 9 artifacts live, all V1 docs drafted)
**Purpose:** Single source of truth for every unfilled placeholder, every `[LAWYER REVIEW]` marker, and every outstanding founder decision across the live drafts under `docs/legal/`. Updated whenever any artifact in this folder is touched.

> **Why this file exists:** Stellaxis has not yet been legally registered as a business entity. Drafts ship with placeholders rather than guessed values so no Razorpay name-match conflict, GST-registration mismatch, or contract-of-record inconsistency is baked in. Once incorporation completes, every row in §2 collapses to a real value in a single search-and-replace pass per document.

---

## 1. Placeholder taxonomy

There are **5 distinct placeholder types** across the legal pack:

| Tag | Closes when | Resolver | Drafts affected |
|---|---|---|---|
| `[ENTITY SUFFIX]` | Founder picks Sole Prop / OPC / LLP / Pvt Ltd AND Stellaxis is registered (§15.1 + ROC filing complete) | Founder + CA / Vakilsearch / local counsel | All 9 drafts |
| `[FOUNDER: Name on PAN]` | Stellaxis PAN is issued — for Sole Prop = founder's personal PAN; for OPC/LLP/Pvt Ltd = company / LLP / OPC PAN with founder named as proprietor / partner / director | Income Tax Department | Privacy, ToS, Refund, Cookie, DPA signature block, KYC merchant form, In-product strings footer |
| `[FOUNDER: Stellaxis registered business address]` | Registered office address is filed with ROC (or, for Sole Prop, declared on PAN/GST/Shop & Establishment) | Founder + ROC / state registrar | All 9 drafts |
| `[FOUNDER: City of Stellaxis registered office]` | Same as registered address — sets the **exclusive jurisdiction** city for ToS §16.2 and DPA §13.1 | Founder | Privacy §15, ToS §16.2, Refund §10, DPA §13.1 |
| `[FOUNDER: State of Stellaxis registered office]` + `[FOUNDER: District]` | GST registration portal entries | Founder | GST checklist §6, Invoice §2 |
| `[FOUNDER: Stellaxis GSTIN]` | Issued 7-10 working days after GST application | gst.gov.in | Invoice template (all sections), In-product strings §3.3 + §7.3 + §11.2 |
| `[FOUNDER: publish date]` | Set on the day each customer-facing document goes live on the website | Founder | Privacy, ToS, Refund, Cookie |
| `[FOUNDER: signature date]` (DPA only) | Set when DPA is signed with each enterprise customer | Founder | DPA §14 |
| `[CUSTOMER: ...]` (DPA only — 6 fields) | Per-customer at DPA signing | Customer | DPA §1, §14 |
| `[CA VERIFY]` | CA confirms before first GST invoice issued | CA | GST checklist §5 (SAC code), Invoice §7 (numbering format) |

**None of the placeholders block document drafting.** They block **publishing**. Drafts can go through Indian lawyer redline with placeholders in place; the lawyer's edits attach to the surrounding clauses, not the placeholder values.

---

## 2. Placeholder location map (audit-grade)

This table is regenerated whenever any `docs/legal/*.md` is edited. Tag occurrences are absolute counts per file as of the last update at the top.

### 2.1 `[ENTITY SUFFIX]`

| File | Lines / locations | What goes here |
|---|---|---|
| `privacy-policy.md` | §1 opener (line ~23), header (line 3) | Empty for Sole Prop; "Private Limited", "(OPC) Private Limited", "LLP" otherwise |
| `terms-of-service.md` | §1 opener (line ~23), §15 notices block (line ~352), header (line 3), document-control row | Same as above |
| `refund-policy.md` | Header (line 3) | Same as above |
| `cookie-policy.md` | §1 opener (line 3), document-control row | Same as above |

### 2.2 `[FOUNDER: Name on PAN]`

| File | Section | Drafted line |
|---|---|---|
| `privacy-policy.md` | §12 Grievance Officer; §16 Contact | "Name: ..." |
| `terms-of-service.md` | §18 Contact | "Grievance Officer: ..." |
| `refund-policy.md` | §6 Refund disputes | "Grievance Officer: ..." |
| `cookie-policy.md` | §7 Contact | "Grievance Officer: ..." |

### 2.3 `[FOUNDER: Stellaxis registered business address]`

| File | Section |
|---|---|
| `privacy-policy.md` | §12 Grievance Officer; §16 Contact |
| `terms-of-service.md` | §15 Notices; §18 Contact |
| `refund-policy.md` | §6 |
| `cookie-policy.md` | §7 |

### 2.4 `[FOUNDER: City of Stellaxis registered office]`

| File | Section | Clause it drives |
|---|---|---|
| `privacy-policy.md` | §15 Disputes and governing law | Exclusive jurisdiction |
| `terms-of-service.md` | §16.2 Exclusive jurisdiction | Same — must match privacy + refund |
| `refund-policy.md` | §10 | Same — must match privacy + ToS |

### 2.5 `[FOUNDER: publish date]`

Every header (Effective date + Last updated) on every customer-facing draft (Privacy, ToS, Refund, Cookie). Set in a single pass on the morning of go-live.

### 2.6 `[FOUNDER: Stellaxis GSTIN]`

| File | Where |
|---|---|
| `invoice-template.md` | Every section that references the supplier GSTIN line on the invoice (§1, §4 example, §8 Razorpay config) |
| `in-product-strings.md` | §3.3 (GSTIN collection notice — references seller GSTIN, not Stellaxis), §7.3 (pricing-page footer), §11.2 (email footer) |
| `razorpay-kyc-checklist.md` | §4 merchant form |

### 2.7 `[FOUNDER: State of Stellaxis registered office]` + `[FOUNDER: District]`

| File | Where |
|---|---|
| `gst-registration-checklist.md` | §6 portal application table |
| `invoice-template.md` | §2 place-of-supply rules |

### 2.8 `[CA VERIFY]` markers

| File | Section | Topic |
|---|---|---|
| `gst-registration-checklist.md` | §5 | SAC code 998314 confirmation |
| `invoice-template.md` | §2 | Place-of-supply for B2C |
| `invoice-template.md` | §7 | Invoice number length cap (16 chars) |

### 2.9 `[CUSTOMER: ...]` markers (DPA only)

DPA template carries 6 customer placeholders (legal name, registered office address, signatory name, signatory title, signature date, address for notices). Filled per-customer at signing — none of these block pre-staging the template.

---

## 3. [LAWYER REVIEW] markers — what an Indian lawyer must redline

The 5 customer-facing or DPA drafts carry **34 `[LAWYER REVIEW]` markers** total (KYC + GST + Invoice + In-product strings are operational; no lawyer review required for them, though CA confirms 3 items per §2.8). The list below is the lawyer's worklist.

### 3.1 `docs/legal/privacy-policy.md` — 8 markers

| # | Section | Topic | Why a lawyer must confirm |
|---|---|---|---|
| 1 | §3.3 | "We do not collect card / UPI / bank account" | Confirm this matches Razorpay's actual data flow contractually — at no point does any PCI-DSS card-data shred touch our servers |
| 2 | §3.4 | SPDI scope | Confirm phone numbers fall outside the SPDI definition in the 2011 Rules, despite being personal data under DPDP |
| 3 | §6 | Cross-border to Gemini | Confirm DPDP §16 disclosure language is sufficient absent the negative-list notification |
| 4 | §7 | "Not stored by Google outside India after processing" | Confirm Google Gemini API Terms support this claim |
| 5 | §9 | TLS / token security claims as "reasonable security practices" | Confirm IT Act §43A defensibility of the specific measures |
| 6 | §11 | "72 hours" breach notification | Confirm against current DPDP Rules 2025 final text |
| 7 | §13 | Strictly-necessary cookie classification | Confirm no consent banner needed in V1 |
| 8 | §15 | Governing law + jurisdiction | Standard, but verify wording for Stellaxis's chosen city |

### 3.2 `docs/legal/refund-policy.md` — 2 markers

| # | Section | Topic |
|---|---|---|
| 1 | §5 | CGST Rule 53 GST reversal mechanics on refund |
| 2 | §10 | Governing law + jurisdiction |

### 3.3 `docs/legal/terms-of-service.md` — 17 markers

| # | Section | Topic |
|---|---|---|
| 1 | §1 | DPA/Enterprise carve-out from prior-agreement supersession |
| 2 | §2.1 | "Not subject to Indian sanctions" representation |
| 3 | §3.3 | Independence-from-Meesho disclaimer language |
| 4 | §5.4 | GST invoice mechanics — CGST Rule 46 compliance |
| 5 | §6.2 | Seller statutory accuracy + liability allocation |
| 6 | §7.2 | Google Gemini API customer-of-record clause |
| 7 | §7.3 | MeeSell Catalog Dataset proprietary claim (India has no statutory database right) |
| 8 | §7.5 | IT Act §79 takedown procedure compliance |
| 9 | §9 | Third-party data — controller/processor allocation |
| 10 | §10 | Warranty disclaimer |
| 11 | §11 | Limitation of liability cap + exclusions |
| 12 | §12 | Indemnity scope |
| 13 | §16.2 | Exclusive jurisdiction |
| 14 | §16.3 | Good-faith resolution as a litigation precondition |
| 15 | §16.4 | **Class-action waiver — flagged high-risk** (enforceability under Indian law is contested) |
| 16 | §17.7 | English-version-controls clause |

### 3.4 `docs/legal/cookie-policy.md` — 1 marker

| # | Section | Topic |
|---|---|---|
| 1 | §4 | Strictly-necessary classification (no consent banner in V1) |

### 3.5 `docs/legal/dpa-template.md` — 6 markers

| # | Section | Topic |
|---|---|---|
| 1 | §5.1 | Processing-on-instructions exception when Applicable Law forces it |
| 2 | §5.7 | 48-hour customer breach notification (tighter than 72-hour regulator window) |
| 3 | §8 | DPDP §16 cross-border restriction mechanism |
| 4 | §9.2 | Audit rights — scope and frequency caps for small SaaS |
| 5 | §11.2 | Liability cap negotiable per enterprise customer |
| 6 | §11.5 | Indemnity scope |

---

## 4. Outstanding founder decisions blocking publishing

Cross-reference: `docs/LEGAL_ARCHITECTURE.md` §15.

| # | Decision | Status | Blocks |
|---|---|---|---|
| 15.1 | Entity (Sole Prop / OPC / LLP / Pvt Ltd) | **RATIFIED** — OPC immediately (founder ruling 2026-06-11) | Blocks: `[ENTITY SUFFIX]` resolution — NOW RESOLVED as "(OPC) Private Limited". Razorpay KYC + GST checklists single-pathed to OPC. |
| 15.2 | Incorporator (Vakilsearch / IndiaFilings / local CA) | **DEFERRED** | Incorporation paperwork only |

All other §15 decisions (14 of 15) are **RATIFIED** as of 2026-06-11. Only §15.2 (incorporator) remains DEFERRED.

---

## 5. Resolution checklist (Founder runbook)

When Stellaxis incorporates, work through this list once. Once done, the legal pack ships.

- [ ] **5.1** Decide entity (§15.1 — Sole Prop recommended for V1)
- [ ] **5.2** Apply for PAN in entity name "Stellaxis" + suffix (CA / Vakilsearch — ₹0 govt fee, ₹500-1,500 service)
- [ ] **5.3** Obtain Shop & Establishment certificate (₹500-2,000, state-dependent) — Sole Prop only
- [ ] **5.4** Open Current Account in "Stellaxis" + suffix (HDFC / ICICI / Axis / Kotak)
- [ ] **5.5** Apply for GSTIN at gst.gov.in (₹0 govt; CA ₹2,500-5,000); 7-10 working days; SAC 998314 or 998361
- [ ] **5.6** Register domain WHOIS for meesell.in in Stellaxis's legal name (or enable WHOIS privacy)
- [ ] **5.7** Set up `grievance@meesell.in` mailbox routed to founder
- [ ] **5.8** Set up `support@meesell.in` mailbox routed to founder (V1) / support inbox (V1.5)
- [ ] **5.9** Send the 4 drafts to Indian lawyer for redline pass (₹5,000-15,000 — LACI §3.4 estimate)
- [ ] **5.10** Apply lawyer redlines + replace 5 placeholder tags via search-and-replace
- [ ] **5.11** Set `[FOUNDER: publish date]` to launch morning
- [ ] **5.12** Publish at:
  - `https://www.meesell.in/legal/privacy-policy`
  - `https://www.meesell.in/legal/terms-of-service`
  - `https://www.meesell.in/legal/refund-policy`
  - `https://www.meesell.in/legal/cookie-policy`
- [ ] **5.13** Link footer of every page to the 4 published URLs
- [ ] **5.14** Wire consent checkbox on signup to live URLs
- [ ] **5.15** Begin Razorpay merchant onboarding (1-3 business days)
- [ ] **5.16** Once Razorpay live: switch razorpay-key-id + razorpay-key-secret in GCP Secret Manager from TEST to LIVE per `docs/INFRASTRUCTURE_ARCHITECTURE.md` §4

---

## 6. Cross-document consistency invariants

Once placeholders collapse, the following values **MUST** be identical across all 4 drafts. Any drift is a publishing bug.

| Value | Privacy | ToS | Refund | Cookie |
|---|---|---|---|---|
| Legal business name | Stellaxis + suffix | Stellaxis + suffix | Stellaxis + suffix | Stellaxis + suffix |
| Trade name | MeeSell | MeeSell | MeeSell | MeeSell |
| Domain | www.meesell.in | www.meesell.in | meesell.in (text in §1 — fix on publish to www.meesell.in) | www.meesell.in |
| Grievance Officer email | grievance@meesell.in | grievance@meesell.in | grievance@meesell.in | grievance@meesell.in |
| Grievance Officer SLA | 24-72h ack, 7d resolve | 24-72h ack, 7d resolve | 24-72h ack, 7d resolve | (refers to Privacy §12) |
| Jurisdiction city | `[FOUNDER: City]` | `[FOUNDER: City]` | `[FOUNDER: City]` | (not stated) |
| Founder name on PAN | `[FOUNDER: Name]` | `[FOUNDER: Name]` | `[FOUNDER: Name]` | `[FOUNDER: Name]` |
| Business address | `[FOUNDER: address]` | `[FOUNDER: address]` | `[FOUNDER: address]` | `[FOUNDER: address]` |
| Effective + Last-updated date | same date | same date | same date | same date |

**Known minor fix on publish:** privacy-policy.md §1 currently reads `https://meesell.in` (no `www.` subdomain). The header line and all other domain references are `www.meesell.in`. Search-and-replace at publish time to normalise.

---

## 7. V1 legal pack — all 9 artifacts shipped as DRAFT

| File | Status | [LAWYER REVIEW] count | Customer-facing? |
|---|---|---|---|
| `privacy-policy.md` | DRAFT v1 | 8 | Yes — publish on incorporation |
| `terms-of-service.md` | DRAFT v1 | 17 | Yes — publish on incorporation |
| `refund-policy.md` | DRAFT v1 (Variant B) | 2 | Yes — publish on incorporation |
| `cookie-policy.md` | DRAFT v1 | 1 | Yes — publish on incorporation |
| `dpa-template.md` | DRAFT TEMPLATE v1 | 6 | No — pre-staged; signed per enterprise customer |
| `razorpay-kyc-checklist.md` | DRAFT runbook v1 | 0 (operational) | No — founder runbook |
| `gst-registration-checklist.md` | DRAFT runbook v1 | 0 (1 CA verify) | No — founder runbook |
| `invoice-template.md` | DRAFT spec v1 | 0 (2 CA verify) | No — Razorpay config + manual fallback |
| `in-product-strings.md` | DRAFT spec v1 | 0 (legal-writer locked copy) | No — hand-off to FE specialist |

**No artifacts pending. V1 legal pack drafting is complete.** Next phase = Indian lawyer redline pass on the 5 customer-facing/DPA documents (34 lawyer-review markers), then placeholder collapse on incorporation, then publish.

---

## 8. Update protocol

This tracker is **owned by `meesell-legal-writer`** and updated:
- On every new draft (add the file's placeholders to §2; add its `[LAWYER REVIEW]` markers to §3)
- On every founder ruling (move §4 rows to the §5 checklist or strike them)
- On every architecture amendment that affects placeholders
- On every consistency-invariant change (§6)

A lint script (deferred) should be added to verify §2 placeholder counts match the actual file contents — for now, manual audit via `grep -nH "FOUNDER:\|ENTITY SUFFIX\|LAWYER REVIEW" docs/legal/*.md`.
