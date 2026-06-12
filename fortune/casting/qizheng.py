"""七政四餘 — Chinese astral 命盤 (7 visibles + 4 shadow points), with this year's transits."""

from __future__ import annotations

from datetime import date

from fortune import astro_ext as AX
from fortune.birth import BirthInput
from fortune.engines.qizheng import qizheng
from fortune.schemas import Chart

KEY, ZH, EN = "qizheng", "七政四餘", "Qi Zheng Si Yu · Seven Luminaries"


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    natal_chart = qizheng.chart_for(birth.as_date)
    natal_sun_sign = qizheng._sign(natal_chart[0][1])      # Sun is first in 七政
    readings = qizheng.qizheng_readings(natal_sun_sign, today)
    chain = qizheng.reasoning_chain(natal_sun_sign, today, natal_chart)
    rows = [{"body": nm, "ecliptic_lon": lon, "sign": sign} for (nm, lon, sign) in natal_chart]

    # 命宮 (rising "life palace") = the ascendant degree; needs 時辰 + 出生地
    asc = AX.ascendant_block(birth)
    if asc:
        for r in rows:
            r["house"] = AX.house_of(r["ecliptic_lon"], asc["longitude"])
        readings["ming_gong_sign"] = f"{asc['sign']} {asc['sign_zh']} {asc['longitude']:.1f}°"
        chain.insert(1, f"命宮（命度／上升）：{asc['sign_zh']}宮 {asc['longitude']:.1f}°"
                        f"——七政四餘以命度起十二宮。")
        ming_str = f"・命宮 {asc['sign_zh']}"
    else:
        readings["ming_gong_sign"] = "unknown — needs birth time + place 需時辰＋出生地"
        ming_str = ""

    summary = (
        f"命主太陽 {readings.get('ming_zhu_sign', '')}{ming_str}"
        f"・流年 {readings.get('qizheng_regime', '')}"
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"bodies": rows}, reasoning_chain=chain, readings=readings, summary=summary,
        ascendant=asc,
    )
