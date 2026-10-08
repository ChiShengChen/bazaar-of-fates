"""紫微斗數 四化 tables and helpers (年干 → 化祿/化權/化科/化忌), plus the 命財官 landing score used by the readings.
"""

from __future__ import annotations

from datetime import date

from fortune.engines.bazi import bazi as B   # reuse the verified year/month-stem calendar

# iztro's 四化 table (年干 → 化祿/化權/化科/化忌), extracted from py_iztro for consistency.
SIHUA = {
    "甲": ["廉貞", "破軍", "武曲", "太陽"], "乙": ["天機", "天梁", "紫微", "太陰"],
    "丙": ["天同", "天機", "文昌", "廉貞"], "丁": ["太陰", "天同", "天機", "巨門"],
    "戊": ["貪狼", "太陰", "右弼", "天機"], "己": ["武曲", "貪狼", "天梁", "文曲"],
    "庚": ["太陽", "武曲", "太陰", "天同"], "辛": ["巨門", "太陽", "文曲", "文昌"],
    "壬": ["天梁", "紫微", "左輔", "武曲"], "癸": ["破軍", "巨門", "太陰", "貪狼"],
}
HUA = ["祿", "權", "科", "忌"]
TARGET = {"命宮", "財帛", "官祿"}        # life / wealth / career
_HOUR_INDEX = 5                          # 09:30 市場開盤 → 巳時


class EngineUnavailable(RuntimeError):
    pass


def build_natal(birth: date) -> dict:
    """Cast the natal 命盤 via the pure-Python engine (no native deps; verified
    cell-by-cell against py-iztro). Overlays the natal 四化 (生年天干's transformations)
    onto the stars for display. Returns palaces + star→palace map + meta."""
    try:
        from lunardate import LunarDate

        from fortune.engines.ziwei import ziwei_core
    except Exception as e:  # noqa: BLE001
        raise EngineUnavailable(f"ziwei engine unavailable: {type(e).__name__}") from e
    natal = ziwei_core.build_chart(birth)
    ly = LunarDate.fromSolarDate(birth.year, birth.month, birth.day).year
    natal_hua = {s: HUA[i] for i, s in enumerate(SIHUA.get(B.STEMS[(ly - 4) % 10], []))}
    for p in natal["palaces"]:
        p["stars"] = [s + (f"({natal_hua[s]})" if s in natal_hua else "") for s in p["stars"]]
    return natal


def liunian_sihua(d: date) -> tuple[str, list[str]]:
    """(年干, [祿星,權星,科星,忌星]) for date d — 立春-anchored via the 八字 calendar."""
    stem = B.STEMS[B.year_pillar(d)[0]]
    return stem, SIHUA[stem]


def liuyue_sihua(d: date) -> tuple[str, list[str]]:
    stem = B.STEMS[B.month_pillar(d)[0]]
    return stem, SIHUA[stem]


def _score(star_palace: dict[str, str], mutagen: list[str]) -> tuple[int, int, dict[str, str]]:
    """飛星 landing: 化祿/化權 into 命財官 = favourable; 化忌 into them = unfavourable."""
    lu, quan, _ke, ji = mutagen
    landing = {f"化{HUA[i]}": f"{mutagen[i]}→{star_palace.get(mutagen[i], '?')}" for i in range(4)}
    fav = sum(1 for s in (lu, quan) if star_palace.get(s) in TARGET)
    unfav = 1 if star_palace.get(ji) in TARGET else 0
    return fav, unfav, landing


def ziwei_readings(natal: dict, as_of: date) -> dict[str, float | str]:
    stem, mut = liunian_sihua(as_of)
    fav, unfav, landing = _score(natal["star_palace"], mut)
    return {
        "ziwei_regime": "favourable_year" if fav > unfav else "unfavourable_year",
        "soul_star": natal["soul"], "body_star": natal["body"],
        "five_elements_class": natal["five_elements_class"],
        "liunian_stem": stem,
        "liunian_sihua": "、".join(f"{mut[i]}化{HUA[i]}" for i in range(4)),
        "sihua_landing": " ".join(f"{k}:{v}" for k, v in landing.items()),
    }


def readings_block(r: dict[str, float | str]) -> str:
    order = ["ziwei_regime", "soul_star", "body_star", "five_elements_class",
             "liunian_stem", "liunian_sihua", "sihua_landing"]
    return "\n".join(f"- {k}: {r[k]}" for k in order if k in r)


def reasoning_chain(natal: dict, as_of: date) -> list[str]:
    stem, mut = liunian_sihua(as_of)
    fav, unfav, landing = _score(natal["star_palace"], mut)
    return [
        f"排盤：命宮主星 {natal['soul']}、身宮主星 {natal['body']}、{natal['five_elements_class']}。",
        f"流年天干＝{stem}，四化：" + "、".join(f"{mut[i]}化{HUA[i]}" for i in range(4)) + "。",
        "四化飛星落宮：" + "；".join(f"{k} {v}" for k, v in landing.items()) + "。",
        f"命財官三宮（命宮/財帛/官祿）：化祿權入 {fav} 顆、化忌入 {unfav} 顆。",
    ]
