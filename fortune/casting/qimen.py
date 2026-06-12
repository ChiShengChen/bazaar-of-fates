"""奇門遁甲 — 八門九宮起局 from the birth date."""

from __future__ import annotations

from datetime import date

from fortune.birth import BirthInput
from fortune.engines.qimen import qimen
from fortune.schemas import Chart

KEY, ZH, EN = "qimen", "奇門遁甲", "Qi Men Dun Jia"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    readings = qimen.qimen_readings(birth.as_date)
    chain = qimen.reasoning_chain(birth.as_date, today)
    layout = qimen.gate_layout(birth.as_date)
    summary = (
        f"{readings.get('dun', '')}・{readings.get('ju', '')}・"
        f"值符門 {readings.get('active_gate', readings.get('qimen_regime', ''))}"
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"gates": layout}, reasoning_chain=chain, readings=readings, summary=summary,
    )
