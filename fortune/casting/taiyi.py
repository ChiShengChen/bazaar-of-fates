"""太乙神數 — 年計 (the annual board) via fortune.taiyi_ext: 命局 on the birth year, 流年局 on this year, same rules.

太乙統宗 積年 (10153917 + 農曆年), 七十二局 陽遁, 太乙 三年一宮 歷八宮, 天目／始擊／計神／合神／定目, 主客定算與大將參將,
四神 天乙 地乙 直符 君基 臣基 民基 五福, 八門, and the classical judgements (三門五將, 主客相關, 多少占勝負).
"""

from __future__ import annotations

from datetime import date

from fortune import bazi_ext as X
from fortune import taiyi_ext as T
from fortune.birth import BirthInput
from fortune.schemas import Chart

KEY, ZH, EN = "taiyi", "太乙神數", "Tai Yi Shen Shu"


def _nayin_elem(d: date, tz: float) -> str:
    try:
        p = X.exact_pillars(__import__("datetime").datetime.combine(d, __import__("datetime").time(12, 0)), tz)
        return p["year"]["nayin"][-1]
    except Exception:  # noqa: BLE001
        return ""


def _lines(b: dict, label: str) -> list[str]:
    return [
        f"{label}：農曆 {b['lunar_year']} 年（太歲 {b['taisui']}），{b['method']}積年 {b['accumulated']}，{b['accumulated']} mod 72 → {b['ju_label']}（{b['li']}）；"
        f"太乙三年一宮歷八宮 → 太乙在 {b['taiyi']}宮（{b['taiyi_num']}，{b['taiyi_assist']}）。",
        f"天目（文昌）在 {b['wenchang']}（{b['wenchang_god']}），始擊在 {b['shiji']}（{b['shiji_god']}）；計神 {b['jigod']}（寅宮逆行）、合神 {b['hegod']}；定目 {b['dingmu']}。",
        f"主算：自文昌 {b['wenchang']} 順數至太乙前一宮 ＝ {b['home_cal']}（{'、'.join(b['home_cal_desc']) or '—'}）→ 主大將 {b['home_general']}宮、主參將 {b['home_vgen']}宮；"
        f"客算：自始擊 {b['shiji']} ＝ {b['away_cal']}（{'、'.join(b['away_cal_desc']) or '—'}）→ 客大將 {b['away_general']}宮、客參將 {b['away_vgen']}宮；定算 {b['set_cal']}。",
        f"四神 {b['four_god']}・天乙 {b['sky_yi']}・地乙 {b['earth_yi']}・直符 {b['zhi_fu']}・君基 {b['king_base']}・臣基 {b['officer_base']}・民基 {b['people_base']}・五福 {b['wufu']}・"
        f"帝符 {b['kingfu']}・太尊 {b['taijun']}・陽九 {b['yangjiu']}・百六 {b['baliu']}。",
        f"八門值事 {b['door_on_duty']}門，太乙宮臨{b['doors'][b['taiyi']]}門 → {b['three_doors']}；{b['five_generals']}；{b['host_guest_relation']}；{b['count_verdict']} → 斷「{b['verdict']}」。",
    ]


def cast(birth: BirthInput, *, taiyi_method: str = "tongzong") -> Chart:
    today = date.today()
    method = taiyi_method if taiyi_method in T.ACC_BASE else "tongzong"
    natal = T.year_board(birth.as_date, method=method, year_nayin_elem=_nayin_elem(birth.as_date, birth.tz_offset_hours))
    now = T.year_board(today, method=method, year_nayin_elem=_nayin_elem(today, birth.tz_offset_hours))
    readings = {
        "taiyi_regime": "host_prevails" if now["verdict"] == "主勝" else "guest_prevails" if now["verdict"] == "客勝" else "balanced",
        "method": natal["method"],
        "natal_accumulated_years": float(natal["accumulated"]), "natal_ju": natal["ju_label"], "natal_palace": natal["taiyi"] + "宮",
        "natal_wenchang_shiji": f"文昌 {natal['wenchang']}・始擊 {natal['shiji']}・計神 {natal['jigod']}",
        "natal_host_guest": f"主算 {natal['home_cal']}（將 {natal['home_general']}）・客算 {natal['away_cal']}（將 {natal['away_general']}）→ {natal['verdict']}",
        "liunian_year": float(now["lunar_year"]), "liunian_ju": now["ju_label"], "liunian_palace": now["taiyi"] + "宮",
        "liunian_wenchang_shiji": f"文昌 {now['wenchang']}・始擊 {now['shiji']}・計神 {now['jigod']}",
        "liunian_host_guest": f"主算 {now['home_cal']}（將 {now['home_general']}）・客算 {now['away_cal']}（將 {now['away_general']}）→ {now['verdict']}",
        "liunian_judgements": f"{now['three_doors']}・{now['five_generals']}・{now['host_guest_relation']}・{now['count_verdict']}・太乙{now['taiyi_assist']}",
        "verdict": now["verdict"],
    }
    chain = _lines(natal, "命局") + _lines(now, "流年局")
    summary = f"命局 {natal['ju_label']} 太乙在{natal['taiyi']}（{natal['verdict']}）・流年 {now['lunar_year']} {now['ju_label']} 太乙在{now['taiyi']}（{now['verdict']}）"
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"natal": natal, "liunian": now}, reasoning_chain=chain, readings=readings, summary=summary,
    )
