"""合盤 / Synastry — compare two natal charts by their inter-aspects.

Casts both people's western charts and computes the cross-aspects (person A's planets
against person B's), the classic relationship-astrology overlay. Native module.
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import timedelta

import ephem

from fortune import astro_ext as AX
from fortune import casting
from fortune.birth import BirthInput
from fortune.casting.astrology import _cross_aspects, aspects_within
from fortune.engines.astrology import astro
from fortune.schemas import Chart, Synastry

_HARMONIOUS = {"trine", "sextile", "conjunction"}


def _midpoint(a: float, b: float) -> float:
    """Shorter-arc midpoint of two ecliptic longitudes."""
    d = ((b - a + 540.0) % 360.0) - 180.0
    return (a + d / 2.0) % 360.0


def _has_geometry(p: BirthInput) -> bool:
    return p.birth_time is not None and p.latitude is not None and p.longitude is not None


def _davison(a: BirthInput, b: BirthInput, house_system: str) -> dict | None:
    """Davison time-space midpoint chart: a REAL ephemeris chart cast for the midpoint
    moment (in UT) and the midpoint location of the two births — distinct from the
    composite, which just averages ecliptic longitudes."""
    if not (_has_geometry(a) and _has_geometry(b)):
        return None
    ua = a.dt - timedelta(hours=a.tz_offset_hours)        # naive UT
    ub = b.dt - timedelta(hours=b.tz_offset_hours)
    mid = ua + (ub - ua) / 2
    lat = (a.latitude + b.latitude) / 2.0
    dlon = ((b.longitude - a.longitude + 540.0) % 360.0) - 180.0
    lon = ((a.longitude + dlon / 2.0 + 180.0) % 360.0) - 180.0

    planets = []
    for name, cls in astro._BODIES.items():               # real positions at the midpoint instant
        body = cls()
        body.compute(ephem.Date(mid))
        lo = math.degrees(ephem.Ecliptic(body).lon) % 360.0
        retro = name not in ("Sun", "Moon") and astro.is_retrograde(cls, mid.date())
        planets.append({"body": name, "ecliptic_lon": round(lo, 2),
                        "sign": AX.sign_of(lo), "sign_zh": AX.sign_zh(lo), "retrograde": retro})

    bsyn = BirthInput(birth_date=mid.date(), birth_time=mid.time().replace(microsecond=0),
                      latitude=lat, longitude=lon, tz_offset_hours=0.0)
    return {
        "datetime": mid.isoformat(timespec="minutes"),
        "latitude": round(lat, 2), "longitude": round(lon, 2),
        "planets": planets, "aspects": aspects_within(planets),
        "ascendant": AX.ascendant_block(bsyn, house_system=house_system),
    }


def _composite(ca: Chart, cb: Chart) -> dict:
    """Composite (midpoint) chart: each planet at the midpoint of the two natal positions."""
    pb = {p["body"]: p for p in cb.chart["planets"]}
    planets = []
    for p in ca.chart["planets"]:
        if p["body"] in pb:
            lon = round(_midpoint(p["ecliptic_lon"], pb[p["body"]]["ecliptic_lon"]), 2)
            planets.append({"body": p["body"], "ecliptic_lon": lon,
                            "sign": AX.sign_of(lon), "sign_zh": AX.sign_zh(lon)})
    comp = {"planets": planets, "aspects": aspects_within(planets)}
    if ca.ascendant and cb.ascendant:
        al = round(_midpoint(ca.ascendant["longitude"], cb.ascendant["longitude"]), 2)
        comp["ascendant"] = {"longitude": al, "sign": AX.sign_of(al), "sign_zh": AX.sign_zh(al),
                             "house_system": "whole_sign", "houses": AX.whole_sign_houses(al)}
    return comp


def compute(a: BirthInput, b: BirthInput, *, house_system: str = "whole_sign") -> Synastry:
    ca = casting.cast("astrology", a, house_system=house_system)
    cb = casting.cast("astrology", b, house_system=house_system)
    cross = _cross_aspects(ca.chart["planets"], cb.chart["planets"])
    by_type = Counter(x["type"] for x in cross)
    harm = sum(v for k, v in by_type.items() if k in _HARMONIOUS)
    composite = _composite(ca, cb)
    davison = _davison(a, b, house_system)
    csun = next((p for p in composite["planets"] if p["body"] == "Sun"), None)
    summary = (
        f"{a.label()} ✕ {b.label()}："
        f"{len(cross)} 組星際相位（harmonious {harm} / challenging {len(cross) - harm}）"
        + (f"・composite Sun {csun['sign']} {csun['sign_zh']}" if csun else "")
    )
    return Synastry(a=ca, b=cb, cross_aspects=cross, composite=composite, davison=davison, summary=summary)
