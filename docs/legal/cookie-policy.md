# Cookie Policy

**For:** **Stellaxis** `[ENTITY SUFFIX — fills in once §15.1 ruled]` operating the **MeeSell** service at `https://www.meesell.in`
**Effective date:** `[FOUNDER: publish date]`
**Last updated:** `[FOUNDER: publish date]`
**Version:** v1.0
**Status:** DRAFT — founder + Indian lawyer review required before publishing
**Drafted by:** `meesell-legal-writer` per `docs/LEGAL_ARCHITECTURE.md` §13, §14

> **Founder action required before publishing:**
> 1. Resolve `[ENTITY SUFFIX]` per §15.1
> 2. Confirm publish date
> 3. Indian lawyer review pass (short doc — typically <30 minutes)
> 4. Linked from the footer of every page

---

## 1. Why this policy exists

This Cookie Policy explains the small set of **cookies** and **browser-storage items** that the MeeSell service places on your device when you use `https://www.meesell.in` or the MeeSell application.

It is a companion to our [Privacy Policy §13](./privacy-policy.md), which already gives you the headline answer. This document expands on it.

If you only want the headline: **we use functional cookies only.** We do not use third-party tracking cookies, advertising cookies, social-media cookies, or analytics cookies in version 1.0.

---

## 2. What a cookie is

A **cookie** is a small text file that a website asks your browser to store, and that the browser sends back to that website on subsequent requests. Cookies let a site recognise you between requests — for example, to keep you signed in.

A **browser-storage item** is similar to a cookie but lives in your browser's local storage, session storage, or service-worker cache. We use service-worker cache for offline-friendly delivery.

---

## 3. Cookies and storage items we use

The complete list:

| Item | Type | Purpose | Storage | Lifetime | Set by |
|---|---|---|---|---|---|
| `refresh_token` | Strictly-necessary functional cookie | Authentication. Lets us refresh your session token so you do not have to log in repeatedly during a working session. Marked **HttpOnly** (JavaScript cannot read it), **Secure** (sent over HTTPS only), **SameSite=Strict** (not sent on cross-site navigation, eliminates CSRF on the refresh endpoint), scoped to `/api/v1/auth` on `meesell.in`. | Browser cookie | Up to **7 days**; deleted immediately on logout or session revocation | Stellaxis server (MeeSell backend) |
| Service-worker cache | Strictly-necessary functional storage | Offline-friendly delivery of the application shell (HTML, CSS, JavaScript). Does not store your personal data — only the static application files. | Browser cache (service worker) | Cleared when you clear your browser cache, or when a new application version replaces it | MeeSell client (PWA service worker) |

That is the complete list. We **do not use**:
- Analytics cookies (Google Analytics, Mixpanel, etc.)
- Advertising cookies (Google Ads, Facebook Pixel, etc.)
- Social-media cookies (Twitter, LinkedIn, etc.)
- Third-party tracking cookies of any kind
- Session-replay or heat-mapping cookies (Hotjar, FullStory, etc.)

---

## 4. Consent

The cookies and storage items in Section 3 are **strictly necessary** for the Service to function. Without them, you cannot stay signed in and the application shell cannot load offline. Under DPDP Act §6 and the corresponding EU ePrivacy interpretation **[LAWYER REVIEW]**, strictly-necessary cookies do not require a separate opt-in consent banner; your acceptance of the [Privacy Policy](./privacy-policy.md) and [Terms of Service](./terms-of-service.md) at signup covers them.

We do not currently display a cookie banner because no non-essential cookies are present.

If we add any non-essential cookies in a future version of the Service, we will:
- Update this policy and the [Privacy Policy](./privacy-policy.md)
- Refresh the effective date
- Display a cookie banner that asks you for explicit, opt-in consent before any non-essential cookie is set
- Let you withdraw consent as easily as you gave it

---

## 5. Controlling cookies through your browser

You can clear or block cookies at any time via your browser's settings:

| Browser | How to manage cookies |
|---|---|
| Chrome | Settings → Privacy and security → Cookies and other site data |
| Firefox | Settings → Privacy & Security → Cookies and Site Data |
| Safari (macOS / iOS) | Settings → Safari → Privacy & Security |
| Edge | Settings → Cookies and site permissions → Manage cookies |

**Note:** if you block or clear the `refresh_token` cookie, you will be signed out of the Service. You can sign back in via OTP at any time.

---

## 6. Changes to this policy

We will update this policy if the set of cookies we use changes. We will:
- Update the **Effective date** at the top
- Notify you via email (if you have a registered email) at least **30 days before** any change that introduces a new non-essential cookie
- Show a cookie banner if non-essential cookies are added

---

## 7. Contact

**Grievance Officer:** `[FOUNDER: Name on PAN]`
**Email:** `grievance@meesell.in`
**Postal address:** `[FOUNDER: Stellaxis registered business address]`

For general questions: `support@meesell.in`

---

## Document control

| Field | Value |
|---|---|
| Document | MeeSell Cookie Policy v1.0 |
| Operator | Stellaxis `[ENTITY SUFFIX]` |
| Status | DRAFT — founder + lawyer review required |
| Drafted by | `meesell-legal-writer` 2026-06-05 |
| Source citations | `docs/LEGAL_ARCHITECTURE.md` §13, §14; `docs/FRONTEND_ARCHITECTURE.md` §1.F (token storage model); `docs/BACKEND_ARCHITECTURE.md` §4.B (refresh cookie scope); `docs/LEGAL_AND_COMPLIANCE_INFO.md` §6 |
| Lawyer review markers | 1 — search for `[LAWYER REVIEW]` (§4 strictly-necessary classification) |
| Founder placeholders | search for `[FOUNDER:` or `[ENTITY SUFFIX]` |
| Pairs with | `privacy-policy.md` §13 (headline), `terms-of-service.md` §9 (data protection) |
