"""Discover the EXACT getTransferPrice request/response shape from the JS bundle.

Logs in (warm Akamai cookies), opens the create flow, then fetches every loaded
.js chunk via the authenticated context and greps for the getTransferPrice call
site + surrounding request-body field names + response field usage.
READ-ONLY; no mutations; no submit.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

PROJECT_ROOT = Path("/Users/mugunthansrinivasan/Project/mesell")
CREDS = PROJECT_ROOT / ".meesho_creds.env"
LOG_DIR = PROJECT_ROOT / "logs" / "scraper"
LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"


def creds():
    load_dotenv(CREDS, override=True)
    import os
    return os.environ["MEESHO_USERNAME"].strip(), os.environ["MEESHO_PASSWORD"].strip()


JS_URLS: set[str] = set()


async def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    user, pwd = creds()
    found = []
    async with async_playwright() as pw:
        b = await pw.webkit.launch(headless=True)
        ctx = await b.new_context(locale="en-IN", timezone_id="Asia/Kolkata",
                                  viewport={"width": 1440, "height": 1000})

        def on_req(r):
            u = r.url
            if u.endswith(".js") or ".js?" in u or "/static/js/" in u or "chunk" in u.lower():
                JS_URLS.add(u.split("?")[0] if False else u)
        ctx.on("request", on_req)

        page = await ctx.new_page()
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2.5)
        await page.locator("input[type='text']").first.fill(user)
        await asyncio.sleep(0.8)
        await page.locator("input[type='password']").first.fill(pwd)
        await asyncio.sleep(0.8)
        await page.get_by_role("button", name=re.compile(r"log\s*in|sign\s*in", re.I)).first.click()
        await asyncio.sleep(6)
        for _ in range(10):
            if "login" not in page.url.lower():
                break
            await asyncio.sleep(2)
        print("login ok?", page.url, flush=True)
        await asyncio.sleep(3)

        # navigate the create flow so its chunk loads
        try:
            await page.goto("https://supplier.meesho.com/panel/v3/new/cataloging/oinpw/"
                            "catalogs/single/select-category",
                            wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(5)
        except Exception as e:
            print("nav warn", e, flush=True)

        print("collected", len(JS_URLS), "js urls", flush=True)
        pat = re.compile(r"getTransferPrice")
        for u in list(JS_URLS):
            try:
                resp = await ctx.request.get(u, timeout=30000)
                if resp.status != 200:
                    continue
                txt = await resp.text()
            except Exception:
                continue
            if pat.search(txt):
                print("HIT in", u.split("?")[0], flush=True)
                for m in pat.finditer(txt):
                    s = max(0, m.start() - 1500)
                    e = min(len(txt), m.end() + 1500)
                    found.append({"url": u.split("?")[0], "excerpt": txt[s:e]})
        out = LOG_DIR / "transfer_price_js_grep.json"
        out.write_text(json.dumps(found, indent=2))
        print("wrote", out, "hits:", len(found), flush=True)
        await b.close()
    # print excerpts
    for f in found:
        print("\n===== ", f["url"], " =====")
        print(f["excerpt"])


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
