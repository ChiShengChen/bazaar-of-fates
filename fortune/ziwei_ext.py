"""紫微斗數 with the real birth hour / 接時辰的紫微排盤.

The synced `ziwei_core.build_chart` hardcodes 巳時 (the market open) because a stock has
no birth hour. 命宮/身宮/五行局/紫微星位/輔星 all genuinely depend on 生時, and the core
primitives (`life_palace_branch`, `major_star_positions`, `aux_star_positions`, …) already
accept a `hour_branch` — so this native module re-assembles the natal chart threading the
real hour, calling those primitives rather than copying their internals.

This is NOT synced; if `ziwei_core.build_chart` changes upstream, re-check this mirror.
本檔不被 sync 覆蓋；若上游 build_chart 變更，需回頭核對此鏡像。
"""

from __future__ import annotations

from datetime import date

from fortune.engines.ziwei import ziwei as ZW          # SIHUA / HUA / TARGET / B(bazi)
from fortune.engines.ziwei import ziwei_core as ZC


def hour_branch_of(hour: int) -> int:
    """Clock hour 0–23 → 時支 index (子=0…亥=11). 23–1→子, 9–11→巳."""
    return ((hour + 1) // 2) % 12


def build_chart(listing: date, hour_branch: int) -> dict:
    """ziwei_core.build_chart, but with the birth 時支 instead of the hardcoded 巳時."""
    ld = ZW.B  # noqa: F841 — keep import side; lunar via LunarDate below
    from lunardate import LunarDate

    lz = LunarDate.fromSolarDate(listing.year, listing.month, listing.day)
    lunar_month, lunar_day, lunar_year = lz.month, lz.day, lz.year

    life_b = ZC.life_palace_branch(lunar_month, hour_branch)
    body_b = (((2 + (lunar_month - 1)) % 12) + hour_branch) % 12
    year_branch = (lunar_year - 4) % 12
    elem, juju = ZC.five_elements_class(lunar_year, life_b)
    zw = ZC.ziwei_branch(juju, lunar_day)

    star_branch: dict[str, int] = {}
    star_branch.update(ZC.major_star_positions(zw))
    star_branch.update(ZC.aux_star_positions(lunar_month, hour_branch))

    branch_palace = {(life_b - i) % 12: ZC.PALACE_NAMES[i] for i in range(12)}
    star_palace = {s: branch_palace[b] for s, b in star_branch.items()}

    palaces = []
    for b in range(12):
        stars = sorted(
            [s for s, bb in star_branch.items() if bb == b],
            key=lambda s: 0 if s in ZC._ZIWEI_SERIES or s in ZC._TIANFU_SERIES else 1,
        )
        palaces.append({"name": branch_palace[b], "branch": ZC.BRANCHES[b],
                        "is_body": b == body_b, "stars": stars})
    return {
        "soul": ZC._MING_ZHU[life_b], "body": ZC._SHEN_ZHU[year_branch],
        "five_elements_class": f"{elem}{'二三四五六'[juju - 2]}局",
        "palaces": palaces, "star_palace": star_palace,
        "life_branch": ZC.BRANCHES[life_b], "ziwei_branch": ZC.BRANCHES[zw],
        "hour_branch": ZC.BRANCHES[hour_branch],
    }


def build_natal(listing: date, hour_branch: int) -> dict:
    """ziwei.build_natal with the real hour: overlay the natal 四化 onto the stars."""
    from lunardate import LunarDate

    natal = build_chart(listing, hour_branch)
    ly = LunarDate.fromSolarDate(listing.year, listing.month, listing.day).year
    natal_hua = {s: ZW.HUA[i] for i, s in enumerate(ZW.SIHUA.get(ZW.B.STEMS[(ly - 4) % 10], []))}
    for p in natal["palaces"]:
        p["stars"] = [s + (f"({natal_hua[s]})" if s in natal_hua else "") for s in p["stars"]]
    return natal
