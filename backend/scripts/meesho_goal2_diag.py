"""Goal-2 diagnostic — referral-fee + payments panel, READ-ONLY, gentle.

One authenticated session, navigate ONLY the two Goal-2 panels, log EVERY XHR
URL+status that fires on each (not just commission-matched), and dump the first
600 chars of rendered body text + page title. Purpose: prove WHY the rate-card
and settlement data do not appear — route-not-found vs e-sig gate vs empty data.
READ-ONLY. Hard-stop on OTP/401/403/429. 463 tolerated.
"""
from __future__ import annotations
import asyncio, json, os, re, sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import Page, Response, TimeoutError as PWTimeout, async_playwright

ROOT = Path("/Users/mugunthansrinivasan/Project/mesell")
CREDS = ROOT / ".meesho_creds.env"
LOGIN = "https://supplier.meesho.com/panel/v3/new/root/login"
OTP_RE = re.compile(r"\b(otp|one[-\s]?time\s?password|enter the code)\b", re.I)
STOP = {401, 403, 429}

xhrs: list[dict] = []
hard = {"stop": None}


async def on_resp(r: Response) -> None:
    u = r.url.split("?", 1)[0]
    if "supplier.meesho.com" not in u:
        return
    # skip the Akamai sensor beacon (random-path noise)
    if re.search(r"/[A-Za-z0-9]{6,}/[A-Za-z0-9]{6,}/[A-Za-z0-9]{6,}/k1/", u):
        return
    if "/api/" in u:
        xhrs.append({"url": u, "status": r.status})
    if r.status in STOP:
        hard["stop"] = f"HTTP {r.status} on {u}"


async def login(page: Page, user: str, pwd: str) -> None:
    await page.goto(LOGIN, wait_until="domcontentloaded", timeout=45000)
    await asyncio.sleep(2)
    await page.locator("input[type='text']").first.fill(user)
    await asyncio.sleep(1)
    await page.locator("input[type='password']").first.fill(pwd)
    await asyncio.sleep(1)
    await page.locator("button[type='submit']").first.click()
    await page.wait_for_url(lambda x: "login" not in x, timeout=45000)


async def probe_page(page: Page, label: str, url: str) -> dict:
    before = len(xhrs)
    out = {"label": label, "url": url, "title": None, "text_head": None, "xhrs": []}
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(8)
        out["title"] = await page.title()
        txt = await page.locator("body").inner_text(timeout=4000)
        if OTP_RE.search(txt):
            hard["stop"] = f"OTP on {label}"
        out["text_head"] = txt[:600]
        out["esig_wall"] = bool(re.search(r"add signature|e-?sign|accept.{0,20}agreement|complete.{0,20}agreement|sign.{0,15}agreement", txt, re.I))
    except PWTimeout:
        out["text_head"] = "[nav timeout]"
    out["xhrs"] = xhrs[before:]
    return out


async def run() -> dict:
    load_dotenv(CREDS)
    user = os.environ["MEESHO_USERNAME"].strip()
    pwd = os.environ["MEESHO_PASSWORD"].strip()
    res = {"pages": [], "hard_stop": None}
    async with async_playwright() as pw:
        b = await pw.webkit.launch(headless=True)
        ctx = await b.new_context(locale="en-IN", timezone_id="Asia/Kolkata",
                                  viewport={"width": 1440, "height": 900})
        ctx.set_default_timeout(20000)
        ctx.set_default_navigation_timeout(45000)
        ctx.on("response", lambda r: asyncio.create_task(on_resp(r)))
        try:
            page = await ctx.new_page()
            await login(page, user, pwd)
            await asyncio.sleep(5)
            ident = "kdwec"
            navs = [
                ("referral-fee", f"https://supplier.meesho.com/panel/v3/new/growth/{ident}/referral-fee"),
                ("payments", f"https://supplier.meesho.com/panel/v3/new/payments/{ident}/payments"),
            ]
            for label, url in navs:
                if hard["stop"]:
                    break
                res["pages"].append(await probe_page(page, label, url))
                await asyncio.sleep(6)  # pace
        finally:
            res["hard_stop"] = hard["stop"]
            await asyncio.sleep(1)
            await ctx.close()
            await b.close()
    return res


def main() -> int:
    r = asyncio.run(run())
    for pg in r["pages"]:
        print(f"\n===== {pg['label']} :: {pg['url']} =====")
        print("title:", pg.get("title"))
        print("esig_wall_text:", pg.get("esig_wall"))
        print("text_head:", repr(pg.get("text_head")))
        print(f"XHRs fired ({len(pg['xhrs'])}):")
        for x in pg["xhrs"]:
            print(f"  {x['status']}  {x['url']}")
    print("\nhard_stop:", r["hard_stop"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
