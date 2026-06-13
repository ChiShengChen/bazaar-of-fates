"""西洋占星 — cast a natal chart (planets + ascendant + whole-sign houses) from a birth moment.

Planet longitudes come from the synced engine (date-based). The ascendant and houses
need the birth time AND birthplace, supplied by fortune.astro_ext. With no time/place we
gracefully fall back to the planets-only chart and flag the ascendant as unknown.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fortune import astro_ext as AX
from fortune.birth import BirthInput
from fortune.engines.astrology import astro
from fortune.schemas import Chart

KEY, ZH, EN, ORB = "astrology", "西洋占星", "Western Astrology", 6.0


# how strongly each aspect type reads (used to rank aspects so the wheel/list lead with what matters)
_ASPECT_POTENCY = {"conjunction": 1.0, "opposition": 0.9, "square": 0.85, "trine": 0.8, "sextile": 0.6}


def _importance(aspect_type: str, orb: float) -> float:
    return round(_ASPECT_POTENCY.get(aspect_type, 0.5) * (1.0 - 0.5 * orb / ORB), 3)


def _cross_aspects(natal: list[dict], transit: list[dict], orb: float = ORB) -> list[dict]:
    """Aspects between two planet sets (natal × transit, or synastry A × B), ranked by importance."""
    out: list[dict] = []
    for n in natal:
        for t in transit:
            sep = astro._separation(n["ecliptic_lon"], t["ecliptic_lon"])
            for name, ang in astro._ASPECTS.items():
                o = abs(sep - ang)
                if o <= orb:
                    out.append({"a": n["body"], "b": t["body"], "type": name,
                                "orb": round(o, 1), "importance": _importance(name, o)})
                    break
    out.sort(key=lambda x: x["importance"], reverse=True)
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


def _return_highlights(rows: list[dict], houses: list[dict] | None,
                       natal_asc_lon: float | None, kind: str) -> list[str]:
    """Year/month-ahead key points for a Solar/Lunar Return chart: its ascendant,
    Sun/Moon house, angular planets, and which natal house the return ascendant lands in."""
    if not houses:
        return []
    by = {p["body"]: p for p in rows}
    asc_lon = houses[0]["longitude"]
    hl = [f"{kind} ascendant 上升 {AX.sign_of(asc_lon)} {AX.sign_zh(asc_lon)}"]
    for b in ("Sun", "Moon"):
        if b in by:
            h = AX.house_of_cusps(by[b]["ecliptic_lon"], houses)
            hl.append(f"{kind} {b} in house 宮 {h} ({by[b]['sign']})")
    angular = [f"{p['body']}(H{AX.house_of_cusps(p['ecliptic_lon'], houses)})"
               for p in rows if AX.house_of_cusps(p["ecliptic_lon"], houses) in _ANGULAR]
    if angular:
        hl.append(f"{kind} angular planets 四正: " + ", ".join(angular))
    if natal_asc_lon is not None:
        hl.append(f"{kind} ascendant in natal house 落本命宮 {AX.house_of(asc_lon, natal_asc_lon)}")
    return hl


def _find_solar_return(year: int, month: int, day: int, natal_sun: float) -> datetime:
    """UT moment in `year` when the transiting Sun returns to the natal Sun longitude
    (the Solar Return), found near the birthday by hourly scan + bisection."""
    def sun(dt: datetime) -> float:
        return {p["body"]: p["ecliptic_lon"] for p in AX.planets_at(dt)}["Sun"]
    try:
        start = datetime(year, month, day) - timedelta(days=2)
    except ValueError:                                        # Feb 29 etc.
        start = datetime(year, month, 28) - timedelta(days=2)
    prev, pv = start, _signed_arc(sun(start) - natal_sun)
    for h in range(1, 5 * 24 + 1):
        t = start + timedelta(hours=h)
        cur = _signed_arc(sun(t) - natal_sun)
        if pv == 0.0 or pv * cur < 0:
            lo, hi = prev, t
            for _ in range(22):
                mid = lo + (hi - lo) / 2
                if _signed_arc(sun(mid) - natal_sun) * pv <= 0:
                    hi = mid
                else:
                    lo = mid
            return lo
        prev, pv = t, cur
    return start + timedelta(days=2)


def _find_lunar_return(target: date, natal_moon: float) -> datetime:
    """UT moment nearest `target` when the transiting Moon returns to the natal Moon
    longitude (≈ every 27.3 days) — the Lunar Return for that month."""
    def moon(dt: datetime) -> float:
        return astro._lon(astro.ephem.Moon, dt)
    anchor = datetime(target.year, target.month, target.day)
    start = anchor - timedelta(days=16)
    prev, pv = start, _signed_arc(moon(start) - natal_moon)
    best = None
    for h in range(2, 33 * 24 + 1, 2):                        # ~33 days in 2-hour steps
        t = start + timedelta(hours=h)
        cur = _signed_arc(moon(t) - natal_moon)
        # real conjunction only — both near 0 (skip the ±180° opposition discontinuity)
        if (pv == 0.0 or pv * cur < 0) and abs(pv) < 90.0 and abs(cur) < 90.0:
            lo, hi = prev, t
            for _ in range(20):
                mid = lo + (hi - lo) / 2
                if _signed_arc(moon(mid) - natal_moon) * pv <= 0:
                    hi = mid
                else:
                    lo = mid
            if best is None or abs((lo - anchor).total_seconds()) < abs((best - anchor).total_seconds()):
                best = lo
        prev, pv = t, cur
    return best or anchor


def _age_for_arc(birth: BirthInput, natal_sun: float, arc_needed: float) -> float:
    """Age (years) at which the solar arc reaches `arc_needed`° (≈ Newton; arc ≈ 1°/yr)."""
    birth_ut = birth.dt - timedelta(hours=birth.tz_offset_hours)
    age = arc_needed
    for _ in range(4):
        sun = {p["body"]: p["ecliptic_lon"] for p in AX.planets_at(birth_ut + timedelta(days=age))}["Sun"]
        err = _signed_arc(arc_needed - (sun - natal_sun) % 360.0)
        age += err                                            # d(arc)/d(age) ≈ 1
        if abs(err) < 0.01:
            break
    return age


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


def _exact_target_lon(a_lon: float, b_lon: float, aspect: str) -> float:
    """The longitude the moving body (b) must reach to perfect `aspect` to the fixed
    body (a) — the nearer side for the symmetric aspects."""
    base = astro._ASPECTS[aspect]
    cands = [(a_lon + base) % 360.0] if base in (0.0, 180.0) else [(a_lon + base) % 360.0, (a_lon - base) % 360.0]
    return min(cands, key=lambda c: abs(_signed_arc(b_lon - c)))


def _enrich_aspects(cross: list[dict], a_lons: dict, b_now: dict, b_next: dict,
                    around: date, days_per_step: float) -> None:
    """Add applying/separating + exact date to each cross-aspect, via linear extrapolation
    of the moving body (b_now → b_next is one step; transits 1 day, progressions 1 year)."""
    for x in cross:
        a, b = a_lons[x["a"]], b_now[x["b"]]
        tgt = _exact_target_lon(a, b, x["type"])
        d0 = _signed_arc(b - tgt)
        rate = _signed_arc(b_next[x["b"]] - b)                # deg per step
        x["phase"] = "applying" if abs(d0 + rate) < abs(d0) else "separating"
        x["exact_date"] = ((around + timedelta(days=(-d0 / rate) * days_per_step)).isoformat()
                           if abs(rate) > 1e-6 and abs(-d0 / rate) < 200 else None)


def aspects_within(rows: list[dict], orb: float = ORB) -> list[dict]:
    """Structured aspects within one chart (unique pairs), each with its orb — so the
    wheel can grade line weight by how tight the aspect is."""
    out: list[dict] = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            sep = astro._separation(rows[i]["ecliptic_lon"], rows[j]["ecliptic_lon"])
            for name, ang in astro._ASPECTS.items():
                o = abs(sep - ang)
                if o <= orb:
                    out.append({"a": rows[i]["body"], "b": rows[j]["body"], "type": name,
                                "orb": round(o, 1), "importance": _importance(name, o)})
                    break
    out.sort(key=lambda x: x["importance"], reverse=True)
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
         progress: bool = False, progress_method: str = "secondary",
         solar_return: bool = False, lunar_return: bool = False) -> Chart:
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
        natal_by = {p["body"]: p["ecliptic_lon"] for p in chart_rows}
        t_now = {p["body"]: p["ecliptic_lon"] for p in trows}
        t_next = {b: astro._lon(astro._BODIES[b], td + timedelta(days=1)) for b in t_now}
        _enrich_aspects(tasp, natal_by, t_now, t_next, td, 1.0)
        chart_payload["transits"] = trows
        chart_payload["transit_aspects"] = tasp
        readings["transit_date"] = td.isoformat()
        readings["transit_hits"] = [
            f"natal {x['a']} {x['type']} transit {x['b']} ({x['orb']}°, {x['phase']}"
            + (f", exact {x['exact_date']}" if x.get("exact_date") else "") + ")" for x in tasp] or ["none 無"]
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
            # ages when each natal planet is solar-arc directed (conjunct) to an angle
            if asc:
                mc_l = AX.mc_lon(birth)
                angs = {"ASC": asc["longitude"], "DSC": (asc["longitude"] + 180.0) % 360.0}
                if mc_l is not None:
                    angs.update({"MC": mc_l, "IC": (mc_l + 180.0) % 360.0})
                directions = []
                for p in chart_rows:
                    for an, alon in angs.items():
                        arc_needed = (alon - p["ecliptic_lon"]) % 360.0
                        age_hit = _age_for_arc(birth, natal_sun, arc_needed)
                        if 0.0 <= age_hit <= 100.0:
                            dd = d + timedelta(days=age_hit * 365.2425)
                            directions.append({"planet": p["body"], "angle": an, "age": round(age_hit, 1),
                                               "date": dd.isoformat(), "arc": round(arc_needed, 1)})
                directions.sort(key=lambda x: x["age"])
                chart_payload["solar_arc_directions"] = directions
                readings["solar_arc_to_angles"] = [
                    f"SA {x['planet']} → {x['angle']} at age {x['age']} ({x['date']})" for x in directions[:12]] or ["none 無"]
        else:
            arc = 0.0
            prows = AX.planets_at(prog_ut)
            mlabel = "secondary progressions 二次推運 (1 day = 1 year)"

        pasp = _cross_aspects(chart_rows, prows)
        natal_by = {p["body"]: p["ecliptic_lon"] for p in chart_rows}
        p_now = {p["body"]: p["ecliptic_lon"] for p in prows}
        next_sec = {p["body"]: p["ecliptic_lon"] for p in AX.planets_at(prog_ut + timedelta(days=1))}  # +1 yr
        if method == "solar_arc":
            arc_next = (next_sec["Sun"] - natal_sun) % 360.0
            p_next = {p["body"]: (p["ecliptic_lon"] + arc_next) % 360.0 for p in chart_rows}
        else:
            p_next = next_sec
        _enrich_aspects(pasp, natal_by, p_now, p_next, target, 365.2425)
        chart_payload["progressions"] = prows
        chart_payload["progression_aspects"] = pasp
        chart_payload["progression_method"] = method
        readings["progressed_to"] = target.isoformat()
        readings["progressed_age"] = round(age_years, 1)
        readings["progression_method"] = method
        readings["progression_hits"] = [
            f"progressed {x['b']} {x['type']} natal {x['a']} ({x['orb']}°, {x['phase']}"
            + (f", exact {x['exact_date']}" if x.get("exact_date") else "") + ")" for x in pasp] or ["none 無"]
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

    if solar_return:                                              # 太陽回歸：the year's chart
        yr = (date.fromisoformat(transit_date) if transit_date else date.today()).year
        natal_sun = next(p["ecliptic_lon"] for p in chart_rows if p["body"] == "Sun")
        sr_ut = _find_solar_return(yr, d.month, d.day, natal_sun)
        srows = AX.planets_at(sr_ut)
        sr_local = sr_ut + timedelta(hours=birth.tz_offset_hours)
        bsyn = BirthInput(birth_date=sr_local.date(), birth_time=sr_local.time().replace(microsecond=0),
                          latitude=birth.latitude, longitude=birth.longitude, tz_offset_hours=birth.tz_offset_hours)
        sr_asc = AX.ascendant_block(bsyn, house_system=house_system)
        sasp = _cross_aspects(chart_rows, srows)
        chart_payload["solar_return"] = srows
        chart_payload["solar_return_aspects"] = sasp
        chart_payload["solar_return_houses"] = sr_asc["houses"] if sr_asc else None
        readings["solar_return_year"] = yr
        readings["solar_return_moment"] = sr_ut.isoformat(timespec="minutes") + " UT"
        if sr_asc:
            readings["solar_return_asc"] = f"{sr_asc['sign']} {sr_asc['sign_zh']}"
        readings["solar_return_highlights"] = _return_highlights(
            srows, sr_asc["houses"] if sr_asc else None, asc["longitude"] if asc else None, "SR")
        readings["solar_return_hits"] = [
            f"SR {x['b']} {x['type']} natal {x['a']} ({x['orb']}°)" for x in sasp[:10]] or ["none 無"]
        chain.append(f"Solar Return 太陽回歸 {yr}（{sr_ut.date().isoformat()}）：{len(sasp)} aspect(s) to natal.")

    if lunar_return:                                              # 月亮回歸：the month's chart
        target = date.fromisoformat(transit_date) if transit_date else date.today()
        natal_moon = next(p["ecliptic_lon"] for p in chart_rows if p["body"] == "Moon")
        lr_ut = _find_lunar_return(target, natal_moon)
        lrows = AX.planets_at(lr_ut)
        lr_local = lr_ut + timedelta(hours=birth.tz_offset_hours)
        bsyn = BirthInput(birth_date=lr_local.date(), birth_time=lr_local.time().replace(microsecond=0),
                          latitude=birth.latitude, longitude=birth.longitude, tz_offset_hours=birth.tz_offset_hours)
        lr_asc = AX.ascendant_block(bsyn, house_system=house_system)
        lasp = _cross_aspects(chart_rows, lrows)
        chart_payload["lunar_return"] = lrows
        chart_payload["lunar_return_aspects"] = lasp
        chart_payload["lunar_return_houses"] = lr_asc["houses"] if lr_asc else None
        readings["lunar_return_moment"] = lr_ut.isoformat(timespec="minutes") + " UT"
        if lr_asc:
            readings["lunar_return_asc"] = f"{lr_asc['sign']} {lr_asc['sign_zh']}"
        readings["lunar_return_highlights"] = _return_highlights(
            lrows, lr_asc["houses"] if lr_asc else None, asc["longitude"] if asc else None, "LR")
        readings["lunar_return_hits"] = [
            f"LR {x['b']} {x['type']} natal {x['a']} ({x['orb']}°)" for x in lasp[:10]] or ["none 無"]
        chain.append(f"Lunar Return 月亮回歸（{lr_ut.date().isoformat()}）：{len(lasp)} aspect(s) to natal.")

    summary = (
        f"太陽 {sun['sign_zh'] if sun else ''}座{asc_str}"
        f"・月相 {moon}"
        f"・水星{'逆行' if readings.get('mercury_retrograde') == 'yes' else '順行'}"
        + (f"・行運 {len(chart_payload['transit_aspects'])} 相位" if transits else "")
        + (f"・推運 {len(chart_payload['progression_aspects'])} 相位" if progress else "")
        + (f"・太陽回歸 {readings.get('solar_return_year', '')}" if solar_return else "")
        + ("・月亮回歸" if lunar_return else "")
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart=chart_payload,
        reasoning_chain=chain,
        readings=readings,
        summary=summary,
        ascendant=asc,
    )
