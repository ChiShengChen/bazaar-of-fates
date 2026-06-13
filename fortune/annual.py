"""年度報告 / Annual report — one person, one year, across the relevant systems.

Pulls the year's forecast from each system that has a usable annual view: the Western
**Solar Return** (ascendant, highlights, the year's key transits), BaZi **流年/大運**,
紫微 **流年四化**, and Jyotiṣa **Mahādaśā** — then an LLM ties it into one bilingual report.
"""

from __future__ import annotations

from datetime import date

from fortune import casting, timeline as tl
from fortune.birth import BirthInput
from fortune.engines.bazi import bazi as BZ
from fortune.engines.jyotish import jyotish as JY
from fortune.engines.ziwei import ziwei as ZW


def compute(birth: BirthInput, year: int, *, light: bool = False) -> dict:
    """Assemble one year. `light` skips the chart payload (for multi-year overviews)."""
    mid = date(year, 6, 1)
    report: dict = {"year": year, "subject": birth.label(), "sections": {}}

    # — Western Solar Return —
    sr = casting.cast("astrology", birth, solar_return=True, transit_date=f"{year}-06-15")
    sr_section = {
        "ascendant": sr.readings.get("solar_return_asc"),
        "moment": sr.readings.get("solar_return_moment"),
        "highlights": sr.readings.get("solar_return_highlights", []),
        "key_transits": sr.readings.get("solar_return_timeline", []),
    }
    if not light:                                            # carry the chart so the UI can draw the SR wheel
        sr_section["chart"] = {
            "natal": sr.chart.get("planets", []),
            "natal_houses": (sr.ascendant or {}).get("houses", []),
            "sr_planets": sr.chart.get("solar_return", []),
            "sr_houses": sr.chart.get("solar_return_houses", []),
            "sr_aspects": sr.chart.get("solar_return_aspects", []),
        }
    report["sections"]["solar_return"] = sr_section

    # — BaZi 流年 + 大運 —
    fav = BZ.strength_and_favourable(BZ.four_pillars(birth.as_date, birth.hour))["favourable"]
    liunian = BZ.liunian_elem(mid)
    dayun = tl.bazi_dayun(birth)
    age = year - birth.as_date.year
    cur = next((p for p in dayun.periods if (p.start_age or 0) <= age < (p.start_age or 0) + 10), None)
    report["sections"]["bazi"] = {
        "liunian_element": liunian, "favourable": fav,
        "verdict": "favourable 喜用" if liunian in fav else "challenging 忌耗",
        "dayun": (f"{cur.label}（{cur.detail}）" if cur else None),
    }

    # — 紫微 流年四化 —
    stem, mut = ZW.liunian_sihua(mid)
    report["sections"]["ziwei"] = {
        "year_stem": stem,
        "sihua": [f"{mut[i]}化{ZW.HUA[i]}" for i in range(4)],
    }

    # — Jyotiṣa Mahādaśā —
    lord = JY.mahadasha_lord(birth.as_date, mid)
    report["sections"]["jyotish"] = {
        "mahadasha_lord": lord, "nature": "benefic" if lord in JY.BENEFIC else "malefic",
    }

    sa = report["sections"]["solar_return"]["ascendant"] or "—"
    report["summary"] = (
        f"{birth.label()} · {year}：SR 上升 {sa}・八字流年 {liunian}（{report['sections']['bazi']['verdict']}）"
        f"・紫微 {stem}年・Jyotiṣa {lord} daśā"
    )
    return report


def overview(birth: BirthInput, start_year: int, count: int = 6) -> dict:
    """A compact one-row-per-year arc across `count` years (no full per-year LLM)."""
    rows = []
    for y in range(start_year, start_year + count):
        r = compute(birth, y, light=True)
        s = r["sections"]
        rows.append({
            "year": y, "age": y - birth.as_date.year,
            "sr_ascendant": s["solar_return"]["ascendant"],
            "bazi_element": s["bazi"]["liunian_element"], "bazi_verdict": s["bazi"]["verdict"],
            "dayun": s["bazi"]["dayun"],
            "ziwei_stem": s["ziwei"]["year_stem"],
            "jyotish_lord": s["jyotish"]["mahadasha_lord"], "jyotish_nature": s["jyotish"]["nature"],
        })
    return {"subject": birth.label(), "start_year": start_year, "count": count, "years": rows,
            "summary": f"{birth.label()} · {start_year}–{start_year + count - 1}：{count}-year outlook"}
