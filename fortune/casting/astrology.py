"""西洋占星 — cast a natal chart (planets + ascendant + whole-sign houses) from a birth moment.

Planet longitudes come from the synced engine (date-based). The ascendant and houses
need the birth time AND birthplace, supplied by fortune.astro_ext. With no time/place we
gracefully fall back to the planets-only chart and flag the ascendant as unknown.
"""

from __future__ import annotations

from datetime import date

from fortune import astro_ext as AX
from fortune.birth import BirthInput
from fortune.engines.astrology import astro
from fortune.schemas import Chart

KEY, ZH, EN, ORB = "astrology", "西洋占星", "Western Astrology", 6.0


def _cross_aspects(natal: list[dict], transit: list[dict], orb: float = ORB) -> list[dict]:
    """Aspects between two planet sets (natal × transit, or synastry A × B)."""
    out: list[dict] = []
    for n in natal:
        for t in transit:
            sep = astro._separation(n["ecliptic_lon"], t["ecliptic_lon"])
            for name, ang in astro._ASPECTS.items():
                if abs(sep - ang) <= orb:
                    out.append({"a": n["body"], "b": t["body"], "type": name, "orb": round(abs(sep - ang), 1)})
                    break
    return out


def aspects_within(rows: list[dict], orb: float = ORB) -> list[dict]:
    """Structured aspects within one chart (unique pairs), each with its orb — so the
    wheel can grade line weight by how tight the aspect is."""
    out: list[dict] = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            sep = astro._separation(rows[i]["ecliptic_lon"], rows[j]["ecliptic_lon"])
            for name, ang in astro._ASPECTS.items():
                if abs(sep - ang) <= orb:
                    out.append({"a": rows[i]["body"], "b": rows[j]["body"], "type": name,
                                "orb": round(abs(sep - ang), 1)})
                    break
    return out

# traditional (7-body) rulerships — the engine tracks exactly these classical bodies
_RULER = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}
_ANGULAR = {1, 4, 7, 10}
_SLOW = {"Jupiter", "Saturn"}                     # the slow movers whose angle-hits are "major"
_HARD = {"conjunction": 0.0, "square": 90.0, "opposition": 180.0}
_ANGLE_ORB = 3.0


def cast(birth: BirthInput, *, house_system: str = "whole_sign",
         transits: bool = False, transit_date: str | None = None) -> Chart:
    d = birth.as_date
    chart_rows = [
        {"body": b, "ecliptic_lon": lon, "sign": sign, "sign_zh": astro.sign_zh(lon), "retrograde": retro}
        for (b, lon, sign, retro) in astro.chart_for(d)
    ]
    readings = astro.astro_readings(d, ORB)
    chain = astro.reasoning_chain(d, ORB)
    sun = next((r for r in chart_rows if r["body"] == "Sun"), None)
    moon = readings.get("moon_phase", "")

    aspects = astro.aspects_for(d, ORB)
    readings["aspects"] = aspects                                  # surface aspects to the 解讀
    asc = AX.ascendant_block(birth, house_system=house_system)    # None if 時辰/出生地 missing
    if asc:
        cusps = asc["houses"]
        place = (lambda lon: AX.house_of(lon, asc["longitude"])) if asc["house_system"] == "whole_sign" \
            else (lambda lon: AX.house_of_cusps(lon, cusps))      # cusp-based for equal + quadrant systems
        for r in chart_rows:
            r["house"] = place(r["ecliptic_lon"])
        hs_label = {"placidus": "Placidus 不等宮", "koch": "Koch 不等宮",
                    "regiomontanus": "Regiomontanus 不等宮", "campanus": "Campanus 不等宮",
                    "equal": "Equal 等宮", "whole_sign": "whole-sign 整星座"}.get(
                        asc["house_system"], asc["house_system"])
        readings["ascendant"] = f"{asc['sign']} {asc['sign_zh']} {asc['longitude']:.1f}°"
        readings["house_system"] = hs_label

        # deeper structure: chart ruler (命主星) + angular planets
        ruler = _RULER.get(asc["sign"])
        rr = next((r for r in chart_rows if r["body"] == ruler), None)
        if rr:
            readings["chart_ruler"] = f"{ruler}（命主星）in {rr['sign']} {rr['sign_zh']}, house {rr.get('house', '?')}"
        angular = [f"{r['body']} ({r['sign']}, H{r['house']})" for r in chart_rows if r.get("house") in _ANGULAR]
        readings["angular_planets"] = angular or ["none 無"]
        chain.insert(0, f"Ascendant 上升 {asc['sign']} {asc['sign_zh']} {asc['longitude']:.1f}° ({hs_label})"
                        + (f"; chart ruler 命主星 {ruler}" if ruler else ""))
        asc_str = f"・上升 {asc['sign_zh']}"
    else:
        readings["ascendant"] = "unknown — needs birth time + place 需時辰＋出生地"
        asc_str = "・上升未知"

    chart_payload = {"planets": chart_rows, "aspects": aspects, "aspects_detail": aspects_within(chart_rows)}
    if transits:                                                  # 流年行運：overlay the sky on a date
        td = date.fromisoformat(transit_date) if transit_date else date.today()
        trows = [
            {"body": b, "ecliptic_lon": lon, "sign": sign, "sign_zh": astro.sign_zh(lon), "retrograde": retro}
            for (b, lon, sign, retro) in astro.chart_for(td)
        ]
        tasp = _cross_aspects(chart_rows, trows)
        chart_payload["transits"] = trows
        chart_payload["transit_aspects"] = tasp
        readings["transit_date"] = td.isoformat()
        readings["transit_hits"] = [f"natal {x['a']} {x['type']} transit {x['b']} ({x['orb']}°)" for x in tasp] or ["none 無"]
        chain.append(f"Transits 行運 ({td.isoformat()}): {len(tasp)} aspect(s) to the natal chart.")

        # major transits: a slow planet (Jupiter/Saturn) hitting a natal angle (ASC/MC/DSC/IC)
        if asc:
            al = asc["longitude"]
            mc = AX.mc_lon(birth)
            angles = {"ASC": al, "DSC": (al + 180.0) % 360.0}
            if mc is not None:
                angles.update({"MC": mc, "IC": (mc + 180.0) % 360.0})
            major = []
            for t in trows:
                if t["body"] not in _SLOW:
                    continue
                for an, alon in angles.items():
                    sep = astro._separation(t["ecliptic_lon"], alon)
                    for asp, exact in _HARD.items():
                        if abs(sep - exact) <= _ANGLE_ORB:
                            major.append({"transit": t["body"], "angle": an, "type": asp,
                                          "angle_lon": round(alon, 2), "orb": round(abs(sep - exact), 1)})
                            break
            chart_payload["major_transits"] = major
            readings["major_transits"] = [
                f"⚠ transit {m['transit']} {m['type']} natal {m['angle']} ({m['orb']}°)" for m in major
            ] or ["none 無"]

    summary = (
        f"太陽 {sun['sign_zh'] if sun else ''}座{asc_str}"
        f"・月相 {moon}"
        f"・水星{'逆行' if readings.get('mercury_retrograde') == 'yes' else '順行'}"
        + (f"・行運 {len(chart_payload['transit_aspects'])} 相位" if transits else "")
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart=chart_payload,
        reasoning_chain=chain,
        readings=readings,
        summary=summary,
        ascendant=asc,
    )
