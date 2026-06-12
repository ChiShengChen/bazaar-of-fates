"""西洋占星 — cast a natal chart (planets + ascendant + whole-sign houses) from a birth moment.

Planet longitudes come from the synced engine (date-based). The ascendant and houses
need the birth time AND birthplace, supplied by fortune.astro_ext. With no time/place we
gracefully fall back to the planets-only chart and flag the ascendant as unknown.
"""

from __future__ import annotations

from datetime import date, timedelta

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


def _signed_arc(x: float) -> float:
    return ((x + 180.0) % 360.0) - 180.0


def _exact_date(body_cls, target_lon: float, around: date, window: int = 500) -> str | None:
    """Date when `body` crosses `target_lon` exactly (orb 0), nearest to `around`.
    Scans ±window days for a sign change of the signed arc, then refines — handling
    retrograde, where there can be several crossings."""
    def g(off: int) -> float:
        return _signed_arc(astro._lon(body_cls, around + timedelta(days=off)) - target_lon)

    prev_off, prev = -window, g(-window)
    best = None
    for off in range(-window + 4, window + 1, 4):
        cur = g(off)
        if prev == 0.0:
            cross = prev_off
        elif prev * cur < 0:
            cross = prev_off + (off - prev_off) * (prev / (prev - cur))   # linear interp
        else:
            prev_off, prev = off, cur
            continue
        if best is None or abs(cross) < abs(best):
            best = cross
        prev_off, prev = off, cur
    if best is None:
        return None
    return (around + timedelta(days=round(best))).isoformat()


def _prog_dt_utc(birth: BirthInput, target: date):
    """Progressed UT datetime for a target date under 1 day = 1 year, and the age."""
    age = max(0.0, (target - birth.as_date).days / 365.2425)
    return (birth.dt - timedelta(hours=birth.tz_offset_hours)) + timedelta(days=age), age


def _prog_lon(birth: BirthInput, body: str, target: date, method: str,
              natal_lon: float, natal_sun: float) -> float:
    dt, _ = _prog_dt_utc(birth, target)
    rows = {p["body"]: p["ecliptic_lon"] for p in AX.planets_at(dt)}
    if method == "solar_arc":
        return (natal_lon + (rows["Sun"] - natal_sun) % 360.0) % 360.0
    return rows[body]


def _next_sign_ingress(birth: BirthInput, body: str, target: date, method: str,
                       natal_lon: float, natal_sun: float, max_years: float, step_days: int):
    """Date the progressed/directed `body` next crosses a sign boundary, scanning forward."""
    def lon(t: date) -> float:
        return _prog_lon(birth, body, t, method, natal_lon, natal_sun)
    s0 = int(lon(target) // 30)
    t, end = target, target + timedelta(days=int(max_years * 365.25))
    while t < end:
        t2 = t + timedelta(days=step_days)
        if int(lon(t2) // 30) != s0:
            lo, hi = t, t2
            while (hi - lo).days > 1:
                mid = lo + (hi - lo) / 2
                if int(lon(mid) // 30) != s0:
                    hi = mid
                else:
                    lo = mid
            return hi.isoformat(), AX.sign_of(lon(hi))
        t = t2
    return None, None


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
# how strongly each angle-contact reads — a conjunction on an angle outweighs a square
_ASPECT_WEIGHT = {"conjunction": 1.0, "opposition": 0.8, "square": 0.6}


def cast(birth: BirthInput, *, house_system: str = "whole_sign",
         transits: bool = False, transit_date: str | None = None,
         progress: bool = False, progress_method: str = "secondary") -> Chart:
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
                        orb = abs(sep - exact)
                        if orb <= _ANGLE_ORB:
                            # weight 0..1: aspect potency × tightness (tight orb → stronger)
                            weight = round(_ASPECT_WEIGHT[asp] * (1.0 - 0.45 * orb / _ANGLE_ORB), 2)
                            cls = astro._BODIES[t["body"]]
                            # applying vs separating: is tomorrow's orb tighter? (handles retrograde)
                            l1 = astro._lon(cls, td + timedelta(days=1))
                            orb1 = abs(astro._separation(l1, alon) - exact)
                            phase = "applying" if orb1 < orb else "separating"
                            # exact-aspect longitude the planet must reach → date it perfects
                            if asp == "conjunction":
                                target = alon
                            elif asp == "opposition":
                                target = (alon + 180.0) % 360.0
                            else:                                          # square: nearer of ±90°
                                c1, c2 = (alon + 90.0) % 360.0, (alon - 90.0) % 360.0
                                target = c1 if abs(_signed_arc(t["ecliptic_lon"] - c1)) <= abs(_signed_arc(t["ecliptic_lon"] - c2)) else c2
                            major.append({"transit": t["body"], "angle": an, "type": asp,
                                          "angle_lon": round(alon, 2), "orb": round(orb, 1),
                                          "weight": weight, "phase": phase,
                                          "exact_date": _exact_date(cls, target, td)})
                            break
            major.sort(key=lambda m: m["weight"], reverse=True)
            chart_payload["major_transits"] = major
            readings["major_transits"] = [
                f"⚠ transit {m['transit']} {m['type']} natal {m['angle']} ({m['orb']}°, {m['phase']}"
                + (f", exact {m['exact_date']}" if m.get("exact_date") else "") + ")" for m in major
            ] or ["none 無"]

    if progress:                                                  # 二次推運 / 太陽弧
        method = progress_method if progress_method in ("secondary", "solar_arc") else "secondary"
        target = date.fromisoformat(transit_date) if transit_date else date.today()
        prog_ut, age_years = _prog_dt_utc(birth, target)
        natal_sun = next(p["ecliptic_lon"] for p in chart_rows if p["body"] == "Sun")

        if method == "solar_arc":                                 # rigid rotation by the Sun's arc
            sec_sun = {p["body"]: p["ecliptic_lon"] for p in AX.planets_at(prog_ut)}["Sun"]
            arc = (sec_sun - natal_sun) % 360.0
            prows = [{"body": p["body"], "ecliptic_lon": round((p["ecliptic_lon"] + arc) % 360.0, 2),
                      "sign": AX.sign_of(p["ecliptic_lon"] + arc), "sign_zh": AX.sign_zh(p["ecliptic_lon"] + arc),
                      "retrograde": p.get("retrograde", False)} for p in chart_rows]
            readings["solar_arc_deg"] = round(arc, 2)
            mlabel = f"solar-arc directions 太陽弧 (arc {arc:.1f}°)"
        else:
            arc = 0.0
            prows = AX.planets_at(prog_ut)
            mlabel = "secondary progressions 二次推運 (1 day = 1 year)"

        pasp = _cross_aspects(chart_rows, prows)
        chart_payload["progressions"] = prows
        chart_payload["progression_aspects"] = pasp
        chart_payload["progression_method"] = method
        readings["progressed_to"] = target.isoformat()
        readings["progressed_age"] = round(age_years, 1)
        readings["progression_method"] = method
        readings["progression_hits"] = [
            f"progressed {x['b']} {x['type']} natal {x['a']} ({x['orb']}°)" for x in pasp] or ["none 無"]
        chain.append(f"{mlabel} (age {age_years:.0f}): {len(pasp)} aspect(s) to natal.")

        # progressed houses for the outer ring
        if asc:
            if method == "solar_arc":
                chart_payload["progression_houses"] = [
                    {"house": c["house"], "longitude": round((c["longitude"] + arc) % 360.0, 2),
                     "sign": AX.sign_of(c["longitude"] + arc), "sign_zh": AX.sign_zh(c["longitude"] + arc)}
                    for c in asc["houses"]]
            else:
                prog_local = birth.dt + timedelta(days=age_years)
                bsyn = BirthInput(birth_date=prog_local.date(), birth_time=prog_local.time().replace(microsecond=0),
                                  latitude=birth.latitude, longitude=birth.longitude, tz_offset_hours=birth.tz_offset_hours)
                pa = AX.ascendant_block(bsyn, house_system=house_system)
                chart_payload["progression_houses"] = pa["houses"] if pa else None

        # major progressions: progressed Moon sign/house + next ingress; progressed Sun sign change
        natal_moon = next(p["ecliptic_lon"] for p in chart_rows if p["body"] == "Moon")
        pmoon = next(p for p in prows if p["body"] == "Moon")
        psun = next(p for p in prows if p["body"] == "Sun")
        mp = [{"event": "progressed Moon in sign 推運月入", "sign": pmoon["sign"], "sign_zh": pmoon["sign_zh"]}]
        if asc:
            mp.append({"event": "progressed Moon in natal house 推運月入本命宮",
                       "house": AX.house_of(pmoon["ecliptic_lon"], asc["longitude"])})
        ndate, nsign = _next_sign_ingress(birth, "Moon", target, method, natal_moon, natal_sun, 3.0, 20)
        if ndate:
            mp.append({"event": "progressed Moon → next sign 推運月換座", "date": ndate, "sign": nsign})
        if psun["sign"] != AX.sign_of(natal_sun):
            mp.append({"event": "progressed Sun changed sign 推運日已換座",
                       "from": AX.sign_of(natal_sun), "to": psun["sign"]})
        chart_payload["major_progressions"] = mp
        readings["major_progressions"] = [
            (m["event"] + "：" + (m.get("sign") or m.get("to") or str(m.get("house", "")))
             + (f"（{m['date']}）" if m.get("date") else "")) for m in mp]

    summary = (
        f"太陽 {sun['sign_zh'] if sun else ''}座{asc_str}"
        f"・月相 {moon}"
        f"・水星{'逆行' if readings.get('mercury_retrograde') == 'yes' else '順行'}"
        + (f"・行運 {len(chart_payload['transit_aspects'])} 相位" if transits else "")
        + (f"・推運 {len(chart_payload['progression_aspects'])} 相位" if progress else "")
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart=chart_payload,
        reasoning_chain=chain,
        readings=readings,
        summary=summary,
        ascendant=asc,
    )
