"""READ-ONLY verification: did anything get left behind on the meesell account?

Checks (no mutation):
  * getCatalogUploadPerformance (single/bulk/total upload counts)
  * the catalog/listing list (fetch-supplier-products) — is there a new live
    or draft catalog?
  * any draft/in-progress catalog count.

NO form interaction, NO submit, NO discard — pure read of current state.
"""
from __future__ import annotations
import asyncio, json, os, re, sys
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

ROOT = Path("/Users/mugunthansrinivasan/Project/mesell")
CREDS = ROOT / ".meesho_creds.env"
LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"


async def main():
    load_dotenv(CREDS, override=True)
    user = os.environ["MEESHO_USERNAME"].strip()
    pwd = os.environ["MEESHO_PASSWORD"].strip()
    out = {}
    async with async_playwright() as pw:
        b = await pw.webkit.launch(headless=True)
        ctx = await b.new_context(locale="en-IN", timezone_id="Asia/Kolkata",
                                  viewport={"width": 1440, "height": 900})
        ctx.set_default_timeout(20000)
        ctx.set_default_navigation_timeout(45000)
        page = await ctx.new_page()
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2)
        await page.locator("input[type='text']").first.fill(user)
        await asyncio.sleep(0.8)
        await page.locator("input[type='password']").first.fill(pwd)
        await asyncio.sleep(0.8)
        await page.get_by_role("button", name=re.compile(r"log\s*in|sign\s*in", re.I)).first.click()
        try:
            await page.wait_for_url(lambda u: "login" not in u, timeout=45000)
        except PWTimeout:
            print(json.dumps({"error": "login_no_redirect"}))
            await b.close()
            return
        await asyncio.sleep(5)
        ident = "oinpw"
        m = re.search(r"/(?:growth|cataloging)/([a-z0-9]{3,12})/", page.url)
        if m and m.group(1) not in ("new", "root"):
            ident = m.group(1)
        # 1) upload performance
        for url in (
            "https://supplier.meesho.com/api/cataloging/singleCatalogUpload/getCatalogUploadPerformance",
            "https://supplier.meesho.com/api/cataloging/getCatalogUploadPerformance",
        ):
            try:
                r = await ctx.request.get(url, timeout=12000)
                if r.status == 200:
                    out["upload_performance"] = await r.json()
                    out["upload_performance_url"] = url
                    break
                else:
                    out.setdefault("upload_perf_status", []).append(f"{r.status} {url}")
            except Exception as e:  # noqa: BLE001
                out.setdefault("upload_perf_err", []).append(str(e)[:120])
        # 2) catalog/product list (existing listings) — count + any with today's date
        for url in (
            "https://supplier.meesho.com/api/growth/activation/fetch-supplier-products",
            "https://supplier.meesho.com/api/cataloging/catalog-listing/fetch-catalogs",
        ):
            try:
                r = await ctx.request.get(url, timeout=12000)
                if r.status == 200:
                    body = await r.json()
                    # find total + item count
                    def deep(o, key):
                        if isinstance(o, dict):
                            for k, v in o.items():
                                if k.lower() == key:
                                    return v
                                res = deep(v, key)
                                if res is not None:
                                    return res
                        elif isinstance(o, list):
                            for it in o:
                                res = deep(it, key)
                                if res is not None:
                                    return res
                        return None
                    items = deep(body, "items")
                    out.setdefault("listings", {})[url.split("/")[-1]] = {
                        "total_entities": deep(body, "total_entities"),
                        "item_count": len(items) if isinstance(items, list) else None,
                        "top_keys": sorted(body.keys())[:20] if isinstance(body, dict) else "[list]",
                    }
                else:
                    out.setdefault("listing_status", []).append(f"{r.status} {url.split('/')[-1]}")
            except Exception as e:  # noqa: BLE001
                out.setdefault("listing_err", []).append(str(e)[:120])
        await b.close()
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
