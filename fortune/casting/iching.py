"""梅花易數 — time-cast a hexagram from the birth date (時間起卦)."""

from __future__ import annotations

from fortune.birth import BirthInput
from fortune.engines.iching import iching
from fortune.schemas import Chart

KEY, ZH = "iching", "梅花易數"


def cast(birth: BirthInput) -> Chart:
    div = iching.divine(birth.as_date)
    chain = [
        f"本卦：{div['ben_name']}（第 {div['ben_num']} 卦）",
        f"互卦：{div['hu_name']}　變卦：{div['bian_name']}（動爻 第 {div['moving']} 爻）",
        f"體用：體={div['ti']}（{div['ti_wuxing']}）・用={div['yong']}（{div['yong_wuxing']}）",
        f"五行：{div['relation']} → {div['verdict']}",
    ]
    summary = f"{div['ben_name']}・{div['relation']}・{div['verdict']}"
    return Chart(
        system=KEY, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"hexagram": div, "diagram": iching.line_diagram(div)},
        reasoning_chain=chain,
        readings={
            "本卦": div["ben_name"], "互卦": div["hu_name"], "變卦": div["bian_name"],
            "體用關係": div["relation"], "斷": div["verdict"], "auspicious": div["auspicious"],
        },
        summary=summary,
    )
