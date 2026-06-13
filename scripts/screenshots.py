"""Capture real screenshots of the running Next app for the docs.
Run with both servers up:  uvicorn (:8000) + next start (:3000).
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

# per-system result-card captures: (pill text fragment, output filename)
SYSTEMS = [
    ("八字", "bazi-chart.png"), ("紫微斗數", "ziwei-chart.png"), ("梅花易數", "iching-chart.png"),
    ("四柱推命", "suimei-chart.png"), ("七政四餘", "qizheng-chart.png"), ("鐵板神數", "tieban-chart.png"),
    ("奇門遁甲", "qimen-chart.png"), ("大六壬", "liuren-chart.png"), ("太乙神數", "taiyi-chart.png"),
    ("Jyoti", "jyotish-chart.png"),
]


def shot(loc, name):
    loc.screenshot(path=str(OUT / name))
    print("  ✓", name)


def result_card(pg):
    return pg.locator("#chart-area").locator("xpath=ancestor::div[contains(@class,'card')][1]")


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1100, "height": 1500}, device_scale_factor=2)
    pg.goto("http://localhost:3000/", wait_until="networkidle")
    cast = lambda: pg.get_by_role("button", name="Cast + Read 排盤＋解讀").click()

    # --- per-system result cards (single mode, no overlay) ---
    for frag, name in SYSTEMS:
        pg.locator(".pill", has_text=frag).first.click()
        cast()
        pg.wait_for_selector("#chart-area", timeout=20000)
        pg.wait_for_timeout(900)
        shot(result_card(pg), name)

    # --- astrology natal wheel + overlays ---
    pg.get_by_text("Western Astrology", exact=False).first.click()
    cast()
    pg.wait_for_selector("#chart-area svg", timeout=20000)
    pg.wait_for_timeout(800)
    shot(pg.locator("#chart-area svg"), "natal-wheel.png")

    def overlay_shot(value, name, method=None):
        pg.locator("select:has(option[value='transits'])").select_option(value)
        if method:
            pg.locator("select:has(option[value='solar_arc'])").select_option(method)
        pg.wait_for_timeout(200)
        cast()
        pg.wait_for_selector("#chart-area svg", timeout=20000)
        pg.wait_for_timeout(900)
        shot(pg.locator("#chart-area svg"), name)

    overlay_shot("transits", "transits-wheel.png")
    overlay_shot("progress", "progressions-wheel.png")
    overlay_shot("progress", "solar-arc-wheel.png", method="solar_arc")
    overlay_shot("solar_return", "solar-return-wheel.png")
    overlay_shot("lunar_return", "lunar-return-wheel.png")

    # --- synastry: bi-wheel + composite + Davison ---
    pg.get_by_text("Synastry 合盤", exact=False).first.click()
    pg.get_by_role("button", name="Compare 合盤").click()
    pg.wait_for_selector("#chart-area svg", timeout=20000)
    pg.wait_for_timeout(1200)
    shot(pg.locator("#chart-area svg"), "synastry-biwheel.png")
    shot(pg.locator(".card").filter(has_text="Composite chart").first.locator("svg"), "composite-wheel.png")
    shot(pg.locator(".card").filter(has_text="Davison chart").first.locator("svg"), "davison-wheel.png")

    # --- group: matrix + group composite ---
    pg.get_by_text("Group 團體", exact=False).first.click()
    pg.get_by_role("button", name="Compare group 團體合盤").click()
    pg.wait_for_selector("table", timeout=20000)
    pg.wait_for_timeout(1200)
    shot(pg.locator(".card").filter(has_text="Group dynamics").first, "group-matrix.png")
    shot(pg.locator(".card").filter(has_text="Group composite").first.locator("svg"), "group-composite-wheel.png")

    # --- annual multi-year overview heatmap ---
    pg.get_by_text("Annual 年度報告", exact=False).first.click()
    nums = pg.locator("input[type='number']")
    nums.nth(0).fill("2018")   # year
    nums.nth(1).fill("12")     # span
    pg.get_by_role("button", name="Multi-year 多年").click()
    pg.wait_for_selector("text=Multi-year outlook", timeout=20000)
    pg.wait_for_timeout(1000)
    shot(pg.locator(".card").filter(has_text="Multi-year outlook").first, "annual-overview.png")

    # --- two-person comparison ---
    pg.get_by_text("vs Person B", exact=False).first.click()
    pg.wait_for_timeout(200)
    pg.get_by_role("button", name="Multi-year 多年").click()
    pg.wait_for_selector("text=Two-person comparison", timeout=20000)
    pg.wait_for_timeout(1200)
    shot(pg.locator(".card").filter(has_text="Two-person comparison").first, "compare-overview.png")

    b.close()
print("done")
