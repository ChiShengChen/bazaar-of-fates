"""西洋占星 — cast a natal chart (planets + ascendant + whole-sign houses) from a birth moment.

Planet longitudes come from the synced engine (date-based). The ascendant and houses
need the birth time AND birthplace, supplied by fortune.astro_ext. With no time/place we
gracefully fall back to the planets-only chart and flag the ascendant as unknown.
"""

from __future__ import annotations

from fortune import astro_ext as AX
from fortune.birth import BirthInput
from fortune.engines.astrology import astro
from fortune.schemas import Chart

KEY, ZH, EN, ORB = "astrology", "西洋占星", "Western Astrology", 6.0


def cast(birth: BirthInput, *, house_system: str = "whole_sign") -> Chart:
    d = birth.as_date
    chart_rows = [
        {"body": b, "ecliptic_lon": lon, "sign": sign, "sign_zh": astro.sign_zh(lon), "retrograde": retro}
        for (b, lon, sign, retro) in astro.chart_for(d)
    ]
    readings = astro.astro_readings(d, ORB)
    chain = astro.reasoning_chain(d, ORB)
    sun = next((r for r in chart_rows if r["body"] == "Sun"), None)
    moon = readings.get("moon_phase", "")

    asc = AX.ascendant_block(birth, house_system=house_system)   # None if 時辰/出生地 missing
    if asc:
        cusps = asc["houses"]
        place = (lambda lon: AX.house_of_cusps(lon, cusps)) if asc["house_system"] == "placidus" \
            else (lambda lon: AX.house_of(lon, asc["longitude"]))
        for r in chart_rows:
            r["house"] = place(r["ecliptic_lon"])
        hs_label = {"placidus": "Placidus 不等宮", "koch": "Koch 不等宮",
                    "equal": "Equal 等宮", "whole_sign": "whole-sign 整星座"}.get(
                        asc["house_system"], asc["house_system"])
        readings["ascendant"] = f"{asc['sign']} {asc['sign_zh']} {asc['longitude']:.1f}°"
        readings["house_system"] = hs_label
        chain.insert(0, f"Ascendant 上升 {asc['sign']} {asc['sign_zh']} {asc['longitude']:.1f}° "
                        f"({hs_label})")
        asc_str = f"・上升 {asc['sign_zh']}"
    else:
        readings["ascendant"] = "unknown — needs birth time + place 需時辰＋出生地"
        asc_str = "・上升未知"

    summary = (
        f"太陽 {sun['sign_zh'] if sun else ''}座{asc_str}"
        f"・月相 {moon}"
        f"・水星{'逆行' if readings.get('mercury_retrograde') == 'yes' else '順行'}"
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"planets": chart_rows, "aspects": astro.aspects_for(d, ORB)},
        reasoning_chain=chain,
        readings=readings,
        summary=summary,
        ascendant=asc,
    )
