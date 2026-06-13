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


def _year_score(row: dict) -> int:
    """A small favourability score (-2..+2): 八字 喜用/忌 + Jyotiṣa benefic/malefic daśā."""
    s = 1 if row["bazi_verdict"].startswith("favourable") else -1
    s += 1 if row["jyotish_nature"] == "benefic" else -1
    return s


def overview(birth: BirthInput, start_year: int, count: int = 6) -> dict:
    """A compact one-row-per-year arc across `count` years (no full per-year LLM),
    with a favourability score and auto-detected turning points."""
    rows = []
    for y in range(start_year, start_year + count):
        s = compute(birth, y, light=True)["sections"]
        rows.append({
            "year": y, "age": y - birth.as_date.year,
            "sr_ascendant": s["solar_return"]["ascendant"],
            "bazi_element": s["bazi"]["liunian_element"], "bazi_verdict": s["bazi"]["verdict"],
            "dayun": s["bazi"]["dayun"],
            "ziwei_stem": s["ziwei"]["year_stem"],
            "jyotish_lord": s["jyotish"]["mahadasha_lord"], "jyotish_nature": s["jyotish"]["nature"],
        })

    # planet returns (Saturn ~29.5 yr, Jupiter ~12 yr) landing in any of these years
    returns_by_year: dict[str, list[str]] = {}
    try:
        for p in tl.astrology_returns(birth).periods:
            returns_by_year.setdefault(p.start[:4], []).append(p.label)
    except Exception:  # noqa: BLE001 — never let the milestone scan break the overview
        pass

    prev = None
    for r in rows:
        r["score"] = _year_score(r)
        t: list[str] = []
        if prev is not None:
            if r["dayun"] != prev["dayun"]:
                t.append(f"new 大運 {r['dayun']}")
            if r["jyotish_lord"] != prev["jyotish_lord"]:
                t.append(f"daśā → {r['jyotish_lord']}")
            pf = prev["bazi_verdict"].startswith("favourable")
            cf = r["bazi_verdict"].startswith("favourable")
            if pf != cf:
                t.append("八字 → " + ("favourable 喜用" if cf else "challenging 忌耗"))
        t.extend(returns_by_year.get(str(r["year"]), []))   # e.g. "Saturn return #1"
        r["turning"] = t
        prev = r

    turning_points = [{"year": r["year"], "events": r["turning"]} for r in rows if r["turning"]]
    return {"subject": birth.label(), "start_year": start_year, "count": count, "years": rows,
            "turning_points": turning_points,
            "summary": f"{birth.label()} · {start_year}–{start_year + count - 1}：{count}-year outlook"
                       + (f"・{len(turning_points)} turning point(s)" if turning_points else "")}
