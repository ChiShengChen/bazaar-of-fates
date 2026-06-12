"""紫微斗數 — cast the natal 命盤 and read this year's 流年四化.

Note: the synced engine's build_natal(date) currently defaults the birth hour, so
命宮 is hour-insensitive for now; passing 時辰 through is a planned engine upgrade.
"""

from __future__ import annotations

from datetime import date

from fortune.birth import BirthInput
from fortune.engines.ziwei import ziwei
from fortune.schemas import Chart

KEY, ZH = "ziwei", "紫微斗數"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    natal = ziwei.build_natal(birth.as_date)
    readings = ziwei.ziwei_readings(natal, today)
    chain = ziwei.reasoning_chain(natal, today)
    summary = (
        f"命主星 {readings.get('soul_star', '?')}・身主星 {readings.get('body_star', '?')}・"
        f"{readings.get('five_elements_class', '')}・流年 {readings.get('ziwei_regime', '')}"
    )
    return Chart(
        system=KEY, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"palaces": natal.get("palaces", []), "star_palace": natal.get("star_palace", {})},
        reasoning_chain=chain, readings=readings, summary=summary,
    )
