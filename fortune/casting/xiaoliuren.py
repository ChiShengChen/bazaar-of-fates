"""小六壬 — the six-palace quick divination from 農曆 month, day and hour (大安起正月)."""

from __future__ import annotations

from fortune import bazi_ext as X
from fortune.birth import BirthInput
from fortune.schemas import Chart

KEY, ZH, EN = "xiaoliuren", "小六壬", "Xiao Liu Ren"
PALACES = [
    ("大安", "木", "東", "吉", "身未動時，五行屬木，青龍；求謀安穩，事事平安"),
    ("留連", "水", "北", "凶", "卒未歸時，五行屬水，玄武；事難成，拖延反覆"),
    ("速喜", "火", "南", "吉", "人即至時，五行屬火，朱雀；喜訊將至，宜速不宜遲"),
    ("赤口", "金", "西", "凶", "官事凶時，五行屬金，白虎；口舌是非，慎言慎行"),
    ("小吉", "木", "東", "吉", "人來喜時，五行屬木，六合；小有所成，貴人相助"),
    ("空亡", "土", "中", "凶", "音信稀時，五行屬土，勾陳；落空無果，宜守不宜攻"),
]


def cast(birth: BirthInput) -> Chart:
    cdt = X.cast_dt(birth)
    hb = X.exact_pillars(cdt, birth.tz_offset_hours)["hour"]["branch_idx"]
    lunar = X.lunar_info(cdt.date(), hb)
    m, d, h = lunar["month"], lunar["day"], hb + 1
    im = (m - 1) % 6
    idd = (im + d - 1) % 6
    ih = (idd + h - 1) % 6
    name, elem, direction, luck, text = PALACES[ih]
    chain = [
        f"起課（農曆 {lunar['text']}）：大安起正月，順數 {m} 月落「{PALACES[im][0]}」；",
        f"自「{PALACES[im][0]}」起初一，順數 {d} 日落「{PALACES[idd][0]}」；",
        f"自「{PALACES[idd][0]}」起子時，順數至{X.BRANCHES[hb]}時（第 {h} 位）落「{name}」。",
        f"{name}：{text}。",
    ]
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"result": name, "elem": elem, "direction": direction, "luck": luck, "text": text,
               "path": [PALACES[im][0], PALACES[idd][0], name], "month": m, "day": d, "hour": h},
        reasoning_chain=chain,
        readings={"課": name, "五行": elem, "方位": direction, "吉凶": luck, "月日時": f"{PALACES[im][0]}→{PALACES[idd][0]}→{name}", "斷": text},
        summary=f"{name}（{luck}・{elem}・{direction}）",
    )
