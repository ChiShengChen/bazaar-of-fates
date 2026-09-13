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

# 引擎的流年判定是為交易訊號設計的，這裡翻成命理說法
_REGIME_ZH = {"favourable_year": "流年祿權入命財官", "unfavourable_year": "流年忌入命財官（宜守）"}


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    hb = ziwei_ext.hour_branch_of(birth.hour)               # 子0…亥11 from 生時
    natal = ziwei_ext.build_natal(birth.as_date, hb)
    readings = ziwei.ziwei_readings(natal, today)
    readings["life_palace_branch"] = natal["life_branch"]
    readings["body_palace"] = next((p["name"] for p in natal["palaces"] if p["is_body"]), "")
    readings["hour_branch"] = natal["hour_branch"]
    life = next((p for p in natal["palaces"] if p["name"] == "命宮"), None)
    body = next((p for p in natal["palaces"] if p["is_body"]), None)
    life_stars = "、".join(life["stars"]) if life and life["stars"] else "空宮"
    body_stars = "、".join(body["stars"]) if body and body["stars"] else "空宮"
    readings["life_palace_stars"] = life_stars          # 命宮內的星（≠ 命主星 soul_star，後者由命宮地支決定）
    readings["body_palace_stars"] = body_stars
    regime = _REGIME_ZH.get(readings.get("ziwei_regime", ""), readings.get("ziwei_regime", ""))
    readings["ziwei_regime"] = regime
    # 引擎的 reasoning_chain 帶著母專案的交易措辭（上市日／開盤／訊號）且把「命主星」寫成「命宮主星」，
    # 這裡換成命理用語，並補上命宮／身宮實際坐的星
    chain = [line for line in ziwei.reasoning_chain(natal, today)
             if not line.startswith("訊號") and not line.startswith("排盤（上市日")]
    chain.insert(0, f"排盤：命宮在 {natal['life_branch']}宮（{life_stars}）、身宮在 {readings['body_palace']}宮（{body_stars}）、"
                    f"{readings.get('five_elements_class', '')}；命主星 {readings.get('soul_star', '?')}、身主星 {readings.get('body_star', '?')}")
    chain.insert(0, f"生時 {natal['hour_branch']}時 → 命宮在 {natal['life_branch']}宮")
    summary = (
        f"命宮 {natal['life_branch']}・命主星 {readings.get('soul_star', '?')}・"
        f"{readings.get('five_elements_class', '')}・{regime}"
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"palaces": natal.get("palaces", []), "star_palace": natal.get("star_palace", {})},
        reasoning_chain=chain, readings=readings, summary=summary,
    )
