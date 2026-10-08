"""六爻（納甲筮法）/ Liu Yao — 京房 納甲, 八宮世應, 六親, 六神, 伏神, 旺衰.

Native module. Hexagram casting reuses the 梅花 time method (本卦 + one 動爻 from the birth
moment); this module does the 納甲 part on top of any (lines, moving) pair:
  納甲   — 京房 stem/branch of each line (inner/outer trigram tables)
  八宮   — the 64 hexagrams generated from the 8 純卦 (本宮, 一世…五世, 游魂, 歸魂) → 宮 + 世/應
  六親   — line branch element vs 宮 element (兄弟/子孫/妻財/官鬼/父母)
  六神   — 青龍 … 玄武 from the 初爻 by 日干
  伏神   — 六親 missing from the 本卦, borrowed from the 本宮卦 at the same position
  旺衰   — each line vs 月建 (旺相休囚死) and 日辰 (臨/生/剋/沖/合), 旬空 by the 日柱
Rule references: 《增刪卜易》 and the open-source implementations listed in docs/CREDITS.md
(mingpan, jishiyu) — rules only, no code copied.
"""

from __future__ import annotations

from fortune.engines.bazi import bazi as BZ
from fortune.engines.iching import iching as IC

STEMS, BRANCHES = BZ.STEMS, BZ.BRANCHES
BE, SHENG, KE = BZ.BRANCH_ELEM, BZ.SHENG, BZ.KE
TRI_ELEM = {k: v["wuxing"] for k, v in IC.TRIGRAMS.items()}
# 京房 納甲: trigram → (inner stem, inner branches bottom→top, outer stem, outer branches)
NAJIA = {
    "乾": ("甲", [0, 2, 4], "壬", [6, 8, 10]), "坤": ("乙", [7, 5, 3], "癸", [1, 11, 9]),
    "震": ("庚", [0, 2, 4], "庚", [6, 8, 10]), "巽": ("辛", [1, 11, 9], "辛", [7, 5, 3]),
    "坎": ("戊", [2, 4, 6], "戊", [8, 10, 0]), "離": ("己", [3, 1, 11], "己", [9, 7, 5]),
    "艮": ("丙", [4, 6, 8], "丙", [10, 0, 2]), "兌": ("丁", [5, 3, 1], "丁", [11, 9, 7]),
}
SIX_GODS = ["青龍", "朱雀", "勾陳", "螣蛇", "白虎", "玄武"]
_GOD_START = [0, 0, 1, 1, 2, 3, 4, 4, 5, 5]            # by 日干 甲…癸
_LIUHE = {(0, 1), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7)}


def _trigram(lines: tuple[int, int, int]) -> str:
    return IC._trigram_by_lines(lines)


def _palace_table() -> dict[tuple, tuple[str, int]]:
    """lines(bottom→top, 6) → (宮 trigram, 世爻 position 1–6) for all 64 hexagrams."""
    table: dict[tuple, tuple[str, int]] = {}
    for tri in IC.ORDER:
        base = list(IC.TRIGRAMS[tri]["lines"]) * 2
        cur = list(base)
        table[tuple(cur)] = (tri, 6)                      # 本宮
        for k, shi in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5)):
            cur[k] ^= 1
            table[tuple(cur)] = (tri, shi)
        cur[3] ^= 1                                       # 游魂: 四爻復原
        table[tuple(cur)] = (tri, 4)
        cur[0:3] = base[0:3]                              # 歸魂: 內卦復原
        table[tuple(cur)] = (tri, 3)
    return table


PALACE = _palace_table()


def najia(lines: list[int]) -> list[dict]:
    """Stem/branch of each of the 6 lines (bottom→top)."""
    lower, upper = _trigram(tuple(lines[0:3])), _trigram(tuple(lines[3:6]))
    si, bi, so, bo = NAJIA[lower]
    _si2, _bi2, so2, bo2 = NAJIA[upper]
    out = []
    for i in range(6):
        stem, br = (si, bi[i]) if i < 3 else (so2, bo2[i - 3])
        out.append({"pos": i + 1, "yang": lines[i] == 1, "stem": stem, "branch": BRANCHES[br], "branch_idx": br, "elem": BE[br]})
    return out


def six_relative(palace_elem: str, elem: str) -> str:
    if elem == palace_elem:
        return "兄弟"
    if SHENG[palace_elem] == elem:
        return "子孫"
    if SHENG[elem] == palace_elem:
        return "父母"
    if KE[palace_elem] == elem:
        return "妻財"
    return "官鬼"


def _state(elem: str, month_elem: str) -> str:
    if elem == month_elem:
        return "旺"
    if SHENG[month_elem] == elem:
        return "相"
    if SHENG[elem] == month_elem:
        return "休"
    if KE[elem] == month_elem:
        return "囚"
    return "死"


def cast(lines: list[int], moving: int, day_stem: int, day_branch: int, month_branch: int) -> dict:
    """Full 納甲 chart for a hexagram with one 動爻. `moving` is 1–6 (0 = none)."""
    key = tuple(lines)
    palace, shi = PALACE[key]
    ying = ((shi - 1 + 3) % 6) + 1
    pal_elem = TRI_ELEM[palace]
    ben_num, ben_name = IC.kingwen(_trigram(tuple(lines[3:6])), _trigram(tuple(lines[0:3])))
    rows = najia(lines)
    god0 = _GOD_START[day_stem]
    kong = set(BRANCHES.index(c) for c in _kong(day_stem, day_branch))
    me = BE[month_branch]
    for i, r in enumerate(rows):
        r["relative"] = six_relative(pal_elem, r["elem"])
        r["god"] = SIX_GODS[(god0 + i) % 6]
        r["shi"] = (i + 1) == shi
        r["ying"] = (i + 1) == ying
        r["moving"] = (i + 1) == moving
        notes = [f"月{_state(r['elem'], me)}"]
        if r["branch_idx"] == day_branch:
            notes.append("日臨")
        elif (r["branch_idx"] - day_branch) % 12 == 6:
            notes.append("日沖（暗動）" if not r["moving"] else "日沖")
        elif tuple(sorted((r["branch_idx"], day_branch))) in _LIUHE:
            notes.append("日合")
        elif SHENG[BE[day_branch]] == r["elem"]:
            notes.append("日生")
        elif KE[BE[day_branch]] == r["elem"]:
            notes.append("日剋")
        if (r["branch_idx"] - month_branch) % 12 == 6:
            notes.append("月破")
        if r["branch_idx"] in kong:
            notes.append("旬空")
        r["notes"] = notes
    # 伏神: 六親 missing from the 本卦 → the 本宮卦's line with that 六親, at its position
    present = {r["relative"] for r in rows}
    base_rows = najia(list(IC.TRIGRAMS[palace]["lines"]) * 2)
    hidden = []
    for br in base_rows:
        rel = six_relative(pal_elem, br["elem"])
        if rel not in present:
            hidden.append({"pos": br["pos"], "relative": rel, "stem": br["stem"], "branch": br["branch"], "under": rows[br["pos"] - 1]["relative"]})
            rows[br["pos"] - 1]["hidden"] = f"伏{rel}{br['stem']}{br['branch']}"
    # 變卦
    changed = None
    if moving:
        cl = list(lines)
        cl[moving - 1] ^= 1
        c_num, c_name = IC.kingwen(_trigram(tuple(cl[3:6])), _trigram(tuple(cl[0:3])))
        crow = najia(cl)[moving - 1]
        crow["relative"] = six_relative(pal_elem, crow["elem"])
        mv = rows[moving - 1]
        rel_change = ("化回頭生" if SHENG[crow["elem"]] == mv["elem"] else "化回頭剋" if KE[crow["elem"]] == mv["elem"]
                      else "化進神" if crow["elem"] == mv["elem"] and (crow["branch_idx"] - mv["branch_idx"]) % 12 in (1, 2, 3) else
                      "化退神" if crow["elem"] == mv["elem"] else "化洩" if SHENG[mv["elem"]] == crow["elem"] else "化剋出")
        changed = {"num": c_num, "name": c_name, "lines": cl, "line": crow, "relation": rel_change,
                   "palace": PALACE[tuple(cl)][0]}
    return {
        "num": ben_num, "name": ben_name, "palace": palace, "palace_elem": pal_elem, "shi": shi, "ying": ying,
        "lines": rows, "hidden": hidden, "moving": moving, "changed": changed,
        "day_gz": STEMS[day_stem] + BRANCHES[day_branch], "month_branch": BRANCHES[month_branch],
        "kong_wang": "".join(_kong(day_stem, day_branch)),
    }


def _kong(stem: int, branch: int) -> tuple[str, str]:
    head = ((6 * stem - 5 * branch) % 60) // 10 * 10
    hb = head % 12
    return BRANCHES[(hb + 10) % 12], BRANCHES[(hb + 11) % 12]
