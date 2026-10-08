"""奇門遁甲 — 時家奇門 命局 (the hour chart of the birth moment) via fortune.qimen_ext.

The synced engine's day-of-year 起局 is a placeholder and is no longer used for the chart;
this adapter casts the standard 轉盤・拆補法 chart: 節氣 → 遁/元/局 → 地盤 → 值符值使 → 天盤.
"""

from __future__ import annotations

from fortune import bazi_ext as X
from fortune import qimen_ext as Q
from fortune.birth import BirthInput
from fortune.schemas import Chart

KEY, ZH, EN = "qimen", "奇門遁甲", "Qi Men Dun Jia"


def cast(birth: BirthInput, *, qimen_method: str = "chaibu") -> Chart:
    g = Q.cast_hour(X.cast_dt(birth), birth.tz_offset_hours, method=qimen_method if qimen_method in ("chaibu", "zhirun") else "chaibu")
    regime = "auspicious_gate" if g["gate_class"] == "三吉門" else "ill_gate" if g["gate_class"] == "凶門" else "neutral_gate"
    readings = {
        "qimen_regime": regime, "method": g["method"] + (f"（{g['method_note']}）" if g["method_note"] else ""),
        "dun": g["dun"], "ju": g["ju_label"], "yuan": g["yuan"], "term": g["term"],
        "day_hour": f"{g['day_gz']}日 {g['hour_gz']}時" + ("（晚子時以次日計）" if g["late_zi"] else "") + ("（時辰未知以午時計）" if not birth.birth_time else ""),
        "xun": f"{g['xun_head']}旬（{g['xun_yi']}）・空亡 {g['kong_wang']}",
        "zhifu": f"{g['zhifu']}（落{Q.PALACE_NAME[g['zhifu_palace']]}宮）", "zhishi": f"{g['zhishi']}（落{Q.PALACE_NAME[g['zhishi_palace']]}宮）",
        "active_gate": g["zhishi"], "gate_class": g["gate_class"],
        "palaces": "　".join(f"{p['name']}:{p['god']}{p['star']}{p['gate']}{p['sky_stem']}/{p['earth_stem']}" for p in g["palaces"]),
    }
    chain = [
        f"起局（{X.cast_dt(birth).isoformat(timespec='minutes')}{' 真太陽時' if X.cast_dt(birth) != birth.dt else ' 本地時'}）：節氣 {g['term']}（{g['term_at'].replace('T', ' ')} 交）→ {g['dun']}；"
        f"日柱 {g['day_gz']} 符頭定 {g['yuan']}（{g['method']}{'：' + g['method_note'] if g['method_note'] else ''}）→ {g['ju_label']}。",
        "地盤：" + "、".join(f"{p['name']}{p['earth_stem']}" for p in g["palaces"]) + "。",
        f"時柱 {g['hour_gz']}，{g['xun_head']}旬，旬首遁 {g['xun_yi']} → 值符 {g['zhifu']}、值使 {g['zhishi']}；時旬空亡 {g['kong_wang']}。",
        f"值符隨時干落 {Q.PALACE_NAME[g['zhifu_palace']]}宮，值使隨時支落 {Q.PALACE_NAME[g['zhishi_palace']]}宮（{g['gate_class']}）。",
        "天盤：" + "、".join(f"{p['name']} {p['god']}·{p['star']}·{p['gate']}·{p['sky_stem']}" for p in g["palaces"] if p["palace"] != 5) + "。",
    ]
    summary = f"{g['ju_label']}（{g['term']}{g['yuan']}・{g['method']}）・值符 {g['zhifu']}・值使 {g['zhishi']}（{g['gate_class']}）"
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"ju": g["ju_label"], "palaces": g["palaces"], "zhifu": g["zhifu"], "zhishi": g["zhishi"],
               "gates": [{"palace": p["name"], "gate": p["gate"], "cls": p["gate_cls"]} for p in g["palaces"] if p["gate"]]},
        reasoning_chain=chain, readings=readings, summary=summary,
    )
