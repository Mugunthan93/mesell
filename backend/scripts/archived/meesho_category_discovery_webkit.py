"""Meesho Bulk Catalog Upload — full category-tree discovery.

One-time interactive scrape. Logs in with the same WebKit (headed) flow used by
``meesho_template_scraper.py``, opens the Bulk Catalog Upload page, then walks
the cascading category picker depth-first until every leaf is found.

A leaf is a category where the right-hand panel exposes the
"Don't have ... template?" / Download Template control. The resulting tree is
written to ``backend/app/data/meesho_category_tree.json``.

This script is intentionally long-running and interactive — the user wants to
watch it work. Run it manually; do not schedule it.
"""

from __future__ import annotations

import json
import logging
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from playwright.sync_api import (
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/mugunthansrinivasan/Project/mesell")
CREDS_FILE = PROJECT_ROOT / ".meesho_creds.env"

OUTPUT_FILE = PROJECT_ROOT / "backend" / "app" / "data" / "meesho_category_tree.json"
DEBUG_SCREENSHOT_DIR = PROJECT_ROOT / "logs" / "scraper" / "discovery_screenshots"

LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"
BULK_UPLOAD_URL = "https://supplier.meesho.com/panel/v3/new/products/upload/bulk"

# The Meesho cascading picker exposes 8 known top-level groups as per the task brief.
TOP_LEVEL_CATEGORIES = [
    "Men Fashion",
    "Women Fashion",
    "Home & Living",
    "Kids & Toys",
    "Personal Care & Wellness",
    "Mobiles & Tablets",
    "Consumer Electronics",
    "Appliances",
]

# Hard cap on how deep we descend. Meesho currently uses 4 columns; 6 is a
# generous safety belt against accidental loops.
MAX_DEPTH = 6

NAV_TIMEOUT_MS = 45_000
ACTION_TIMEOUT_MS = 20_000
LEAF_CHECK_TIMEOUT_MS = 4_000

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("meesho-discovery")


# ---------------------------------------------------------------------------
# Helpers (mirrored from the PoC scraper so this script is self-contained)
# ---------------------------------------------------------------------------


def jitter(min_s: float = 1.2, max_s: float = 2.4) -> None:
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def screenshot(page: Page, name: str) -> Path | None:
    try:
        DEBUG_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = DEBUG_SCREENSHOT_DIR / f"{name}.png"
        page.screenshot(path=str(path), full_page=True)
        return path
    except Exception as exc:  # noqa: BLE001
        log.debug("Screenshot %s failed: %s", name, exc)
        return None


def detect_block(page: Page) -> None:
    url = page.url
    if any(token in url for token in ("captcha", "/error", "/blocked")):
        raise RuntimeError(f"Detected block URL: {url}")

    body_text = ""
    try:
        body_text = (page.locator("body").inner_text(timeout=2_000) or "").lower()
    except Exception:  # noqa: BLE001
        return

    block_markers = (
        "access denied",
        "too many requests",
        "rate limit",
        "captcha",
        "are you a human",
        "forbidden",
    )
    for marker in block_markers:
        if marker in body_text:
            raise RuntimeError(f"Block marker detected in page body: {marker!r}")


def slugify(parts: list[str]) -> str:
    def one(part: str) -> str:
        s = part.strip().lower()
        s = re.sub(r"[^a-z0-9]+", "-", s)
        return s.strip("-")

    return "__".join(one(p) for p in parts if p)


# ---------------------------------------------------------------------------
# Credentials / login (kept compatible with the PoC scraper)
# ---------------------------------------------------------------------------


def load_creds() -> tuple[str, str]:
    import os

    if not CREDS_FILE.exists():
        raise FileNotFoundError(f"Credentials file missing: {CREDS_FILE}")
    load_dotenv(CREDS_FILE)
    user = os.environ.get("MEESHO_USERNAME", "").strip()
    pwd = os.environ.get("MEESHO_PASSWORD", "").strip()
    if not user or not pwd:
        raise RuntimeError("MEESHO_USERNAME / MEESHO_PASSWORD missing in creds file")
    return user, pwd


def perform_login(page: Page, username: str, password: str) -> None:
    log.info("Navigating to login URL: %s", LOGIN_URL)
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
    jitter()
    detect_block(page)

    user_field = None
    for build in (
        lambda: page.get_by_placeholder(re.compile(r"email.*mobile", re.I)),
        lambda: page.get_by_label(re.compile(r"email.*mobile", re.I)),
        lambda: page.get_by_role("textbox", name=re.compile(r"email|mobile", re.I)),
        lambda: page.locator("input[type='text']").first,
    ):
        try:
            loc = build()
            loc.wait_for(state="visible", timeout=5_000)
            user_field = loc
            break
        except Exception:  # noqa: BLE001
            continue
    if user_field is None:
        screenshot(page, "login_no_user_field")
        raise RuntimeError("Could not locate username field on login page")
    user_field.fill(username)
    jitter(0.8, 1.4)

    pwd_field = None
    for build in (
        lambda: page.get_by_placeholder(re.compile(r"password", re.I)),
        lambda: page.get_by_label(re.compile(r"password", re.I)),
        lambda: page.locator("input[type='password']").first,
    ):
        try:
            loc = build()
            loc.wait_for(state="visible", timeout=5_000)
            pwd_field = loc
            break
        except Exception:  # noqa: BLE001
            continue
    if pwd_field is None:
        screenshot(page, "login_no_pwd_field")
        raise RuntimeError("Could not locate password field on login page")
    pwd_field.fill(password)
    jitter(0.8, 1.4)

    submit = None
    for build in (
        lambda: page.get_by_role("button", name=re.compile(r"log\s*in|sign\s*in", re.I)),
        lambda: page.locator("button[type='submit']").first,
    ):
        try:
            loc = build()
            loc.wait_for(state="visible", timeout=5_000)
            submit = loc
            break
        except Exception:  # noqa: BLE001
            continue
    if submit is None:
        screenshot(page, "login_no_submit")
        raise RuntimeError("Could not locate login submit button")

    submit.click()
    try:
        page.wait_for_url(lambda u: "login" not in u, timeout=NAV_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        screenshot(page, "login_no_redirect")
        raise RuntimeError(f"Login did not redirect away from /login. URL={page.url!r}")

    detect_block(page)
    page.wait_for_load_state("domcontentloaded", timeout=NAV_TIMEOUT_MS)
    log.info("Login OK — current URL: %s", page.url)
    jitter()


def navigate_to_bulk_upload(page: Page) -> None:
    log.info("Opening bulk upload page")
    page.goto(BULK_UPLOAD_URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
    jitter()
    detect_block(page)

    if "login" in page.url:
        raise RuntimeError(f"Bulk-upload URL redirected back to login: {page.url}")

    try:
        page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        pass

    body_text = ""
    try:
        body_text = page.locator("body").inner_text(timeout=3_000).lower()
    except Exception:  # noqa: BLE001
        pass

    on_bulk = ("select category" in body_text) or ("women fashion" in body_text)
    if not on_bulk:
        clicked = False
        for build in (
            lambda: page.get_by_role("button", name=re.compile(r"add\s+catalogs?\s+in\s+bulk", re.I)),
            lambda: page.get_by_role("link", name=re.compile(r"add\s+catalogs?\s+in\s+bulk", re.I)),
            lambda: page.get_by_text(re.compile(r"add\s+catalogs?\s+in\s+bulk", re.I)),
        ):
            try:
                loc = build()
                for idx in range(loc.count()):
                    cand = loc.nth(idx)
                    if cand.is_visible():
                        cand.scroll_into_view_if_needed(timeout=ACTION_TIMEOUT_MS)
                        cand.click(timeout=ACTION_TIMEOUT_MS)
                        clicked = True
                        break
                if clicked:
                    break
            except Exception:  # noqa: BLE001
                continue
        if not clicked:
            screenshot(page, "bulk_nav_failed")
            raise RuntimeError("Could not navigate to bulk-upload UI")
        jitter(1.5, 2.5)
        try:
            page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            pass

    log.info("Bulk-upload page loaded at %s", page.url)


# ---------------------------------------------------------------------------
# Category-tree walk
# ---------------------------------------------------------------------------


def reset_to_bulk_upload(page: Page) -> None:
    """Reload the bulk-upload page to reset the cascading picker between paths."""
    page.goto(BULK_UPLOAD_URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
    try:
        page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        pass
    jitter(1.0, 2.0)


def click_category(page: Page, label: str, column_index: int) -> bool:
    """Click a single category cell. Returns True on success, False if not found.

    Reuses the rightmost-visible strategy from the PoC scraper to disambiguate
    duplicate labels appearing across cascading columns.
    """
    strategies = [
        lambda: page.get_by_role("button", name=re.compile(rf"^\s*{re.escape(label)}\s*$", re.I)),
        lambda: page.get_by_role("treeitem", name=re.compile(rf"^\s*{re.escape(label)}\s*$", re.I)),
        lambda: page.get_by_role("listitem", name=re.compile(rf"^\s*{re.escape(label)}\s*$", re.I)),
        lambda: page.get_by_role("menuitem", name=re.compile(rf"^\s*{re.escape(label)}\s*$", re.I)),
        lambda: page.get_by_text(re.compile(rf"^\s*{re.escape(label)}\s*$", re.I)),
    ]
    for build in strategies:
        try:
            loc = build()
            count = loc.count()
            if count == 0:
                continue
            visible: list[tuple[float, Any]] = []
            for idx in range(count):
                cand = loc.nth(idx)
                try:
                    if not cand.is_visible():
                        continue
                    box = cand.bounding_box()
                    x = box["x"] if box else 0.0
                    visible.append((x, cand))
                except Exception:  # noqa: BLE001
                    continue
            if not visible:
                continue
            visible.sort(key=lambda pair: pair[0])
            target = visible[-1][1]
            target.scroll_into_view_if_needed(timeout=ACTION_TIMEOUT_MS)
            target.click(timeout=ACTION_TIMEOUT_MS)
            jitter(0.8, 1.6)
            detect_block(page)
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


def navigate_path(page: Page, path: list[str]) -> bool:
    """Reload the page and click through the cascading columns to ``path``."""
    reset_to_bulk_upload(page)
    for idx, label in enumerate(path):
        ok = click_category(page, label, idx)
        if not ok:
            log.warning("Could not click %r at column %d on path %s", label, idx, path)
            return False
        try:
            page.wait_for_load_state("networkidle", timeout=ACTION_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            pass
    return True


def detect_leaf(page: Page) -> bool:
    """Return True if the current category screen exposes a Download Template control."""
    try:
        # Quick scroll so the right-panel template block enters the viewport.
        page.mouse.wheel(0, 400)
    except Exception:  # noqa: BLE001
        pass

    leaf_patterns = (
        re.compile(r"don'?t\s+have.*template", re.I),
        re.compile(r"download\s+template", re.I),
        re.compile(r"get\s+template", re.I),
    )
    for pat in leaf_patterns:
        try:
            loc = page.get_by_text(pat)
            count = loc.count()
            for idx in range(count):
                cand = loc.nth(idx)
                try:
                    if cand.is_visible():
                        return True
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            continue
    return False


def discover_children(page: Page, depth: int) -> list[str]:
    """Return the visible category labels in the column matching ``depth``.

    Heuristic: after clicking column ``depth-1``, the next column appears to the
    right. We look for clickable, visible text elements that look like category
    cells (short, capitalised, not navigation chrome).
    """
    # Wait a tick for the next column to populate.
    try:
        page.wait_for_load_state("networkidle", timeout=ACTION_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        pass
    jitter(0.6, 1.2)

    # Strategy: read every visible text-only listitem/button/treeitem.
    candidates: dict[str, float] = {}  # label -> x-coordinate (used for column inference)

    role_selectors = ["listitem", "treeitem", "menuitem", "button"]
    for role in role_selectors:
        try:
            loc = page.get_by_role(role)
            count = min(loc.count(), 400)
        except Exception:  # noqa: BLE001
            continue
        for idx in range(count):
            cand = loc.nth(idx)
            try:
                if not cand.is_visible():
                    continue
                text = (cand.inner_text(timeout=1_000) or "").strip()
                if not text:
                    continue
                if "\n" in text:
                    text = text.split("\n", 1)[0].strip()
                if len(text) < 2 or len(text) > 60:
                    continue
                # Filter chrome / actions.
                lower = text.lower()
                if any(
                    skip in lower
                    for skip in (
                        "upload",
                        "download",
                        "next",
                        "back",
                        "sign out",
                        "log out",
                        "help",
                        "submit",
                        "browse",
                        "select category",
                        "don't have",
                        "dont have",
                        "template",
                        "drag",
                        "add catalog",
                    )
                ):
                    continue
                box = cand.bounding_box()
                if not box:
                    continue
                # Skip very wide elements (likely whole rows / nav containers).
                if box["width"] > 320:
                    continue
                candidates.setdefault(text, box["x"])
            except Exception:  # noqa: BLE001
                continue

    if not candidates:
        return []

    # Infer the rightmost column's x-range — children of the just-clicked node
    # are the items with the largest x-coordinate.
    sorted_x = sorted(candidates.values())
    # Bucket by 60-px columns.
    columns: dict[int, list[str]] = {}
    for label, x in candidates.items():
        bucket = int(x // 60)
        columns.setdefault(bucket, []).append(label)

    rightmost_bucket = max(columns.keys())
    result = sorted(set(columns[rightmost_bucket]))
    log.debug("discover_children depth=%d -> %d items", depth, len(result))
    return result


def walk_tree(page: Page, path: list[str], leaves: list[dict], visited: set[str]) -> None:
    """Depth-first walk. Appends each leaf as a dict to ``leaves``."""
    key = " > ".join(path)
    if key in visited:
        return
    visited.add(key)

    if len(path) > MAX_DEPTH:
        log.warning("Max depth exceeded at %s — stopping descent", key)
        return

    ok = navigate_path(page, path)
    if not ok:
        log.warning("Skipping unreachable path: %s", path)
        return

    if detect_leaf(page):
        slug = slugify(path)
        leaves.append({"path": path[:], "slug": slug, "is_leaf": True})
        log.info("LEAF [%d total]: %s", len(leaves), " > ".join(path))
        return

    children = discover_children(page, len(path))
    if not children:
        log.warning("No children found at %s — treating as terminal non-leaf", key)
        return

    log.info("Node %s has %d children: %s", key, len(children), children[:6])
    for child in children:
        walk_tree(page, path + [child], leaves, visited)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run(pw: Playwright) -> dict:
    user, pwd = load_creds()

    browser = pw.webkit.launch(headless=False)
    context = browser.new_context(
        locale="en-IN",
        timezone_id="Asia/Kolkata",
        viewport={"width": 1440, "height": 900},
    )
    context.set_default_timeout(ACTION_TIMEOUT_MS)
    context.set_default_navigation_timeout(NAV_TIMEOUT_MS)
    page = context.new_page()

    leaves: list[dict] = []
    visited: set[str] = set()
    try:
        perform_login(page, user, pwd)
        navigate_to_bulk_upload(page)

        for top in TOP_LEVEL_CATEGORIES:
            log.info("==== Top-level: %s ====", top)
            try:
                walk_tree(page, [top], leaves, visited)
            except RuntimeError as exc:
                # Hard block — abort immediately so we don't burn through the
                # remaining tree under captcha.
                log.error("Aborting discovery: %s", exc)
                break
            except Exception as exc:  # noqa: BLE001
                log.warning("Top-level %s threw %s — continuing", top, exc)
                continue
    finally:
        context.close()
        browser.close()

    return {
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "categories": leaves,
    }


def main() -> int:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEBUG_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    log.info("==== Meesho category-tree discovery starting ====")
    with sync_playwright() as pw:
        tree = run(pw)

    OUTPUT_FILE.write_text(json.dumps(tree, indent=2, ensure_ascii=False))
    log.info("Wrote %d leaves to %s", len(tree["categories"]), OUTPUT_FILE)

    print("\n========= DISCOVERY SUMMARY =========")
    print(f"discovered_at : {tree['discovered_at']}")
    print(f"leaf_count    : {len(tree['categories'])}")
    print(f"output_file   : {OUTPUT_FILE}")
    by_top: dict[str, int] = {}
    for leaf in tree["categories"]:
        top = leaf["path"][0] if leaf["path"] else "?"
        by_top[top] = by_top.get(top, 0) + 1
    for top, count in sorted(by_top.items()):
        print(f"  {top}: {count} leaves")
    print("=====================================")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        log.exception("Discovery failed: %s", exc)
        sys.exit(1)
