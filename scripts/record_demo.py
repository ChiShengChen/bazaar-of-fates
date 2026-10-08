"""Record the 10-second hero GIF for the README (input → charts → streaming reading) and render
the 1280×640 social-preview card. Needs both servers up (API :8010 or :8000, Next :3000) and Playwright.

  python scripts/record_demo.py gif      → docs/img/demo.gif  (via Playwright's bundled ffmpeg)
  python scripts/record_demo.py social   → docs/img/social-preview.png  (upload in GitHub → Settings → Social preview)
"""

from __future__ import annotations

import glob, os, shutil, subprocess, sys, tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "docs" / "img"
WEB = os.environ.get("DEMO_WEB", "http://localhost:3000/")


def _ffmpeg() -> str:
    cands = glob.glob(os.path.expanduser("~/Library/Caches/ms-playwright/ffmpeg-*/ffmpeg-*")) + glob.glob(os.path.expanduser("~/.cache/ms-playwright/ffmpeg-*/ffmpeg-*"))
    return shutil.which("ffmpeg") or (cands[0] if cands else "ffmpeg")


def gif() -> None:
    tmp = tempfile.mkdtemp()
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1100, "height": 760}, record_video_dir=tmp, record_video_size={"width": 1100, "height": 760})
        pg = ctx.new_page()
        pg.goto(WEB, wait_until="networkidle")
        pg.wait_for_timeout(600)
        pg.fill("input[list='bf-cities']", ""); pg.type("input[list='bf-cities']", "台北", delay=80); pg.locator("input[list='bf-cities']").blur()
        pg.wait_for_timeout(500)
        for frag in ("八字", "紫微斗數"):
            pg.locator(".pill", has_text=frag).first.click()
            pg.get_by_role("button", name="Cast + Read 排盤＋解讀").click()
            pg.wait_for_selector("#chart-area", timeout=30000)
            pg.wait_for_timeout(1800)
            pg.mouse.wheel(0, 500); pg.wait_for_timeout(900); pg.mouse.wheel(0, -500); pg.wait_for_timeout(300)
        pg.locator(".pill", has_text="Synthesis").first.click()
        pg.locator("input[placeholder*='career']").fill("明年事業")
        pg.get_by_role("button", name="Synthesize 綜合會診").click()
        pg.wait_for_selector("table", timeout=60000); pg.wait_for_timeout(1800)
        pg.mouse.wheel(0, 400); pg.wait_for_timeout(1200)
        video = pg.video.path()
        ctx.close(); b.close()
    out = IMG / "demo.gif"
    subprocess.run([_ffmpeg(), "-y", "-i", video, "-vf", "fps=10,scale=900:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
                    "-loop", "0", str(out)], check=True, capture_output=True)
    print("→", out, f"{out.stat().st_size // 1024} KB")


def social() -> None:
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
    body{{margin:0;width:1280px;height:640px;background:#0b0b10;color:#e4e4e7;font-family:-apple-system,"Noto Sans TC","PingFang TC",sans-serif;overflow:hidden}}
    .wrap{{display:flex;height:640px}} .l{{flex:1;padding:64px 0 0 64px;min-width:700px}} .r{{width:520px;display:flex;flex-wrap:wrap;gap:10px;align-content:center;padding:0 48px}}
    h1{{font-size:44px;margin:0;letter-spacing:-1px;white-space:nowrap}} h2{{font-size:26px;font-weight:500;color:#a78bfa;margin:8px 0 22px}}
    p{{font-size:20px;line-height:1.55;color:#a1a1aa;max-width:600px;margin:0 0 18px}}
    .pill{{border:1px solid #2a2a33;border-radius:999px;padding:7px 13px;font-size:15px;color:#d4d4d8;background:#111118}} .pill.on{{border-color:#a78bfa;color:#a78bfa;background:#1c1530}}
    .tags{{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}} .tag{{font-size:14px;color:#71717a}}
    .r img{{width:150px;height:150px;object-fit:cover;border-radius:10px;border:1px solid #2a2a33}}
    </style></head><body><div class="wrap"><div class="l">
    <h1>🔮 Bazaar of Fates · 算命</h1><h2>13 divination systems · one birth moment · real astronomy</h2>
    <p>西洋占星 · 八字 · 紫微斗數 · 梅花易數 · 六爻 · 小六壬 · 四柱推命 · 七政四餘 · 鐵板神數 · 奇門遁甲 · 大六壬 · 太乙神數 · Jyotiṣa</p>
    <p>Exact 節氣 and planets, cross-validated against Swiss Ephemeris & iztro. Question-oriented readings, cross-tradition synthesis, 擇日, synastry, forecasts. MIT.</p>
    <div class="tags"><span class="pill on">pip install bazaar-of-fates</span><span class="pill">MCP server</span><span class="pill">Python · FastAPI · Next.js</span><span class="pill">518,400-chart dataset</span></div>
    </div><div class="r">
    <img src="file://{IMG}/natal-wheel.png"><img src="file://{IMG}/ziwei-chart.png"><img src="file://{IMG}/bazi-chart.png">
    <img src="file://{IMG}/qimen-chart.png"><img src="file://{IMG}/synthesis.png"><img src="file://{IMG}/zeri.png">
    </div></div></body></html>"""
    tmp = Path(tempfile.mkdtemp()) / "card.html"; tmp.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 640})
        pg.goto(tmp.as_uri()); pg.wait_for_timeout(800)
        out = IMG / "social-preview.png"; pg.screenshot(path=str(out)); b.close()
    print("→", out)


def gif_space() -> None:
    """Hero GIF from the themed Space UI (run `python deploy/hf-space/app.py` on :7860 first, or set DEMO_SPACE)."""
    url = os.environ.get("DEMO_SPACE", "http://localhost:7860/")
    tmp = tempfile.mkdtemp()
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1100, "height": 760}, record_video_dir=tmp, record_video_size={"width": 1100, "height": 760})
        pg = ctx.new_page()
        pg.goto(url, wait_until="networkidle"); pg.wait_for_timeout(1200)
        pg.get_by_role("button", name="排 盤 · Cast").click(); pg.wait_for_timeout(2500)
        pg.mouse.wheel(0, 650); pg.wait_for_timeout(1400); pg.mouse.wheel(0, 500); pg.wait_for_timeout(900); pg.mouse.wheel(0, -1150); pg.wait_for_timeout(300)
        pg.locator("input[aria-label='System 系統']").click(); pg.wait_for_timeout(300); pg.get_by_role("option", name="紫微斗數 · Zi Wei Dou Shu · Purple Star").click(); pg.wait_for_timeout(300)
        pg.get_by_role("button", name="排 盤 · Cast").click(); pg.wait_for_timeout(2500)
        pg.mouse.wheel(0, 650); pg.wait_for_timeout(1600); pg.mouse.wheel(0, -650); pg.wait_for_timeout(300)
        pg.get_by_role("tab", name="Synthesis 綜合會診").click(); pg.wait_for_timeout(400)
        pg.locator("[placeholder*='事業']").first.fill("明年事業"); pg.get_by_role("button", name="會 診 · 十三術同問").click(); pg.wait_for_timeout(5000)
        pg.mouse.wheel(0, 500); pg.wait_for_timeout(1500)
        video = pg.video.path(); ctx.close(); b.close()
    out = IMG / "demo.gif"
    subprocess.run([_ffmpeg(), "-y", "-i", video, "-vf", "fps=10,scale=900:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
                    "-loop", "0", str(out)], check=True, capture_output=True)
    print("→", out, f"{out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    {"gif": gif, "gif_space": gif_space, "social": social}.get(sys.argv[1] if len(sys.argv) > 1 else "gif", gif)()
