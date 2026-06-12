"""合盤 / Synastry — compare two natal charts by their inter-aspects.

Casts both people's western charts and computes the cross-aspects (person A's planets
against person B's), the classic relationship-astrology overlay. Native module.
"""

from __future__ import annotations

from collections import Counter

from fortune import astro_ext as AX
from fortune import casting
from fortune.birth import BirthInput
from fortune.casting.astrology import _cross_aspects, aspects_within
from fortune.schemas import Chart, Synastry

_HARMONIOUS = {"trine", "sextile", "conjunction"}


def _midpoint(a: float, b: float) -> float:
    """Shorter-arc midpoint of two ecliptic longitudes."""
    d = ((b - a + 540.0) % 360.0) - 180.0
    return (a + d / 2.0) % 360.0


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
    csun = next((p for p in composite["planets"] if p["body"] == "Sun"), None)
    summary = (
        f"{a.label()} ✕ {b.label()}："
        f"{len(cross)} 組星際相位（harmonious {harm} / challenging {len(cross) - harm}）"
        + (f"・composite Sun {csun['sign']} {csun['sign_zh']}" if csun else "")
    )
    return Synastry(a=ca, b=cb, cross_aspects=cross, composite=composite, summary=summary)
