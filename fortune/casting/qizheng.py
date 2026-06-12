"""七政四餘 — Chinese astral 命盤 (7 visibles + 4 shadow points), with this year's transits."""

from __future__ import annotations

from datetime import date

from fortune.birth import BirthInput
from fortune.engines.qizheng import qizheng
from fortune.schemas import Chart

KEY, ZH = "qizheng", "七政四餘"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    natal_chart = qizheng.chart_for(birth.as_date)
    natal_sun_sign = qizheng._sign(natal_chart[0][1])      # Sun is first in 七政
    readings = qizheng.qizheng_readings(natal_sun_sign, today)
    chain = qizheng.reasoning_chain(natal_sun_sign, today, natal_chart)
    rows = [{"body": nm, "ecliptic_lon": lon, "sign": sign} for (nm, lon, sign) in natal_chart]
    summary = (
        f"命主太陽 {readings.get('ming_zhu_sign', '')}・流年 {readings.get('qizheng_regime', '')}"
    )
    return Chart(
        system=KEY, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"bodies": rows}, reasoning_chain=chain, readings=readings, summary=summary,
    )
