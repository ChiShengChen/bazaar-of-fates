"""Jyotiṣa（吠陀占星）— sidereal 命盤 + the active Vimśottarī Mahādaśā."""

from __future__ import annotations

from datetime import date

from fortune.birth import BirthInput
from fortune.engines.jyotish import jyotish
from fortune.schemas import Chart

KEY, ZH, EN = "jyotish", "Jyotiṣa（吠陀占星）", "Jyotiṣa · Vedic Astrology"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    natal_chart = jyotish.chart(birth.as_date)
    readings = jyotish.jyotish_readings(birth.as_date, today)
    chain = jyotish.reasoning_chain(birth.as_date, today)
    rows = [{"graha": nm, "sidereal_lon": lon, "rashi": rashi} for (nm, lon, rashi) in natal_chart]
    summary = (
        f"月宿 {readings.get('moon_nakshatra', '')}・月 rāśi {readings.get('moon_rashi', '')}・"
        f"大運 {readings.get('mahadasha_lord', '')}（{readings.get('dasha_nature', '')}）"
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"grahas": rows}, reasoning_chain=chain, readings=readings, summary=summary,
    )
