"""紫微斗數 with the real birth hour / 接時辰的紫微排盤 — plus the stars the core leaves out.

The synced `ziwei_core.build_chart` hardcodes 巳時 (the market open) because a stock has
no birth hour. 命宮/身宮/五行局/紫微星位/輔星 all genuinely depend on 生時, and the core
primitives (`life_palace_branch`, `major_star_positions`, `aux_star_positions`, …) already
accept a `hour_branch` — so this native module re-assembles the natal chart threading the
real hour, calling those primitives rather than copying their internals, and adds:
  • 閏月: first half (≤15) counts as the month itself, second half as the next month
  • 晚子時 (23:00–23:59): counted as the next day's 子時 (the common 紫微 convention)
  • 祿存 擎羊 陀羅 天魁 天鉞 (年干), 火星 鈴星 天馬 紅鸞 天喜 龍池 鳳閣 天哭 天虛 孤辰 寡宿 (年支),
    地空 地劫 (時支), 天刑 天姚 (月), 天才 天壽 (命/身)
  • 流年四化 keyed to the 農曆 year (same calendar as the natal 年干), not 立春

This is NOT synced; if `ziwei_core.build_chart` changes upstream, re-check this mirror.
本檔不被 sync 覆蓋；若上游 build_chart 變更，需回頭核對此鏡像。
"""

from __future__ import annotations

from datetime import date, timedelta

from fortune.engines.ziwei import ziwei as ZW          # SIHUA / HUA / TARGET / B(bazi)
from fortune.engines.ziwei import ziwei_core as ZC

_JU_START = {"水": 2, "木": 3, "金": 4, "土": 5, "火": 6}           # 大限起運虛歲 = 五行局數
_CS_START = {"水": 8, "木": 11, "金": 5, "土": 8, "火": 2}           # 十二長生 長生宮 by 五行局
CHANGSHENG = ["長生", "沐浴", "冠帶", "臨官", "帝旺", "衰", "病", "死", "墓", "絕", "胎", "養"]
BOSHI = ["博士", "力士", "青龍", "小耗", "將軍", "奏書", "飛廉", "喜神", "病符", "大耗", "伏兵", "官府"]
SUIQIAN = ["太歲", "晦氣", "喪門", "貫索", "官符", "小耗", "大耗", "龍德", "白虎", "天德", "弔客", "病符"]
JIANGQIAN = ["將星", "攀鞍", "歲驛", "息神", "華蓋", "劫煞", "災煞", "天煞", "指背", "咸池", "月煞", "亡神"]
_JIANGXING = [0, 6, 9, 3]                                            # 將星 by 三合 group (申子辰/寅午戌/巳酉丑/亥卯未)
_LIUCHANG = [5, 6, 8, 9, 8, 9, 11, 0, 2, 3]                          # 流年文昌 by 年干

STEMS, BRANCHES = ZC.STEMS, ZC.BRANCHES
_LUCUN = [2, 3, 5, 6, 5, 6, 8, 9, 11, 0]               # 祿存 by 年干 甲…癸
_KUI = [1, 0, 11, 11, 1, 0, 1, 6, 3, 3]                # 天魁 by 年干
_YUE = [7, 8, 9, 9, 7, 8, 7, 2, 5, 5]                  # 天鉞 by 年干
_SANHE = {0: 0, 4: 0, 8: 0, 2: 1, 6: 1, 10: 1, 5: 2, 9: 2, 1: 2, 11: 3, 3: 3, 7: 3}   # 申子辰/寅午戌/巳酉丑/亥卯未
_HUO_START = [2, 1, 3, 9]                              # 火星 起子時 by 三合 group
_LING_START = [10, 3, 10, 10]                          # 鈴星 起子時
_TIANMA = [2, 8, 11, 5]                                # 天馬 by 三合 group


def hour_branch_of(hour: int) -> int:
    """Clock hour 0–23 → 時支 index (子=0…亥=11). 23–1→子, 9–11→巳."""
    return ((hour + 1) // 2) % 12


def lunar_for_ziwei(d: date, hour: int) -> tuple[int, int, int, bool]:
    """(lunar_year, lunar_month, lunar_day, note) with the 晚子時 and 閏月 conventions applied."""
    from lunardate import LunarDate
    if hour >= 23:                                      # 晚子時 → next day
        d = d + timedelta(days=1)
    ld = LunarDate.from_solar_date(d.year, d.month, d.day)
    year, month, day = ld.year, ld.month, ld.day
    leap_shift = False
    if ld.is_leap_month and day > 15:                   # 閏月下半月 → 次月
        month += 1
        leap_shift = True
        if month == 13:
            month = 1
    return year, month, day, leap_shift


def extra_star_positions(year_stem: int, year_branch: int, lunar_month: int, hour_branch: int,
                         life_b: int, body_b: int) -> dict[str, int]:
    g = _SANHE[year_branch]
    lu = _LUCUN[year_stem]
    out = {
        "祿存": lu, "擎羊": (lu + 1) % 12, "陀羅": (lu - 1) % 12,
        "天魁": _KUI[year_stem], "天鉞": _YUE[year_stem],
        "火星": (_HUO_START[g] + hour_branch) % 12, "鈴星": (_LING_START[g] + hour_branch) % 12,
        "地劫": (11 + hour_branch) % 12, "地空": (11 - hour_branch) % 12,
        "天馬": _TIANMA[g],
        "紅鸞": (3 - year_branch) % 12, "天喜": (9 - year_branch) % 12,
        "龍池": (4 + year_branch) % 12, "鳳閣": (10 - year_branch) % 12,
        "天哭": (6 - year_branch) % 12, "天虛": (6 + year_branch) % 12,
        "天刑": (9 + lunar_month - 1) % 12, "天姚": (1 + lunar_month - 1) % 12,
        "天才": (life_b + year_branch) % 12, "天壽": (body_b + year_branch) % 12,
    }
    gu = {11: 2, 0: 2, 1: 2, 2: 5, 3: 5, 4: 5, 5: 8, 6: 8, 7: 8, 8: 11, 9: 11, 10: 11}
    gua = {11: 10, 0: 10, 1: 10, 2: 1, 3: 1, 4: 1, 5: 4, 6: 4, 7: 4, 8: 7, 9: 7, 10: 7}
    out["孤辰"], out["寡宿"] = gu[year_branch], gua[year_branch]
    return out


def build_chart(listing: date, hour_branch: int, clock_hour: int | None = None) -> dict:
    """ziwei_core.build_chart, but with the birth 時支 instead of the hardcoded 巳時,
    閏月/晚子時 conventions, and the auxiliary + 煞 stars."""
    lunar_year, lunar_month, lunar_day, leap_shift = lunar_for_ziwei(listing, clock_hour if clock_hour is not None else hour_branch * 2)

    life_b = ZC.life_palace_branch(lunar_month, hour_branch)
    body_b = (((2 + (lunar_month - 1)) % 12) + hour_branch) % 12
    year_branch = (lunar_year - 4) % 12
    year_stem = (lunar_year - 4) % 10
    elem, juju = ZC.five_elements_class(lunar_year, life_b)
    zw = ZC.ziwei_branch(juju, lunar_day)

    star_branch: dict[str, int] = {}
    star_branch.update(ZC.major_star_positions(zw))
    star_branch.update(ZC.aux_star_positions(lunar_month, hour_branch))
    star_branch.update(extra_star_positions(year_stem, year_branch, lunar_month, hour_branch, life_b, body_b))

    branch_palace = {(life_b - i) % 12: ZC.PALACE_NAMES[i] for i in range(12)}
    star_palace = {s: branch_palace[b] for s, b in star_branch.items()}
    rank = {s: 0 for s in list(ZC._ZIWEI_SERIES) + list(ZC._TIANFU_SERIES)}
    rank.update({s: 1 for s in ("文昌", "文曲", "左輔", "右弼", "天魁", "天鉞", "祿存", "天馬")})
    rank.update({s: 2 for s in ("擎羊", "陀羅", "火星", "鈴星", "地空", "地劫")})

    palaces = []
    for b in range(12):
        stars = sorted([s for s, bb in star_branch.items() if bb == b], key=lambda s: (rank.get(s, 3), s))
        palaces.append({"name": branch_palace[b], "branch": ZC.BRANCHES[b],
                        "stem": STEMS[ZC.life_palace_stem(lunar_year, b)],
                        "is_body": b == body_b, "stars": stars})
    return {
        "soul": ZC._MING_ZHU[life_b], "body": ZC._SHEN_ZHU[year_branch],
        "five_elements_class": f"{elem}{'二三四五六'[juju - 2]}局",
        "palaces": palaces, "star_palace": star_palace,
        "life_branch": ZC.BRANCHES[life_b], "ziwei_branch": ZC.BRANCHES[zw],
        "hour_branch": ZC.BRANCHES[hour_branch],
        "lunar": {"year": lunar_year, "month": lunar_month, "day": lunar_day, "year_gz": STEMS[year_stem] + BRANCHES[year_branch],
                  "leap_shifted": leap_shift, "late_zi": bool(clock_hour is not None and clock_hour >= 23)},
    }


def build_natal(listing: date, hour_branch: int, clock_hour: int | None = None) -> dict:
    """ziwei.build_natal with the real hour: overlay the natal 四化 (農曆年干) onto the stars."""
    natal = build_chart(listing, hour_branch, clock_hour)
    stem = natal["lunar"]["year_gz"][0]
    natal_hua = {s: ZW.HUA[i] for i, s in enumerate(ZW.SIHUA.get(stem, []))}
    for p in natal["palaces"]:
        p["stars"] = [s + (f"({natal_hua[s]})" if s in natal_hua else "") for s in p["stars"]]
    natal["natal_sihua"] = "、".join(f"{s}化{ZW.HUA[i]}" for i, s in enumerate(ZW.SIHUA.get(stem, [])))
    return natal


def liunian_sihua_lunar(d: date) -> tuple[str, list[str]]:
    """(年干, [祿,權,科,忌]) for the 農曆 year containing date d — same calendar as the natal 年干."""
    from lunardate import LunarDate
    ly = LunarDate.from_solar_date(d.year, d.month, d.day).year
    stem = STEMS[(ly - 4) % 10]
    return stem, ZW.SIHUA[stem]


def readings(natal: dict, as_of: date) -> dict:
    stem, mut = liunian_sihua_lunar(as_of)
    fav, unfav, landing = ZW._score(natal["star_palace"], mut)
    return {
        "ziwei_regime": "favourable_year" if fav > unfav else "unfavourable_year",
        "soul_star": natal["soul"], "body_star": natal["body"],
        "five_elements_class": natal["five_elements_class"],
        "natal_sihua": natal.get("natal_sihua", ""),
        "liunian_stem": stem,
        "liunian_sihua": "、".join(f"{mut[i]}化{ZW.HUA[i]}" for i in range(4)),
        "sihua_landing": " ".join(f"{k}:{v}" for k, v in landing.items()),
    }


def luck(natal: dict, male: bool, today: date, count_years: int = 10) -> dict:
    """大限 (五行局起運, 陽男陰女順/陰男陽女逆), 十二長生, 博士十二神, and the 流年 inside each 大限
    (太歲宮, 流年四化, 流祿/流羊/流陀/流魁/流鉞/流昌, 歲前/將前十二神)."""
    life_b = BRANCHES.index(natal["life_branch"])
    elem = natal["five_elements_class"][0]
    lunar_year = natal["lunar"]["year"]
    ys, yb = (lunar_year - 4) % 10, (lunar_year - 4) % 12
    forward = (ys % 2 == 0 and male) or (ys % 2 == 1 and not male)
    sign = 1 if forward else -1
    by_branch = {BRANCHES.index(p["branch"]): p for p in natal["palaces"]}
    start = _JU_START[elem]

    # static rings: 十二長生 (by 局, same direction) and 博士十二神 (from 祿存, same direction)
    cs0 = _CS_START[elem]
    lucun = next(BRANCHES.index(p["branch"]) for p in natal["palaces"] if any(st.startswith("祿存") for st in p["stars"]))
    for b, p in by_branch.items():
        p["changsheng"] = CHANGSHENG[(sign * (b - cs0)) % 12]
        p["boshi"] = BOSHI[(sign * (b - lucun)) % 12]

    age_now = today.year - lunar_year + 1                                   # 虛歲 (農曆年)
    daxian = []
    for k in range(12):
        b = (life_b + sign * k) % 12
        pal = by_branch[b]
        a0 = start + 10 * k
        stem = pal["stem"]
        y0 = lunar_year + a0 - 1
        liunian = []
        for a in range(a0, a0 + 10):
            yr = lunar_year + a - 1
            lys, lyb = (yr - 4) % 10, (yr - 4) % 12
            lstem = STEMS[lys]
            mut = ZW.SIHUA[lstem]
            lu = _LUCUN[lys]
            jg = _SANHE[lyb]
            suiqian = {BRANCHES[(lyb + i) % 12]: SUIQIAN[i] for i in range(12)}
            jiangqian = {BRANCHES[(_JIANGXING[jg] + i) % 12]: JIANGQIAN[i] for i in range(12)}
            liunian.append({
                "year": yr, "age": a, "gz": lstem + BRANCHES[lyb], "taisui_palace": by_branch[lyb]["name"], "branch": BRANCHES[lyb],
                "sihua": [f"{mut[i]}化{ZW.HUA[i]}" for i in range(4)],
                "sihua_landing": {ZW.HUA[i]: natal["star_palace"].get(mut[i], "?") for i in range(4)},
                "flow_stars": {"流祿": BRANCHES[lu], "流羊": BRANCHES[(lu + 1) % 12], "流陀": BRANCHES[(lu - 1) % 12],
                               "流魁": BRANCHES[_KUI[lys]], "流鉞": BRANCHES[_YUE[lys]], "流昌": BRANCHES[_LIUCHANG[lys]],
                               "流馬": BRANCHES[_TIANMA[jg]]},
                "suiqian": suiqian, "jiangqian": jiangqian,
                "current": yr == today.year,
            })
        dmut = ZW.SIHUA[stem]
        daxian.append({
            "index": k, "palace": pal["name"], "branch": pal["branch"], "stem": stem, "gz": stem + pal["branch"],
            "ages": [a0, a0 + 9], "years": [y0, y0 + 9], "changsheng": pal["changsheng"],
            "sihua": [f"{dmut[i]}化{ZW.HUA[i]}" for i in range(4)],
            "sihua_landing": {ZW.HUA[i]: natal["star_palace"].get(dmut[i], "?") for i in range(4)},
            "current": a0 <= age_now <= a0 + 9,
            "liunian": liunian,
        })
    return {"start_age": start, "forward": forward, "age_now": age_now, "daxian": daxian}
