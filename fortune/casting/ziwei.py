"""紫微斗數 — cast the natal 命盤 (命宮 from the real birth 時辰) and read 流年四化.

命宮/身宮/五行局/星位 are cast from the birth hour via fortune.ziwei_ext (the synced
core hardcodes 巳時 for stocks); it also applies the 閏月 / 晚子時 conventions and adds the
auxiliary and 煞 stars. With no birth_time we fall back to 午時 (noon).
"""

from __future__ import annotations

from datetime import date

from fortune import bazi_ext as X
from fortune import ziwei_ext
from fortune.birth import BirthInput
from fortune.engines.ziwei import ziwei
from fortune.schemas import Chart

KEY, ZH, EN = "ziwei", "紫微斗數", "Zi Wei Dou Shu · Purple Star"

# 引擎的流年判定是為交易訊號設計的，這裡翻成命理說法
_REGIME_ZH = {"favourable_year": "流年祿權入命財官", "unfavourable_year": "流年忌入命財官（宜守）"}


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    cdt = X.cast_dt(birth)                                   # true solar time if requested
    hb = ziwei_ext.hour_branch_of(cdt.hour)                 # 子0…亥11 from 生時
    natal = ziwei_ext.build_natal(cdt.date(), hb, clock_hour=cdt.hour)
    readings = ziwei_ext.readings(natal, today)
    male = X._is_male(birth)
    gender_assumed = male is None
    luck = ziwei_ext.luck(natal, True if male is None else male, today)
    cur = next((d for d in luck["daxian"] if d["current"]), None)
    cur_ln = next((l for d in luck["daxian"] for l in d["liunian"] if l["current"]), None)
    if cur:
        readings["current_daxian"] = (f"第{cur['index'] + 1}大限 {cur['palace']}（{cur['gz']}，{cur['ages'][0]}–{cur['ages'][1]} 虛歲，{cur['years'][0]}–{cur['years'][1]}）"
                                      f"大限四化 {'、'.join(cur['sihua'])}")
    if cur_ln:
        readings["current_liunian"] = (f"{cur_ln['year']} {cur_ln['gz']}（虛歲 {cur_ln['age']}）太歲在{cur_ln['taisui_palace']}宮；"
                                       f"流年四化 {'、'.join(cur_ln['sihua'])}；" + "、".join(f"{k}{v}" for k, v in cur_ln["flow_stars"].items()))
    readings["daxian_sequence"] = "　".join(f"{d['ages'][0]}–{d['ages'][1]}歲 {d['palace']}({d['gz']})" for d in luck["daxian"])
    if gender_assumed:
        readings["note"] = "性別未填，大限方向以男命推算 / gender unset → assumed male"
    readings["life_palace_branch"] = natal["life_branch"]
    readings["body_palace"] = next((p["name"] for p in natal["palaces"] if p["is_body"]), "")
    readings["hour_branch"] = natal["hour_branch"]
    readings["lunar_birth"] = f"農曆 {natal['lunar']['year_gz']}年 {natal['lunar']['month']} 月 {natal['lunar']['day']} 日 {natal['hour_branch']}時"
    life = next((p for p in natal["palaces"] if p["name"] == "命宮"), None)
    body = next((p for p in natal["palaces"] if p["is_body"]), None)
    life_stars = "、".join(life["stars"]) if life and life["stars"] else "空宮"
    body_stars = "、".join(body["stars"]) if body and body["stars"] else "空宮"
    readings["life_palace_stars"] = life_stars          # 命宮內的星（≠ 命主星 soul_star，後者由命宮地支決定）
    readings["body_palace_stars"] = body_stars
    readings["palaces"] = "　".join(f"{p['name']}({p['stem']}{p['branch']}):{'、'.join(p['stars']) or '空'}" for p in natal["palaces"])
    regime = _REGIME_ZH.get(readings.get("ziwei_regime", ""), readings.get("ziwei_regime", ""))
    readings["ziwei_regime"] = regime

    notes = []
    if natal["lunar"]["late_zi"]:
        notes.append("晚子時（23 時後）以次日論")
    if natal["lunar"]["leap_shifted"]:
        notes.append("閏月下半月以次月論")
    if not birth.birth_time:
        notes.append("時辰未知，以午時估算")
    chain = [
        f"生時 {natal['hour_branch']}時・{readings['lunar_birth']}" + (f"（{'；'.join(notes)}）" if notes else "")
        + f" → 命宮在 {natal['life_branch']}宮",
        f"排盤：命宮在 {natal['life_branch']}宮（{life_stars}）、身宮在 {readings['body_palace']}宮（{body_stars}）、"
        f"{readings.get('five_elements_class', '')}；命主星 {readings.get('soul_star', '?')}、身主星 {readings.get('body_star', '?')}",
        f"生年四化（{natal['lunar']['year_gz'][0]}干）：{natal.get('natal_sihua', '')}。",
        f"流年天干＝{readings['liunian_stem']}（農曆年），四化：{readings['liunian_sihua']}。",
        f"四化飛星落宮：{readings['sihua_landing']}。",
    ]
    if cur:
        chain.append(f"大限：{natal['five_elements_class']}起 {luck['start_age']} 虛歲，{'陽男陰女順行' if luck['forward'] else '陰男陽女逆行'}；"
                     f"現行{readings['current_daxian']}。")
    if cur_ln:
        chain.append(f"流年：{readings['current_liunian']}。")
    summary = (
        f"命宮 {natal['life_branch']}・命主星 {readings.get('soul_star', '?')}・"
        f"{readings.get('five_elements_class', '')}・{regime}"
    )
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"palaces": natal.get("palaces", []), "star_palace": natal.get("star_palace", {}), "lunar": natal["lunar"], "luck": luck},
        reasoning_chain=chain, readings=readings, summary=summary,
    )
