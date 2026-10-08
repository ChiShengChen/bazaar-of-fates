"""太乙神數 — 太乙八宮起算 from the birth year (命局) and this year (流年).

The engine is a simplified stand-in (積年 from a nominal 上元, 24-year palace moves, a
deterministic 主算/客算 pair). This adapter keeps that model but casts it consistently:
the 命局 on the birth year and the 流年局 on today, both shown, both from the same rules.
"""

from __future__ import annotations

from datetime import date

from fortune.birth import BirthInput
from fortune.engines.taiyi import taiyi
from fortune.schemas import Chart

KEY, ZH, EN = "taiyi", "太乙神數", "Tai Yi Shen Shu"


def _block(d: date) -> dict:
    h, g = taiyi.host_guest(d)
    return {"year": taiyi.B._solar_year(d), "accumulated": taiyi.accumulated_years(d),
            "palace": taiyi.taiyi_palace(d), "host": h, "guest": g, "verdict": "主勝" if h >= g else "客勝"}


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    natal, now = _block(birth.as_date), _block(today)
    readings = {
        "taiyi_regime": "host_prevails" if now["host"] >= now["guest"] else "guest_prevails",
        "natal_accumulated_years": float(natal["accumulated"]), "natal_palace": natal["palace"] + "宮",
        "natal_host_guest": f"主 {natal['host']}・客 {natal['guest']} → {natal['verdict']}",
        "liunian_year": float(now["year"]), "liunian_palace": now["palace"] + "宮",
        "liunian_host_guest": f"主 {now['host']}・客 {now['guest']} → {now['verdict']}",
        "verdict": now["verdict"],
    }
    chain = [
        f"命局：生年 {natal['year']}，太乙積年 {natal['accumulated']}，太乙臨 {natal['palace']}宮（24 年遷一宮，不入中五）。",
        f"命局主算 {natal['host']}、客算 {natal['guest']} → 「{natal['verdict']}」。",
        f"流年局：{now['year']} 年積年 {now['accumulated']}，太乙臨 {now['palace']}宮。",
        f"流年主算 {now['host']}、客算 {now['guest']} → 「{now['verdict']}」（{'主勝利己' if now['verdict'] == '主勝' else '客勝不利己'}）。",
        "註：上元積年與主客算法為簡化模型，非正統太乙 十六神／格局 推算。",
    ]
    summary = f"命局太乙入 {natal['palace']}宮（{natal['verdict']}）・流年 {now['year']} 入 {now['palace']}宮（{now['verdict']}）"
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"natal": natal, "liunian": now}, reasoning_chain=chain, readings=readings, summary=summary,
    )
