"""鐵板神數 — 起命數 from the birth moment, with this year's 流年數 verdict.

The engine is an honest stand-in (太玄數 起數; the real 條文 system is proprietary).
Pillars come from fortune.bazi_ext so the real birth hour and exact 節氣 are used
(the engine's own `ming_number` hardcodes 巳時).
"""

from __future__ import annotations

from datetime import date, datetime

from fortune import bazi_ext as X
from fortune.birth import BirthInput
from fortune.engines.tieban import tieban
from fortune.schemas import Chart

KEY, ZH, EN = "tieban", "鐵板神數", "Tie Ban Shen Shu · Iron Plate"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    p = X.exact_pillars(X.cast_dt(birth), birth.tz_offset_hours)
    nums = {k: tieban._gz_number(p[k]["stem_idx"], p[k]["branch_idx"]) for k in ("year", "month", "day", "hour")}
    ming = sum(nums.values())
    ly = X.exact_pillars(datetime(today.year, today.month, today.day, 12), birth.tz_offset_hours)["year"]
    vn = ming + tieban._gz_number(ly["stem_idx"], ly["branch_idx"])
    v = tieban.verdict(vn)
    readings = {
        "tieban_regime": {"吉": "auspicious", "平": "neutral", "凶": "inauspicious"}[v],
        "ming_number": float(ming), "liunian_year": f"{today.year} {ly['gz']}",
        "liunian_verse_no": float(vn), "liunian_verdict": v,
        "liunian_gua": "乾兌離震巽坎艮坤"[vn % 8],
    }
    gz = "、".join(f"{p[k]['gz']}({nums[k]})" for k in ("year", "month", "day", "hour"))
    chain = [
        f"起數：四柱 {gz}，各取太玄數（甲己9 乙庚8 丙辛7 丁壬6 戊癸5；子午9 丑未8 寅申7 卯酉6 辰戌5 巳亥4）"
        + ("；時辰未知以正午計" if not birth.birth_time else "") + "。",
        f"命數（太極數）＝四柱太玄數之和＝{ming}。",
        f"流年起例：命數 + 流年 {ly['gz']} 太玄數 ＝ 條文 #{vn}。",
        f"斷例：條文 #{vn} → 「{v}」（編號 mod 3）；流年卦象 {readings['liunian_gua']}。",
    ]
    summary = f"命數 {ming}・流年 {ly['gz']} {readings['tieban_regime']}"
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"ming_number": ming, "pillars": [p[k] for k in ("year", "month", "day", "hour")]},
        reasoning_chain=chain, readings=readings, summary=summary,
    )
