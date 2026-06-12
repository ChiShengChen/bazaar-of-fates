"""鐵板神數 — 起命數 from the birth date, with this year's 流年數 verdict."""

from __future__ import annotations

from datetime import date

from fortune.birth import BirthInput
from fortune.engines.tieban import tieban
from fortune.schemas import Chart

KEY, ZH = "tieban", "鐵板神數"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    ming = tieban.ming_number(birth.as_date)
    readings = tieban.tieban_readings(birth.as_date, ming, today)
    chain = tieban.reasoning_chain(birth.as_date, ming, today)
    summary = f"命數 {ming}・流年 {readings.get('verse_fortune', readings.get('tieban_regime', ''))}"
    return Chart(
        system=KEY, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"ming_number": ming}, reasoning_chain=chain, readings=readings, summary=summary,
    )
