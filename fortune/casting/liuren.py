"""大六壬 — 四課三傳起課 from the birth date; day-stem taken from the 八字 day pillar."""

from __future__ import annotations

from datetime import date

from fortune.birth import BirthInput
from fortune.engines.bazi import bazi
from fortune.engines.liuren import liuren
from fortune.schemas import Chart

KEY, ZH, EN = "liuren", "大六壬", "Da Liu Ren"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    ds_idx, _ = bazi.day_pillar(birth.as_date)
    day_stem = bazi.STEMS[ds_idx]
    day_stem_elem = bazi.STEM_ELEM[ds_idx]
    readings = liuren.liuren_readings(birth.as_date, day_stem, day_stem_elem)
    chain = liuren.reasoning_chain(birth.as_date, today, day_stem, day_stem_elem)
    summary = (
        f"日干 {day_stem}（{day_stem_elem}）・"
        f"{readings.get('liuren_regime', readings.get('yong', ''))}"
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"day_stem": day_stem, "day_stem_elem": day_stem_elem},
        reasoning_chain=chain, readings=readings, summary=summary,
    )
