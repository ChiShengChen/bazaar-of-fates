"""團體合盤 / Group synastry — pairwise cross-aspects among N people.

Casts each person's chart, then scores every pair by its harmonious vs challenging
cross-aspects, yielding a net-score matrix and the standout pairs. Native module.
"""

from __future__ import annotations

import math

from fortune import astro_ext as AX
from fortune import casting
from fortune.birth import BirthInput
from fortune.casting.astrology import _cross_aspects, aspects_within

_HARMONIOUS = {"trine", "sextile", "conjunction"}


def _circular_mean(angles: list[float]) -> float:
    """Mean of angles via unit-vector averaging (correct for wrap-around)."""
    s = sum(math.sin(math.radians(a)) for a in angles)
    c = sum(math.cos(math.radians(a)) for a in angles)
    return math.degrees(math.atan2(s, c)) % 360.0


def _group_composite(charts: list) -> dict:
    """The whole group's composite chart: each planet at the circular mean of all members."""
    bodies = [p["body"] for p in charts[0].chart["planets"]]
    planets = []
    for body in bodies:
        lons = [next(p["ecliptic_lon"] for p in c.chart["planets"] if p["body"] == body) for c in charts]
        lo = round(_circular_mean(lons), 2)
        planets.append({"body": body, "ecliptic_lon": lo, "sign": AX.sign_of(lo), "sign_zh": AX.sign_zh(lo)})
    comp = {"planets": planets, "aspects": aspects_within(planets)}
    ascs = [c.ascendant["longitude"] for c in charts if c.ascendant]
    if len(ascs) == len(charts):                          # only if every member has time + place
        al = round(_circular_mean(ascs), 2)
        comp["ascendant"] = {"longitude": al, "sign": AX.sign_of(al), "sign_zh": AX.sign_zh(al),
                             "house_system": "whole_sign", "houses": AX.whole_sign_houses(al)}
    return comp


def compute(births: list[BirthInput], *, house_system: str = "whole_sign") -> dict:
    charts = [casting.cast("astrology", b, house_system=house_system) for b in births]
    n = len(charts)
    people = [{"name": (b.name or f"P{i + 1}"), "subject": charts[i].subject, "summary": charts[i].summary}
              for i, b in enumerate(births)]

    matrix = [[0] * n for _ in range(n)]
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            cross = _cross_aspects(charts[i].chart["planets"], charts[j].chart["planets"])
            harm = sum(1 for x in cross if x["type"] in _HARMONIOUS)
            chal = len(cross) - harm
            net = harm - chal
            matrix[i][j] = matrix[j][i] = net
            pairs.append({"i": i, "j": j, "a": people[i]["name"], "b": people[j]["name"],
                          "harmonious": harm, "challenging": chal, "net": net, "aspects": cross[:8]})

    best = max(pairs, key=lambda p: p["net"]) if pairs else None
    tense = min(pairs, key=lambda p: p["net"]) if pairs else None
    total_h = sum(p["harmonious"] for p in pairs)
    total_c = sum(p["challenging"] for p in pairs)
    summary = (
        f"{n} people 人 · {len(pairs)} pairs 對 · harmonious {total_h} / challenging {total_c}"
        + (f"・most in-sync {best['a']}↔{best['b']}" if best else "")
    )
    return {"people": people, "pairs": pairs, "matrix": matrix,
            "best_pair": best, "tense_pair": tense, "summary": summary,
            "composite": _group_composite(charts)}
