"""八字（四柱）— cast the natal 命盤 from birth date + 時辰.

Adapter over fortune/engines/bazi/bazi.py. Birth hour drives the 時柱 (defaults to
noon → 午時 when unknown); the engine pins 日柱 to the verified 甲子 anchor.
"""

from __future__ import annotations

from fortune.birth import BirthInput
from fortune.engines.bazi import bazi
from fortune.schemas import Chart

KEY, ZH = "bazi", "八字（四柱）"
_ORDER = ("year", "month", "day", "hour")
_ZH = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "時柱"}


def cast(birth: BirthInput) -> Chart:
    d = birth.as_date
    pillars = bazi.four_pillars(d, birth.hour)
    fav = bazi.strength_and_favourable(pillars)

    rows = [{"pillar": _ZH[k], **pillars[k]} for k in _ORDER]
    chain = [
        f"{_ZH[k]}：{pillars[k]['gz']}（{pillars[k]['stem_elem']}{pillars[k]['branch_elem']}・{pillars[k]['zodiac']}）"
        for k in _ORDER
    ]
    chain.append(
        f"日主 {fav['day_master']}（{fav['dm_elem']}）→ {fav['label']}，喜用神：{'、'.join(fav['favourable'])}"
    )
    summary = (
        f"日主 {fav['day_master']}{fav['dm_elem']}・{fav['label']}・"
        f"喜用 {'、'.join(fav['favourable'])}"
    )
    return Chart(
        system=KEY, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"pillars": rows},
        reasoning_chain=chain,
        readings={
            "day_master": fav["day_master"], "dm_elem": fav["dm_elem"],
            "strength": fav["label"], "favourable": fav["favourable"],
            "current_liunian_elem": bazi.liunian_elem(d),
        },
        summary=summary,
    )
