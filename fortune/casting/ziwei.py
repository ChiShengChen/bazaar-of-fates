"""紫微斗數 — cast the natal 命盤 (命宮 from the real birth 時辰) and read 流年四化.

命宮/身宮/五行局/星位 are cast from the birth hour via fortune.ziwei_ext (the synced
core hardcodes 巳時 for stocks). With no birth_time we fall back to 午時 (noon).
"""

from __future__ import annotations

from datetime import date

from fortune import ziwei_ext
from fortune.birth import BirthInput
from fortune.engines.ziwei import ziwei
from fortune.schemas import Chart

KEY, ZH, EN = "ziwei", "紫微斗數", "Zi Wei Dou Shu · Purple Star"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    hb = ziwei_ext.hour_branch_of(birth.hour)               # 子0…亥11 from 生時
    natal = ziwei_ext.build_natal(birth.as_date, hb)
    readings = ziwei.ziwei_readings(natal, today)
    readings["life_palace_branch"] = natal["life_branch"]
    readings["body_palace"] = next((p["name"] for p in natal["palaces"] if p["is_body"]), "")
    readings["hour_branch"] = natal["hour_branch"]
    chain = ziwei.reasoning_chain(natal, today)
    chain.insert(0, f"生時 {natal['hour_branch']}時 → 命宮在 {natal['life_branch']}宮")
    summary = (
        f"命宮 {natal['life_branch']}・命主星 {readings.get('soul_star', '?')}・"
        f"{readings.get('five_elements_class', '')}・流年 {readings.get('ziwei_regime', '')}"
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"palaces": natal.get("palaces", []), "star_palace": natal.get("star_palace", {})},
        reasoning_chain=chain, readings=readings, summary=summary,
    )
