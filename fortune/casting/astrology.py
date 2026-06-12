"""西洋占星 — cast a natal-style chart from a birth moment.

Adapter over the pure synced engine (fortune/engines/astrology/astro.py). The
engine computes ecliptic longitudes from the calendar; birth time-of-day refines
the Moon. (Ascendant/house cusps need lat/lon and are a planned engine upgrade —
the birthplace is already carried on BirthInput for when it lands.)
"""

from __future__ import annotations

from fortune.birth import BirthInput
from fortune.engines.astrology import astro
from fortune.schemas import Chart

KEY, ZH, EN, ORB = "astrology", "西洋占星", "Western Astrology", 6.0


def cast(birth: BirthInput) -> Chart:
    d = birth.as_date
    chart_rows = [
        {"body": b, "ecliptic_lon": lon, "sign": sign, "sign_zh": astro.sign_zh(lon), "retrograde": retro}
        for (b, lon, sign, retro) in astro.chart_for(d)
    ]
    readings = astro.astro_readings(d, ORB)
    sun = next((r for r in chart_rows if r["body"] == "Sun"), None)
    moon = readings.get("moon_phase", "")
    summary = (
        f"太陽 {sun['sign_zh'] if sun else ''}座"
        f"・月相 {moon}"
        f"・水星{'逆行' if readings.get('mercury_retrograde') == 'yes' else '順行'}"
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"planets": chart_rows, "aspects": astro.aspects_for(d, ORB)},
        reasoning_chain=astro.reasoning_chain(d, ORB),
        readings=readings,
        summary=summary,
    )
