"""太乙神數 — 太乙九宮起算 from the birth date."""

from __future__ import annotations

from datetime import date

from fortune.birth import BirthInput
from fortune.engines.taiyi import taiyi
from fortune.schemas import Chart

KEY, ZH = "taiyi", "太乙神數"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    readings = taiyi.taiyi_readings(birth.as_date)
    chain = taiyi.reasoning_chain(birth.as_date, today)
    summary = (
        f"太乙入 {readings.get('taiyi_palace', '')}・"
        f"{readings.get('taiyi_regime', readings.get('host_guest', ''))}"
    )
    return Chart(
        system=KEY, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"palace": readings.get("taiyi_palace", "")},
        reasoning_chain=chain, readings=readings, summary=summary,
    )
