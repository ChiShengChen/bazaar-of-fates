"""Jyotiṣa（吠陀占星）— sidereal 命盤 + the active Vimśottarī Mahādaśā."""

from __future__ import annotations

from datetime import date

from fortune import astro_ext as AX
from fortune.birth import BirthInput
from fortune.engines.jyotish import jyotish
from fortune.schemas import Chart

KEY, ZH, EN = "jyotish", "Jyotiṣa（吠陀占星）", "Jyotiṣa · Vedic Astrology"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    natal_chart = jyotish.chart(birth.as_date)
    readings = jyotish.jyotish_readings(birth.as_date, today)
    chain = jyotish.reasoning_chain(birth.as_date, today)
    rows = [{"graha": nm, "sidereal_lon": lon, "rashi": rashi} for (nm, lon, rashi) in natal_chart]

    # Lagna (sidereal ascendant) = tropical ascendant − Lahiri ayanāṃśa; whole-sign rāśi bhāva.
    trop = AX.ascendant_lon(birth)                          # None if 時辰/出生地 missing
    asc_block = None
    if trop is not None:
        ayan = jyotish.ayanamsa(birth.as_date)
        lagna_lon = (trop - ayan) % 360.0
        lagna_idx = int(lagna_lon // 30) % 12
        lagna_rashi = jyotish.RASHI[lagna_idx]
        houses = [{"house": h + 1, "rashi": jyotish.RASHI[(lagna_idx + h) % 12]} for h in range(12)]
        for r in rows:                                     # place each graha in a bhāva (house)
            r["bhava"] = ((int(r["sidereal_lon"] // 30) - lagna_idx) % 12) + 1
        readings["lagna_rashi"] = lagna_rashi
        readings["lagna_deg"] = round(lagna_lon, 2)
        chain.insert(1, f"Lagna (ascendant) = tropical asc {trop:.1f}° − ayanāṃśa {ayan:.1f}° "
                        f"→ {lagna_rashi} {lagna_lon:.1f}°; whole-sign bhāva from the Lagna rāśi.")
        asc_block = {"longitude": round(lagna_lon, 2), "sign": lagna_rashi, "sign_zh": lagna_rashi,
                     "house_system": "whole_sign", "sidereal": True, "houses": houses}
        lagna_str = f"・Lagna {lagna_rashi}"
    else:
        readings["lagna_rashi"] = "unknown — needs birth time + place 需時辰＋出生地"
        lagna_str = ""

    summary = (
        f"月宿 {readings.get('moon_nakshatra', '')}・月 rāśi {readings.get('moon_rashi', '')}{lagna_str}・"
        f"大運 {readings.get('mahadasha_lord', '')}（{readings.get('dasha_nature', '')}）"
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"grahas": rows}, reasoning_chain=chain, readings=readings, summary=summary,
        ascendant=asc_block,
    )
