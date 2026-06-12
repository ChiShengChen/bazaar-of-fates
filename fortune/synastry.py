"""合盤 / Synastry — compare two natal charts by their inter-aspects.

Casts both people's western charts and computes the cross-aspects (person A's planets
against person B's), the classic relationship-astrology overlay. Native module.
"""

from __future__ import annotations

from collections import Counter

from fortune import casting
from fortune.birth import BirthInput
from fortune.casting.astrology import _cross_aspects
from fortune.schemas import Synastry

_HARMONIOUS = {"trine", "sextile", "conjunction"}


def compute(a: BirthInput, b: BirthInput, *, house_system: str = "whole_sign") -> Synastry:
    ca = casting.cast("astrology", a, house_system=house_system)
    cb = casting.cast("astrology", b, house_system=house_system)
    cross = _cross_aspects(ca.chart["planets"], cb.chart["planets"])
    by_type = Counter(x["type"] for x in cross)
    harm = sum(v for k, v in by_type.items() if k in _HARMONIOUS)
    summary = (
        f"{a.label()} ✕ {b.label()}："
        f"{len(cross)} 組星際相位（harmonious {harm} / challenging {len(cross) - harm}）"
    )
    return Synastry(a=ca, b=cb, cross_aspects=cross, summary=summary)
