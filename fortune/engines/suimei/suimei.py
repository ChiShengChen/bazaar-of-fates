"""四柱推命 (Japanese Shichū-Suimei) tables: 十二運星 cycle, 天中殺 (空亡) from the 日柱 旬, 藏干.
"""

from __future__ import annotations

from datetime import date

from fortune.engines.bazi import bazi as B   # reuse the verified 干支 calendar

STEMS = B.STEMS
BRANCHES = B.BRANCHES

# 十二運星, in cycle order from 長生
TWELVE = ["長生", "沐浴", "冠帶", "臨官", "帝旺", "衰", "病", "死", "墓", "絕", "胎", "養"]
THRIVING = {"長生", "冠帶", "臨官", "帝旺"}        # 旺相 → favourable
WEAK = {"病", "死", "墓", "絕"}                    # 衰絕 → unfavourable
# 長生 branch index per day-stem (子0…亥11); 陽干 順行, 陰干 逆行
_CHANGSHENG = {0: 11, 1: 6, 2: 2, 3: 9, 4: 2, 5: 9, 6: 5, 7: 0, 8: 8, 9: 3}

# 藏干 (standard 本氣→餘氣), per branch index
_HIDDEN = {
    0: ["癸"], 1: ["己", "癸", "辛"], 2: ["甲", "丙", "戊"], 3: ["乙"], 4: ["戊", "乙", "癸"],
    5: ["丙", "庚", "戊"], 6: ["丁", "己"], 7: ["己", "丁", "乙"], 8: ["庚", "壬", "戊"],
    9: ["辛"], 10: ["戊", "辛", "丁"], 11: ["壬", "甲"],
}


def twelve_fortune(day_stem: int, branch: int) -> str:
    """十二運星 of `day_stem` at `branch`. 陽干順 / 陰干逆 from 長生."""
    cs = _CHANGSHENG[day_stem]
    if day_stem % 2 == 0:                          # 陽干 順行
        idx = (branch - cs) % 12
    else:                                          # 陰干 逆行
        idx = (cs - branch) % 12
    return TWELVE[idx]


def _sexagenary(stem: int, branch: int) -> int:
    for n in range(60):
        if n % 10 == stem and n % 12 == branch:
            return n
    raise ValueError("bad 干支")


def tenchusatsu(day_stem: int, day_branch: int) -> tuple[int, int]:
    """空亡 / 天中殺 — the void branch PAIR from the 日柱's 旬."""
    xun = _sexagenary(day_stem, day_branch) // 10   # 0..5
    a = (10 - 2 * xun) % 12
    return a, (a + 1) % 12


def liunian_branch(d: date) -> int:
    return B.year_pillar(d)[1]


def liuyue_branch(d: date) -> int:
    return B.month_pillar(d)[1]


def build_chart(birth: date) -> dict:
    """The natal 四柱 read Japanese-style: pillars + 十二運星 + 藏干, 日主, 天中殺."""
    p = B.four_pillars(birth)
    day_stem = p["day"]["stem_idx"]
    void = tenchusatsu(day_stem, p["day"]["branch_idx"])
    roles = {"year": "年", "month": "月", "day": "日", "hour": "時"}
    pillars = []
    for k in ("year", "month", "day", "hour"):
        pp = p[k]
        pillars.append({
            "role": roles[k], "gz": pp["gz"], "stem": pp["stem"], "branch": pp["branch"],
            "twelve_fortune": twelve_fortune(day_stem, pp["branch_idx"]),
            "hidden": _HIDDEN[pp["branch_idx"]],
        })
    return {
        "day_master": p["day"]["stem"], "day_master_elem": p["day"]["stem_elem"],
        "day_stem_idx": day_stem, "void": void,
        "tenchusatsu": BRANCHES[void[0]] + BRANCHES[void[1]],
        "pillars": pillars,
    }
