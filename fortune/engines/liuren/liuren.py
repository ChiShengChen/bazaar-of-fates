"""大六壬 basic helpers: 地支五行 and the 日主 vs 用神 五行 relation. The full 起課 (月將加時, 四課三傳, 九宗門, 天將) lives in fortune/liuren_ext.py.
"""

from __future__ import annotations

import math
from datetime import date

import ephem

from fortune.engines.bazi import bazi as B

BRANCHES = B.BRANCHES
BRANCH_ELEM = ["水", "土", "木", "木", "土", "火", "火", "土", "金", "金", "土", "水"]  # 子..亥
_SHENG = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}
_KE = {"金": "木", "木": "土", "土": "水", "水": "火", "火": "金"}
_OCCUPY = 5   # 占時 = 巳時 (birth-open convention)


def _sun_sign(d: date) -> int:
    s = ephem.Sun(); s.compute(ephem.Date(d))
    return int(math.degrees(ephem.Ecliptic(s).lon) % 360 // 30) % 12


def yue_jiang_branch(d: date) -> int:
    """月將 — 太陽過宮之支 (the 神將 of the month). Sun sign → 地支 (寅=2 起)."""
    return (_sun_sign(d) + 2) % 12


def yong_branch(d: date) -> int:
    """用神 (初傳) — 月將加占時，落於日支起算 (simplified)."""
    yj = yue_jiang_branch(d)
    day_branch = B.day_pillar(d)[1]
    return (yj + day_branch - _OCCUPY) % 12


def _relation(day_stem_elem: str, yong_elem: str) -> tuple[str, bool]:
    if day_stem_elem == yong_elem:
        return "比和", True
    if _SHENG.get(yong_elem) == day_stem_elem:
        return "用神生日主", True
    if _KE.get(day_stem_elem) == yong_elem:
        return "日主剋用神", True
    if _SHENG.get(day_stem_elem) == yong_elem:
        return "日主洩於用神", False
    if _KE.get(yong_elem) == day_stem_elem:
        return "用神剋日主", False
    return "無生剋", False


def auspicious(d: date, day_stem_elem: str) -> tuple[bool, str]:
    yb = yong_branch(d)
    rel, good = _relation(day_stem_elem, BRANCH_ELEM[yb])
    return good, rel


def liuren_readings(d: date, day_stem: str, day_stem_elem: str) -> dict[str, float | str]:
    yb = yong_branch(d)
    good, rel = auspicious(d, day_stem_elem)
    return {
        "liuren_regime": "supported" if good else "afflicted",
        "day_master": f"{day_stem}（{day_stem_elem}）",
        "yue_jiang": BRANCHES[yue_jiang_branch(d)],
        "occupy_hour": BRANCHES[_OCCUPY],
        "yong_branch": f"{BRANCHES[yb]}（{BRANCH_ELEM[yb]}）",
        "relation": rel,
    }


def readings_block(r: dict[str, float | str]) -> str:
    order = ["liuren_regime", "day_master", "yue_jiang", "occupy_hour", "yong_branch", "relation"]
    return "\n".join(f"- {k}: {r[k]}" for k in order if k in r)


def reasoning_chain(d_natal: date, as_of: date, day_stem: str, day_stem_elem: str) -> list[str]:
    r = liuren_readings(as_of, day_stem, day_stem_elem)
    return [
        f"起課（命課日干 {day_stem}；流日 {as_of.isoformat()} 占，簡化四課三傳）。",
        f"月將 {r['yue_jiang']}（太陽過宮）加 占時 {r['occupy_hour']} → 天地盤。",
        f"用神（初傳）：{r['yong_branch']}。",
        f"與日主 {day_stem}（{day_stem_elem}）之關係：{r['relation']}。",
    ]
