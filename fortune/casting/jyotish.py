"""Jyotiṣa（吠陀占星）— sidereal 命盤 + the active Vimśottarī Mahādaśā.

Positions, nakṣatra and daśā come from fortune.jyotish_ext at the exact birth instant
(true equinox of date − Lahiri ayanāṃśa); the engine's date-only Moon is not used.
"""

from __future__ import annotations

from datetime import date

from fortune import astro_ext as AX
from fortune import jyotish_ext as JX
from fortune.birth import BirthInput
from fortune.engines.jyotish import jyotish
from fortune.schemas import Chart

KEY, ZH, EN = "jyotish", "Jyotiṣa（吠陀占星）", "Jyotiṣa · Vedic Astrology"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    birth_ut = AX.birth_utc(birth)
    rows = JX.sidereal_positions(birth_ut)
    n, frac = JX.natal_nakshatra(birth_ut)
    lord = JX.mahadasha_lord(birth_ut, today)
    ayan = JX.ayanamsa_at(birth_ut)
    moon = next(r for r in rows if r["graha"] == "Moon")
    nature = "benefic" if lord in jyotish.BENEFIC else "malefic"
    readings = {
        "jyotish_regime": "benefic_dasha" if nature == "benefic" else "malefic_dasha",
        "moon_nakshatra": jyotish.NAKSHATRA[n], "moon_rashi": moon["rashi"],
        "mahadasha_lord": lord, "dasha_nature": nature, "ayanamsa_deg": round(ayan, 2),
        "birth_moment_ut": birth_ut.isoformat(timespec="minutes") + " UT"
                           + ("" if birth.birth_time else " (time unknown → noon local 時辰未知以正午計)"),
        "grahas": "、".join(f"{r['graha']} {r['rashi']} {r['sidereal_lon']:.1f}°{' ℞' if r['retrograde'] else ''}" for r in rows),
    }
    chain = [
        f"Birth instant {readings['birth_moment_ut']}: sidereal = tropical (of date) − Lahiri ayanāṃśa ({ayan:.2f}°).",
        f"Natal Moon {moon['sidereal_lon']:.1f}° {moon['rashi']} → nakṣatra {jyotish.NAKSHATRA[n]} ({frac * 100:.0f}% elapsed) "
        f"→ the Vimśottarī sequence starts at its lord {jyotish.DASHA_LORDS[n % 9]}.",
        f"Walking the 120-yr Vimśottarī cycle to {today.isoformat()}: current Mahādaśā lord = {lord} ({nature}).",
    ]

    # Lagna (sidereal ascendant) = tropical ascendant − Lahiri ayanāṃśa; whole-sign rāśi bhāva.
    trop = AX.ascendant_lon(birth)                          # None if 時辰/出生地 missing
    asc_block = None
    if trop is not None:
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
        f"月宿 {readings['moon_nakshatra']}・月 rāśi {readings['moon_rashi']}{lagna_str}・"
        f"大運 {lord}（{nature}）"
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"grahas": rows}, reasoning_chain=chain, readings=readings, summary=summary,
        ascendant=asc_block,
    )
