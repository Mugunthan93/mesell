"""ROUND 11 FAST DIAGNOSTIC (read-only, no-submit): login → Extension Chords details
step → click the Size field + the first attribute field → dump the popup menu
outerHTML + a structured list of clickable option rows, so we can write a working
MUI option-selector. Then Discard. NEVER submits/go-live.

Reuses meesho_taxcard_probe's proven login/nav/category/image helpers.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.async_api import async_playwright  # noqa: E402

import meesho_taxcard_probe as P  # noqa: E402

OUT = P.LOG_DIR / "dropdown_diag.txt"


async def dump_open_menu(page, tag: str) -> None:
    """After a trigger is clicked, dump the open menu."""
    html = await page.evaluate(
        """() => {
            const m = document.querySelector(
                'ul[role=menu], .MuiMenu-list, .MuiPopover-paper, [role=listbox], '
                + '.MuiPaper-root');
            return m ? m.outerHTML.slice(0, 4000) : '(no menu element)';
        }""")
    rows = await page.evaluate(
        """() => {
            const vis = el => { const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0; };
            return Array.from(document.querySelectorAll(
                'li, [role=option], [role=menuitem], .MuiMenuItem-root, '
                + '.MuiTypography-root, [class*=option i]'))
                .filter(vis)
                .map(e => ({tag: e.tagName,
                            role: e.getAttribute('role') || '',
                            cls: (e.className || '').toString().slice(0, 45),
                            clickable: !!e.onclick || e.getAttribute('role') === 'option'
                                       || e.getAttribute('role') === 'menuitem'
                                       || (e.className || '').toString().includes('MenuItem'),
                            txt: (e.innerText || '').trim().slice(0, 28)}))
                .filter(o => o.txt && o.txt.length < 28)
                .slice(0, 25);
        }""")
    with OUT.open("a") as f:
        f.write(f"\n===== {tag} =====\n")
        f.write("ROWS:\n")
        for r in rows:
            f.write(f"  {r}\n")
        f.write("MENU outerHTML (4k):\n")
        f.write(html + "\n")
    print(f"[{tag}] {len(rows)} candidate rows; menu html len={len(html)}")
    for r in rows[:12]:
        print("   ", r)


async def main() -> int:
    OUT.write_text("ROUND 11 dropdown diagnostic\n")
    user, pwd = P.load_creds()
    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True)
        ctx = await browser.new_context(
            locale="en-IN", timezone_id="Asia/Kolkata",
            viewport={"width": 1440, "height": 1000})
        ctx.set_default_timeout(P.LOGIN_ACTION_TIMEOUT_MS)
        ctx.set_default_navigation_timeout(P.LOGIN_NAV_TIMEOUT_MS)
        ctx.on("response", lambda r: asyncio.create_task(P.on_response(r)))
        page = await ctx.new_page()
        P._mode["phase"] = "login"
        await P.perform_login(page, user, pwd)
        await asyncio.sleep(5.0)
        P.detect_identifier_from_url(page.url)
        print("account:", P.findings["account"])

        P._mode["phase"] = "nav"
        if not await P.goto_single_select_category(page):
            print("could not reach select-category"); return 1
        if not await P.select_one_category(page, "extension chords", r"extension\s*chords?"):
            print("could not select extension chords"); return 1
        if not await P.upload_placeholder_image(page):
            print("image upload failed"); await P.discard_catalog(page); return 1
        P._mode["phase"] = "advance"
        await P.click_safe_next(page)
        await asyncio.sleep(4.0)

        # First: dump the Size field's WRAPPER HTML so we see the real click target.
        wrap = await page.evaluate(
            """() => {
                const ps = Array.from(document.querySelectorAll('p, label, span'));
                const lbl = ps.find(e => (e.innerText||'').trim() === 'Size');
                if (!lbl) return '(no Size label)';
                // climb to a field-ish container
                let c = lbl;
                for (let i=0;i<5;i++){ if(c.parentElement) c=c.parentElement; }
                return c.outerHTML.slice(0, 3000);
            }""")
        with OUT.open("a") as f:
            f.write("\n===== SIZE FIELD WRAPPER HTML =====\n" + wrap + "\n")
        print("Size wrapper html len:", len(wrap))

        # Try several click targets for the Size field and report which opens a menu.
        for desc, js_click in [
            ("input-following-Size",
             "() => {const ps=[...document.querySelectorAll('p')];"
             "const l=ps.find(e=>(e.innerText||'').trim()==='Size');"
             "const inp=l&&l.parentElement&&l.parentElement.parentElement"
             "?l.parentElement.parentElement.querySelector('input'):null;"
             "if(inp){inp.click();return 'clicked input';}return 'no input';}"),
            ("muiselect-div",
             "() => {const d=document.querySelector('.MuiSelect-select');"
             "if(d){d.click();return 'clicked MuiSelect-select';}return 'no MuiSelect-select';}"),
        ]:
            try:
                r = await page.evaluate(js_click)
                await asyncio.sleep(1.6)
                print(f"[{desc}] js_click -> {r}")
                await dump_open_menu(page, f"SIZE_{desc}")
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.8)
            except Exception as exc:  # noqa: BLE001
                print(f"[{desc}] failed:", exc)

        # PLAYWRIGHT click (force) on the readonly Select input → dump the open menu.
        sel = page.locator("input[placeholder='Select'][readonly]")
        try:
            n = await sel.count()
            print("readonly placeholder=Select inputs:", n)
            if n:
                inp = sel.first
                await inp.scroll_into_view_if_needed(timeout=3000)
                await inp.click(timeout=3000, force=True)
                await asyncio.sleep(2.0)
                # Dump EVERYTHING that looks like an overlay/popover now.
                overlays = await page.evaluate(
                    """() => Array.from(document.querySelectorAll(
                        '.MuiPopover-root, .MuiModal-root, [role=presentation], '
                        + '.MuiMenu-root, .MuiPopper-root, [class*=Popover], [class*=Popper]'))
                        .map(e => ({cls:(e.className||'').toString().slice(0,60),
                                    role:e.getAttribute('role')||'',
                                    txt:(e.innerText||'').trim().slice(0,120)}))
                        .filter(o=>o.txt).slice(0,8)""")
                with OUT.open("a") as f:
                    f.write("\n===== OVERLAYS AFTER PW CLICK =====\n")
                    for o in overlays:
                        f.write(f"  {o}\n")
                print("overlays after PW click:", len(overlays))
                for o in overlays:
                    print("   OVERLAY:", o)
                await dump_open_menu(page, "PW_CLICK_SELECT")
                await page.keyboard.press("Escape")
        except Exception as exc:  # noqa: BLE001
            print("attr PW click failed:", exc)

        # VERIFY the new selectors: click trigger (force) → click an option in the
        # popover → click Apply → confirm the input value changed.
        print("\n=== SELECTOR VERIFICATION ===")
        triggers = page.locator("input[placeholder='Select'][readonly]")
        nt = await triggers.count()
        filled_ok = 0
        for i in range(min(nt, nt)):
            t = triggers.nth(i)
            try:
                if not await t.is_visible():
                    continue
                before = await t.input_value()
                await t.scroll_into_view_if_needed(timeout=2500)
                await t.click(timeout=2500, force=True)
                await asyncio.sleep(1.0)
                opt = page.locator(
                    ".MuiPopover-root li.MuiMenuItem-root:visible, "
                    ".MuiPopover-root [role='option']:visible, "
                    ".MuiPopover-root [role='menuitem']:visible, "
                    ".MuiMenu-root li:visible, "
                    ".MuiPopover-root .MuiList-root p.MuiTypography-root:visible, "
                    ".MuiPopover-root .MuiBox-root p.MuiTypography-body1:visible")
                on = await opt.count()
                if on == 0:
                    ph = await page.evaluate(
                        """() => {const m=document.querySelector('.MuiPopover-root, .MuiMenu-root');
                            return m ? m.outerHTML.slice(0,2500) : '(no popover)';}""")
                    with OUT.open("a") as f:
                        f.write(f"\n=== TRIGGER#{i} ZERO-OPTION POPOVER ===\n{ph}\n")
                    print(f"  trigger#{i} ZERO options — popover html dumped (len={len(ph)})")
                picked = None
                import re as _re
                for j in range(min(on, 25)):
                    o = opt.nth(j)
                    if not await o.is_visible():
                        continue
                    nm = (await o.inner_text(timeout=1000)).strip()
                    if (nm and len(nm) < 50 and not _re.search(
                            r"^(select|clear filter|apply|cancel|reset|all)$", nm, _re.I)):
                        await o.click(timeout=2000)
                        picked = nm
                        break
                await asyncio.sleep(0.5)
                ab = page.get_by_role("button", name=_re.compile(r"^\s*apply\s*$", _re.I))
                if await ab.count() and await ab.first.is_visible():
                    await ab.first.click(timeout=2000)
                    await asyncio.sleep(0.5)
                else:
                    await page.keyboard.press("Escape")
                after = await t.input_value()
                if after and after != before:
                    filled_ok += 1
                print(f"  trigger#{i}: options={on} picked={picked!r} "
                      f"value {before!r}->{after!r}")
            except Exception as exc:  # noqa: BLE001
                print(f"  trigger#{i} failed: {exc}")
        print(f"=== {filled_ok}/{nt} triggers filled OK ===")
        # Now explicitly select the SIZE field via the proven select_a_size().
        print("\n=== explicit select_a_size (Free Size) ===")
        sized = await P.select_a_size(page)
        print("select_a_size returned:", sized, "size=", P.findings["form_fill"].get("size"))
        await asyncio.sleep(2.5)

        # Fully complete the remaining mandatory text/number fields so the form is
        # 100% green — then look for any newly-enabled price step / control.
        print("\n=== complete remaining text/number fields ===")
        await P.fill_all_text_inputs(page)
        await P.fill_all_number_inputs(page, skip_price=True)
        await asyncio.sleep(2.0)
        # Re-run the dropdown filler for the 2 that were empty.
        nfilled = await P.fill_meesho_attribute_dropdowns(page)
        print("extra dropdowns filled:", nfilled)
        await asyncio.sleep(2.0)
        # Enumerate ALL buttons + any enabled/disabled state.
        btns = await page.evaluate(
            """() => Array.from(document.querySelectorAll('button')).map(b => ({
                txt:(b.innerText||'').trim().slice(0,30),
                disabled:b.disabled, vis:!!b.offsetParent}))
                .filter(b=>b.txt)""")
        print("BUTTONS:", btns)
        with OUT.open("a") as f:
            f.write(f"\n=== BUTTONS after full fill ===\n{btns}\n")

        # check if price cells rendered now
        body_txt = (await page.locator("body").inner_text(timeout=4000)).lower()
        print("price cells now present:",
              ("meesho price" in body_txt and "mrp" in body_txt))
        print("card present:",
              ("bank settlement" in body_txt or "customer price breakdown" in body_txt))
        # dump current DOM for inspection
        (P.LOG_DIR / "diag_after_fill_dom.txt").write_text(
            await page.locator("body").inner_text(timeout=4000))
        await page.screenshot(path=str(P.LOG_DIR / "diag_after_fill.png"), full_page=True)
        print("DOM + screenshot saved")

        # Always discard.
        await P.discard_catalog(page)
        await browser.close()
    print("diagnostic written to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
