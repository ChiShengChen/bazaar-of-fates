"""四柱推命（日系・京都泰山流）— 十二運星 + 天中殺（空亡）from the natal four pillars.

Pillars come from fortune.bazi_ext (exact 節氣 boundaries, the real birth hour); the
synced engine's `build_chart` hardcodes 巳時 and ±1-day term tables, so only its
十二運星 / 天中殺 / 藏干 tables are reused here.
"""

from __future__ import annotations

from fortune import bazi_ext as X
from fortune.birth import BirthInput
from fortune.engines.suimei import suimei
from fortune.schemas import Chart

KEY, ZH, EN = "suimei", "四柱推命（日）", "Shichū-Suimei · JP Four Pillars"
_ROLE = {"year": "年", "month": "月", "day": "日", "hour": "時"}


def cast(birth: BirthInput) -> Chart:
    p = X.exact_pillars(birth.dt, birth.tz_offset_hours)
    day_stem, day_branch = p["day"]["stem_idx"], p["day"]["branch_idx"]
    void = suimei.tenchusatsu(day_stem, day_branch)
    tenchu = suimei.BRANCHES[void[0]] + suimei.BRANCHES[void[1]]
    pillars = [{
        "role": _ROLE[k], "gz": p[k]["gz"], "stem": p[k]["stem"], "branch": p[k]["branch"],
        "stem_elem": p[k]["stem_elem"], "branch_elem": p[k]["branch_elem"], "zodiac": p[k]["zodiac"],
        "twelve_fortune": suimei.twelve_fortune(day_stem, p[k]["branch_idx"]),
        "hidden": suimei._HIDDEN[p[k]["branch_idx"]],
        "in_void": p[k]["branch_idx"] in void,
    } for k in ("year", "month", "day", "hour")]
    chain = [
        f"{q['role']}柱：{q['gz']}（十二運星 {q['twelve_fortune']}・藏干 {''.join(q['hidden'])}{'・空亡' if q['in_void'] else ''}）"
        for q in pillars
    ]
    if not birth.birth_time:
        chain.insert(0, "時辰未知，時柱以正午（午時）估算 / birth time unknown → noon")
    chain.append(f"日主 {p['day']['stem']}（{p['day']['stem_elem']}）・天中殺（空亡）：{tenchu}")
    summary = f"日主 {p['day']['stem']}{p['day']['stem_elem']}・天中殺 {tenchu}"
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"pillars": pillars},
        reasoning_chain=chain,
        readings={
            "day_master": p["day"]["stem"], "day_master_elem": p["day"]["stem_elem"],
            "pillars": "　".join(f"{q['role']}柱{q['gz']}" for q in pillars),
            "twelve_fortune": "　".join(f"{q['role']}{q['twelve_fortune']}" for q in pillars),
            "tenchusatsu": tenchu,
        },
        summary=summary,
    )
