"""getTransferPrice FIELD SWEEP — find the body that returns a NON-empty breakdown.

Confirmed (round 13): the endpoint accepts `price`+`sub_sub_category_id`+`supplier_id`
and returns HTTP 200, but the body is `{}`. This sweep logs in ONCE, then fires a
curated set of bodies (all 200-or-400 captured in full) to find which field(s)
unlock the actual commission/tax/shipping/transfer breakdown.

READ-ONLY compute calls; no submit; paced. Stop on 401/403/429.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

ROOT = Path("/Users/mugunthansrinivasan/Project/mesell")
CREDS = ROOT / ".meesho_creds.env"
LOG_DIR = ROOT / "logs" / "scraper"
LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"
TP_URL = "https://supplier.meesho.com/api/cataloging/singleCatalogUpload/getTransferPrice"

SSCAT = 10949
VAR = 167
STOP = {401, 403, 429}


def creds():
    load_dotenv(CREDS, override=True)
    return os.environ["MEESHO_USERNAME"].strip(), os.environ["MEESHO_PASSWORD"].strip()


def headers(sid, ident):
    return {
        "identifier": str(ident), "client-type": "d-web",
        "client-package-version": "1.0.1", "supplier-id": str(sid),
        "content-type": "application/json;charset=UTF-8",
        "accept": "application/json, text/plain, */*",
    }


def bodies(sid, ident, price=100, mrp=120, wdrp=89, inv=10, wt=20):
    """Curated variants — vary the EXTRA fields around the confirmed-good core."""
    core = {"price": price, "supplier_id": sid, "sub_sub_category_id": SSCAT}
    return [
        # 0 confirmed-good core (returns 200 {} baseline)
        dict(core),
        # 1 + mrp + wdrp
        {**core, "mrp": mrp, "wrong_defective_price": wdrp},
        # 2 + weight (shipping needs weight)
        {**core, "net_weight": wt, "weight": wt, "product_weight_in_gms": wt},
        # 3 + inventory + variation
        {**core, "inventory": inv, "variation_id": VAR},
        # 4 + price_type / scale
        {**core, "price_type": "MEESHO", "scale_id": 1},
        # 5 + gst fields
        {**core, "gst": 18, "gst_percentage": 18, "hsn_code": "85444299"},
        # 6 EVERYTHING flat
        {**core, "mrp": mrp, "product_mrp": mrp, "wrong_defective_price": wdrp,
         "only_wrong_return_price": wdrp, "inventory": inv, "variation_id": VAR,
         "net_weight": wt, "weight": wt, "product_weight_in_gms": wt,
         "identifier": ident, "scale_id": 1, "price_type": "MEESHO",
         "gst": 18, "gst_percentage": 18},
        # 7 listing_price / selling_price aliases alongside price
        {**core, "listing_price": price, "selling_price": price,
         "meesho_price": price, "net_weight": wt},
        # 8 prices[] / price_list shapes
        {"supplier_id": sid, "sub_sub_category_id": SSCAT, "identifier": ident,
         "prices": [{"price": price, "variation_id": VAR, "net_weight": wt}]},
        # 9 weight in kg (maybe expects kg)
        {**core, "weight": 0.02, "net_weight": 20},
        # 10 + category_id guesses are unknown; try is_wrong_defective flag + return price
        {**core, "wrong_defective_price": wdrp, "net_weight": wt,
         "is_wrong_defective_enabled": True},
    ]


async def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    user, pwd = creds()
    acct = {"sid": None, "ident": None}
    out = []

    async with async_playwright() as pw:
        b = await pw.webkit.launch(headless=True)
        ctx = await b.new_context(locale="en-IN", timezone_id="Asia/Kolkata",
                                  viewport={"width": 1440, "height": 1000})

        async def on_resp(r):
            if "prefetch-supply-data" in r.url or "fetch-registration-status" in r.url:
                try:
                    body = await r.json()
                except Exception:
                    return
                stack = [body]
                while stack:
                    c = stack.pop()
                    if isinstance(c, dict):
                        for k, v in c.items():
                            kl = str(k).lower()
                            if kl == "supplier_id" and isinstance(v, (int, str)):
                                acct["sid"] = acct["sid"] or v
                            if kl == "supplier_identifier_to_id_mapping" and isinstance(v, dict):
                                for ident, sid in v.items():
                                    acct["ident"] = acct["ident"] or ident
                                    acct["sid"] = acct["sid"] or sid
                            if isinstance(v, (dict, list)):
                                stack.append(v)
                    elif isinstance(c, list):
                        stack.extend(c)
        ctx.on("response", lambda r: asyncio.create_task(on_resp(r)))

        page = await ctx.new_page()
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2.5)
        await page.locator("input[type='text']").first.fill(user)
        await asyncio.sleep(0.8)
        await page.locator("input[type='password']").first.fill(pwd)
        await asyncio.sleep(0.8)
        await page.get_by_role("button", name=re.compile(r"log\s*in|sign\s*in", re.I)).first.click()
        await asyncio.sleep(6)
        for _ in range(12):
            if "login" not in page.url.lower():
                break
            await asyncio.sleep(2)
        print("after login url:", page.url, flush=True)
        await asyncio.sleep(3)

        sid = acct["sid"] or 4359160
        ident = acct["ident"] or "oinpw"
        print("account sid/ident:", sid, ident, flush=True)

        for i, body in enumerate(bodies(sid, ident)):
            try:
                resp = await ctx.request.post(TP_URL, headers=headers(sid, ident),
                                              data=body, timeout=30000)
                st = resp.status
                if st in STOP:
                    print(f"HARD-STOP {st} on attempt {i}", flush=True)
                    out.append({"i": i, "body": body, "status": st, "resp": "STOP"})
                    break
                try:
                    rb = await resp.json()
                except Exception:
                    rb = {"_text": (await resp.text())[:500]}
                nonempty = bool(rb) and rb != {} and not (isinstance(rb, dict) and rb.get("data") is None and rb.get("errors"))
                out.append({"i": i, "body": body, "status": st, "resp": rb,
                            "nonempty": nonempty})
                tag = "*** NON-EMPTY ***" if (st == 200 and rb) else ""
                print(f"[{i}] {st} {tag} resp={json.dumps(rb, default=str)[:400]}", flush=True)
            except Exception as e:
                out.append({"i": i, "body": body, "error": str(e)})
                print(f"[{i}] ERROR {e}", flush=True)
            await asyncio.sleep(2.5)

        await b.close()

    p = LOG_DIR / f"tp_sweep_{ts}.json"
    p.write_text(json.dumps(out, indent=2, default=str))
    print("\nwrote", p, flush=True)
    winners = [o for o in out if o.get("status") == 200 and o.get("resp") and o["resp"] != {}]
    print("NON-EMPTY 200 winners:", len(winners), flush=True)
    for w in winners:
        print("  body keys:", sorted(w["body"].keys()))
        print("  resp:", json.dumps(w["resp"], indent=2, default=str)[:1500])


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
