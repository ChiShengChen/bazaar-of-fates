"""Capture real screenshots of the running Next app for docs/astrology.md.
Run with both servers up:  uvicorn (:8000) + next start (:3000).
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)


def shot(loc, name):
    loc.screenshot(path=str(OUT / name))
    print("  ✓", name)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1100, "height": 1400}, device_scale_factor=2)
    pg.goto("http://localhost:3000/", wait_until="networkidle")

    # --- natal astrology wheel ---
    pg.get_by_text("Western Astrology", exact=False).first.click()
    pg.get_by_role("button", name="Cast + Read 排盤＋解讀").click()
    pg.wait_for_selector("#chart-area svg", timeout=20000)
    pg.wait_for_timeout(800)
    shot(pg.locator("#chart-area svg"), "natal-wheel.png")

    # --- transits overlay (outer ring + major-transit highlight, date 2005-07 when Saturn hits MC) ---
    pg.locator("select:has(option[value='transits'])").select_option("transits")   # Overlay select
    pg.wait_for_timeout(200)
    pg.get_by_role("button", name="Cast + Read 排盤＋解讀").click()
    pg.wait_for_selector("#chart-area svg", timeout=20000)
    pg.wait_for_timeout(800)
    shot(pg.locator("#chart-area svg"), "transits-wheel.png")

    # --- synastry bi-wheel ---
    pg.get_by_text("Synastry 合盤", exact=False).first.click()
    pg.get_by_role("button", name="Compare 合盤").click()
    pg.wait_for_selector("#chart-area svg", timeout=20000)
    pg.wait_for_timeout(1000)
    shot(pg.locator("#chart-area svg"), "synastry-biwheel.png")

    # --- group matrix ---
    pg.get_by_text("Group 團體", exact=False).first.click()
    pg.get_by_role("button", name="Compare group 團體合盤").click()
    pg.wait_for_selector("table", timeout=20000)
    pg.wait_for_timeout(1000)
    shot(pg.locator(".card").filter(has_text="Group dynamics").first, "group-matrix.png")

    b.close()
print("done")
