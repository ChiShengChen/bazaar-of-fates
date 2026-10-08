"""時家奇門遁甲・轉盤・拆補法 / Hour-chart Qi Men Dun Jia (rotating plates, 拆補 method).

Native module. The engine is a day-of-year placeholder; this is the
standard 起局:
  1. 節氣 in force (exact, from fortune.bazi_ext) → 陽遁 (冬至…芒種) / 陰遁 (夏至…大雪)
  2. 元 (上/中/下) from the day's 符頭 — the latest 甲/己 day at or before it
     (甲子 甲午 己卯 己酉 → 上元; 甲寅 甲申 己巳 己亥 → 中元; 甲辰 甲戌 己丑 己未 → 下元)
  3. 局數 from the 節氣 × 元 table
  4. 地盤: 六儀三奇 (戊己庚辛壬癸丁丙乙) from the 局數 palace, 陽順陰逆 through 九宮
  5. 時干支 (五鼠遁; 23:00+ counts as the next day's 子時) → 旬首 → 值符星 / 值使門
  6. 天盤: 值符 follows the 時干's palace; 值使 follows the 時支 (counted from the 旬首 branch);
     the other stars / gates rotate with them; 八神 from the 值符 palace, 陽順陰逆
Lo Shu palaces 1–9 (5 = centre; 天禽 and its 門 寄坤二).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fortune import bazi_ext as X
from fortune.engines.bazi import bazi as BZ

STEMS, BRANCHES = X.STEMS, X.BRANCHES
PALACE_NAME = {1: "坎一", 2: "坤二", 3: "震三", 4: "巽四", 5: "中五", 6: "乾六", 7: "兌七", 8: "艮八", 9: "離九"}
PALACE_DIR = {1: "北", 2: "西南", 3: "東", 4: "東南", 5: "中", 6: "西北", 7: "西", 8: "東北", 9: "南"}
STAR = {1: "天蓬", 2: "天芮", 3: "天沖", 4: "天輔", 5: "天禽", 6: "天心", 7: "天柱", 8: "天任", 9: "天英"}
GATE = {1: "休門", 2: "死門", 3: "傷門", 4: "杜門", 6: "開門", 7: "驚門", 8: "生門", 9: "景門"}
GOOD_GATES, BAD_GATES = {"開門", "休門", "生門"}, {"傷門", "死門", "驚門"}
RING = [1, 8, 3, 4, 9, 2, 7, 6]                         # clockwise around the outer palaces
GODS_YANG = ["值符", "騰蛇", "太陰", "六合", "白虎", "玄武", "九地", "九天"]
_YI = "戊己庚辛壬癸丁丙乙"                               # 六儀三奇 布局 order
_XUN_YI = {0: "戊", 10: "己", 20: "庚", 30: "辛", 40: "壬", 50: "癸"}   # 旬首 → 六儀

_JU = {  # 節氣 → (上元, 中元, 下元); 陽遁 冬至→芒種, 陰遁 夏至→大雪
    "冬至": (1, 7, 4), "小寒": (2, 8, 5), "大寒": (3, 9, 6), "立春": (8, 5, 2), "雨水": (9, 6, 3), "驚蟄": (1, 7, 4),
    "春分": (3, 9, 6), "清明": (4, 1, 7), "穀雨": (5, 2, 8), "立夏": (4, 1, 7), "小滿": (5, 2, 8), "芒種": (6, 3, 9),
    "夏至": (9, 3, 6), "小暑": (8, 2, 5), "大暑": (7, 1, 4), "立秋": (2, 5, 8), "處暑": (1, 4, 7), "白露": (9, 3, 6),
    "秋分": (7, 1, 4), "寒露": (6, 9, 3), "霜降": (5, 8, 2), "立冬": (6, 9, 3), "小雪": (5, 8, 2), "大雪": (4, 7, 1),
}
_YANG_TERMS = {"冬至", "小寒", "大寒", "立春", "雨水", "驚蟄", "春分", "清明", "穀雨", "立夏", "小滿", "芒種"}
_YUAN_OF_FUTOU = {0: 0, 30: 0, 15: 0, 45: 0, 50: 1, 20: 1, 5: 1, 35: 1, 40: 2, 10: 2, 25: 2, 55: 2}   # 60-cycle idx → 元


def _step(palace: int, n: int) -> int:
    """Move n palaces through 1…9 (陽 +, 陰 −), wrapping."""
    return (palace - 1 + n) % 9 + 1


_TERM_ORDER = ["冬至", "小寒", "大寒", "立春", "雨水", "驚蟄", "春分", "清明", "穀雨", "立夏", "小滿", "芒種",
               "夏至", "小暑", "大暑", "立秋", "處暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪"]


def _zhirun(d_eff: datetime, tz: float) -> tuple[str, int, str]:
    """置閏法: the 15-day block starts at the 上元 符頭 (甲子/己卯/甲午/己酉 day, 60-cycle idx % 15 == 0).
    A block belongs to the latest 節氣 that begins no later than 9 days after its head (超神 ≤ 9 days,
    otherwise 接氣). When that would repeat a term, the repeat is allowed only at 芒種 / 大雪 (the 閏);
    elsewhere the block is handed to the following term. Returns (term, yuan, note)."""
    ds, db = BZ.day_pillar(d_eff.date())
    idx = X.gz_index(ds, db)
    head_day = d_eff.date() - timedelta(days=idx % 15)
    elapsed = idx % 15
    yuan = elapsed // 5
    head_dt = datetime(head_day.year, head_day.month, head_day.day, 0, 0)
    terms = X.all_terms(head_day.year - 1, tz) + X.all_terms(head_day.year, tz) + X.all_terms(head_day.year + 1, tz)
    terms = [t for t in terms if t[1] in _JU]
    term = max(t for t in terms if t[0] <= head_dt + timedelta(days=9))
    prev_head = head_dt - timedelta(days=15)
    prev_term = max(t for t in terms if t[0] <= prev_head + timedelta(days=9))
    note = ""
    if prev_term[1] == term[1] and term[1] not in ("芒種", "大雪"):
        later = [t for t in terms if t[0] > term[0]]
        term = min(later, key=lambda t: t[0])
        note = f"超神逾九日，非芒種/大雪不置閏，改用次節 {term[1]}"
    elif prev_term[1] == term[1]:
        note = f"置閏：{term[1]} 重複一局（閏奇）"
    return term[1], yuan, note


def cast_hour(dt_local: datetime, tz: float, method: str = "chaibu") -> dict:
    """`method`: "chaibu" 拆補法 (default) or "zhirun" 置閏法."""
    # day & hour pillars (23:00+ → next day's 子時)
    d_eff = dt_local + timedelta(hours=1) if dt_local.hour >= 23 else dt_local
    ds, db = BZ.day_pillar(d_eff.date())
    hs, hb = BZ.hour_pillar(ds, dt_local.hour)
    day_idx = X.gz_index(ds, db)
    method_note = ""
    if method == "zhirun":
        term_name, yuan, method_note = _zhirun(d_eff, tz)
        term = next(t for t in (X.all_terms(d_eff.year - 1, tz) + X.all_terms(d_eff.year, tz) + X.all_terms(d_eff.year + 1, tz))
                    if t[1] == term_name and abs((t[0] - d_eff).days) < 60)
    else:
        term = X.current_term(dt_local, tz)
        futou_idx = max(k for k in _YUAN_OF_FUTOU if k <= day_idx) if any(k <= day_idx for k in _YUAN_OF_FUTOU) else 55
        yuan = _YUAN_OF_FUTOU[futou_idx]
    yang = term[1] in _YANG_TERMS
    ju = _JU[term[1]][yuan]

    # 地盤
    earth: dict[int, str] = {}
    pal = ju
    for yi in _YI:
        earth[pal] = yi
        pal = _step(pal, 1 if yang else -1)
    stem_palace = {v: k for k, v in earth.items()}

    # 旬首 → 值符 / 值使
    hour_idx = X.gz_index(hs, hb)
    xun_head = hour_idx // 10 * 10
    xun_yi = _XUN_YI[xun_head]
    xun_branch = xun_head % 12
    fu_palace = stem_palace[xun_yi]
    fu_palace_eff = 2 if fu_palace == 5 else fu_palace            # 天禽 / 中宮 寄坤二
    zhifu_star = STAR[fu_palace]
    zhishi_gate = GATE[fu_palace_eff]
    kong = X.kong_wang(hs, hb)

    # 天盤 stars: 值符 moves to the 時干's palace (甲 → its 旬首儀)
    hour_stem = STEMS[hs] if STEMS[hs] != "甲" else xun_yi
    target = stem_palace[hour_stem]
    target_eff = 2 if target == 5 else target
    star_rot = (RING.index(target_eff) - RING.index(fu_palace_eff)) % 8
    sky_star: dict[int, str] = {}
    sky_stem: dict[int, str] = {}
    for i, home in enumerate(RING):
        dest = RING[(i + star_rot) % 8]
        sky_star[dest] = STAR[home] + ("禽" if home == 2 and fu_palace == 5 else "")
        sky_stem[dest] = earth[home]
    # 天盤 gates: 值使 moves with the 時支, counted from the 旬首 branch, 陽順陰逆 through 1–9
    steps = (hb - xun_branch) % 12
    shi_palace = _step(fu_palace, steps if yang else -steps)          # counts from the real palace (中五 included)
    shi_palace_eff = 2 if shi_palace == 5 else shi_palace
    gate_rot = (RING.index(shi_palace_eff) - RING.index(fu_palace_eff)) % 8
    sky_gate: dict[int, str] = {}
    for i, home in enumerate(RING):
        sky_gate[RING[(i + gate_rot) % 8]] = GATE[home]
    # 八神 from the 值符's new palace, 陽遁順 / 陰遁逆 around the ring
    gods: dict[int, str] = {}
    start = RING.index(target_eff)
    for k, god in enumerate(GODS_YANG):
        gods[RING[(start + (k if yang else -k)) % 8]] = god

    palaces = [{
        "palace": p, "name": PALACE_NAME[p], "direction": PALACE_DIR[p],
        "earth_stem": earth.get(p, ""), "sky_stem": sky_stem.get(p, earth.get(p, "") if p == 5 else ""),   # 中宮 does not rotate
        "star": sky_star.get(p, "天禽" if p == 5 else ""), "gate": sky_gate.get(p, ""), "god": gods.get(p, ""),
        "gate_cls": "吉" if sky_gate.get(p) in GOOD_GATES else "凶" if sky_gate.get(p) in BAD_GATES else "平" if sky_gate.get(p) else "",
    } for p in range(1, 10)]
    active_gate_palace = next(p for p in palaces if p["gate"] == zhishi_gate)
    return {
        "term": term[1], "term_at": term[0].isoformat(timespec="minutes"), "dun": "陽遁" if yang else "陰遁",
        "method": "置閏法" if method == "zhirun" else "拆補法", "method_note": method_note,
        "yuan": "上中下"[yuan] + "元", "ju": ju, "ju_label": f"{'陽' if yang else '陰'}遁{ju}局",
        "day_gz": STEMS[ds] + BRANCHES[db], "hour_gz": STEMS[hs] + BRANCHES[hb], "late_zi": dt_local.hour >= 23,
        "xun_head": STEMS[xun_head % 10] + BRANCHES[xun_branch], "xun_yi": xun_yi, "kong_wang": kong,
        "zhifu": zhifu_star, "zhifu_palace": target_eff, "zhishi": zhishi_gate, "zhishi_palace": active_gate_palace["palace"],
        "gate_class": "三吉門" if zhishi_gate in GOOD_GATES else "凶門" if zhishi_gate in BAD_GATES else "平門",
        "palaces": palaces,
    }
