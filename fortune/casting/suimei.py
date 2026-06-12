"""四柱推命（日系・京都泰山流）— 十二運星 + 天中殺（空亡）from the natal four pillars."""

from __future__ import annotations

from fortune.birth import BirthInput
from fortune.engines.suimei import suimei
from fortune.schemas import Chart

KEY, ZH, EN = "suimei", "四柱推命（日）", "Shichū-Suimei · JP Four Pillars"


def cast(birth: BirthInput) -> Chart:
    ch = suimei.build_chart(birth.as_date)
    chain = [
        f"{p['role']}柱：{p['gz']}（十二運星 {p['twelve_fortune']}・藏干 {''.join(p['hidden'])}）"
        for p in ch["pillars"]
    ]
    chain.append(
        f"日主 {ch['day_master']}（{ch['day_master_elem']}）・天中殺（空亡）：{ch['tenchusatsu']}"
    )
    summary = f"日主 {ch['day_master']}{ch['day_master_elem']}・天中殺 {ch['tenchusatsu']}"
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"pillars": ch["pillars"]},
        reasoning_chain=chain,
        readings={
            "day_master": ch["day_master"], "day_master_elem": ch["day_master_elem"],
            "tenchusatsu": ch["tenchusatsu"],
        },
        summary=summary,
    )
