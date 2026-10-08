"""大六壬 九宗門 / the nine course-types of Da Liu Ren — native 起課 logic.

Given the 天地盤 (月將加占時), the 四課 and the 日干, derive the 三傳:
  賊克 (下賊上 → 重審, 上克下 → 元首) · 比用 (知一) · 涉害 · 遙克 (蒿矢/彈射) · 昴星 (虎視/冬蛇掩目)
  · 別責 · 八專 · 伏吟 · 返吟
Branch indices 子=0…亥=11. 寄宮: 甲寅 乙辰 丙巳 丁未 戊巳 己未 庚申 辛戌 壬亥 癸丑.
"""

from __future__ import annotations

from fortune.engines.bazi import bazi as BZ

STEMS, BRANCHES = BZ.STEMS, BZ.BRANCHES
BE = BZ.BRANCH_ELEM
SE = BZ.STEM_ELEM
KE = BZ.KE
JI_GONG = [2, 4, 5, 7, 5, 7, 8, 10, 11, 1]
_XING = {0: 3, 3: 0, 1: 10, 10: 7, 7: 1, 2: 5, 5: 8, 8: 2}          # 三刑; 辰午酉亥 自刑
_YIMA = {0: 2, 4: 2, 8: 2, 2: 8, 6: 8, 10: 8, 5: 11, 9: 11, 1: 11, 11: 5, 3: 5, 7: 5}
_HE_STEM = {0: 5, 5: 0, 1: 6, 6: 1, 2: 7, 7: 2, 3: 8, 8: 3, 4: 9, 9: 4}   # 五合
_SANHE_NEXT = {8: 0, 0: 4, 4: 8, 2: 6, 6: 10, 10: 2, 5: 9, 9: 1, 1: 5, 11: 3, 3: 7, 7: 11}
_JI_STEMS = {2: ["甲"], 4: ["乙"], 5: ["丙", "戊"], 7: ["丁", "己"], 8: ["庚"], 10: ["辛"], 11: ["壬"], 1: ["癸"]}   # 天干寄宮
_MENG = {2, 5, 8, 11}
_ZHONG = {0, 3, 6, 9}
GENERALS = ["貴人", "螣蛇", "朱雀", "六合", "勾陳", "青龍", "天空", "白虎", "太常", "玄武", "太陰", "天后"]
GENERAL_SHORT = ["貴", "蛇", "雀", "合", "勾", "龍", "空", "虎", "常", "玄", "陰", "后"]
_GUIREN = [(1, 7), (0, 8), (11, 9), (11, 9), (1, 7), (0, 8), (1, 7), (6, 2), (5, 3), (5, 3)]   # (晝貴, 夜貴) by 日干: 甲戊庚牛羊 乙己鼠猴 丙丁豬雞 辛馬虎 壬癸蛇兔(晝巳夜卯)


def generals(ds: int, hb: int, shift: int) -> dict[int, str]:
    """十二天將 on the 天盤: 貴人 = 晝貴 (占時 卯–申) or 夜貴; it sits on a 地盤 branch — 亥…辰 → 順布,
    巳…戌 → 逆布 (貴人順治逆亂). Returns {天盤 branch: general}."""
    day_time = 3 <= hb <= 8
    gui = _GUIREN[ds][0 if day_time else 1]
    ground = (gui - shift) % 12                      # the 地盤 branch under 貴人
    forward = ground in (11, 0, 1, 2, 3, 4)
    return {(gui + (k if forward else -k)) % 12: GENERALS[k] for k in range(12)}


def _ke(a: str, b: str) -> bool:
    return KE[a] == b


def cast(ds: int, db: int, hb: int, yj: int) -> dict:
    shift = (yj - hb) % 12
    up = lambda x: (x + shift) % 12
    down = lambda x: (x - shift) % 12
    yang = ds % 2 == 0
    de = SE[ds]
    g = JI_GONG[ds]
    k1, k3 = up(g), up(db)
    k2, k4 = up(k1), up(k3)
    courses = [("第一課", g, k1, de, True), ("第二課", k1, k2, BE[k1], False),
               ("第三課", db, k3, BE[db], False), ("第四課", k3, k4, BE[k3], False)]
    distinct = {(l, u) for _n, l, u, _e, _s in courses}
    notes: list[str] = []
    kind = ""
    chu: int | None = None
    zhong: int | None = None
    mo: int | None = None

    zei = [c for c in courses if _ke(c[3], BE[c[2]])]          # 下賊上 (all four courses, duplicates included)
    ke_ = [c for c in courses if _ke(BE[c[2]], c[3])]          # 上克下

    def resolve(cands, lower_attacks: bool):
        """比用 → 涉害 among several 賊克/遙克 candidates (the same 上神 in two courses counts once)."""
        nonlocal kind
        seen: set[int] = set()
        cands = [c for c in cands if not (c[2] in seen or seen.add(c[2]))]
        if len(cands) == 1:
            return cands[0][2]
        bi = [c for c in cands if (c[2] % 2 == 0) == yang]
        if len(bi) == 1:
            kind = "知一課（比用）"
            return bi[0][2]
        pool = bi if bi else cands
        # 涉害: each candidate 上神 walks BACKWARDS (逆數) over the 地盤 from the branch it sits on to
        # its 本家; count the branches (and the 天干 lodged there, 寄宮) that 剋 it (下賊上) / that it
        # 剋 (上克下). The deeper count wins.
        scored = []
        for c in pool:
            u = c[2]
            b = down(u)
            depth = 0
            while True:
                elems = [BE[b]] + [SE[STEMS.index(st)] for st in _JI_STEMS.get(b, [])]
                for e in elems:
                    if (lower_attacks and _ke(e, BE[u])) or (not lower_attacks and _ke(BE[u], e)):
                        depth += 1
                if b == u:
                    break
                b = (b - 1) % 12
            scored.append((depth, u))
        best = max(d for d, _u in scored)
        tops = [u for d, u in scored if d == best]
        kind = "涉害課"
        if len(tops) > 1:                                      # 深淺相等 → 取孟，次取仲
            for grp, label in ((_MENG, "孟"), (_ZHONG, "仲")):
                sel = [u for u in tops if down(u) in grp]
                if sel:
                    notes.append(f"涉害深淺相等，取{label}上神")
                    return sel[0]
            notes.append("涉害深淺相等，俱孟或俱仲（綴瑕）：" + ("陽日取干上神" if yang else "陰日取支上神"))
            pick = k1 if yang else k3
            return pick if pick in tops else tops[0]
        return tops[0]

    if shift == 0:                                             # 伏吟
        kind = "伏吟課"
        if zei or ke_:
            chu = resolve(zei or ke_, bool(zei))
            kind = "伏吟課（有剋取剋）"
        else:
            chu = k1 if yang else k3
        zhong = _XING.get(chu)
        if zhong is None:                                      # 初傳自刑 → 中傳取另一上神（陽日支上神／陰日干上神）
            zhong = k3 if chu == k1 else k1
            notes.append("初傳自刑，中傳取支上神" if chu == k1 else "初傳自刑，中傳取干上神")
            if zhong == chu:                                   # 干支上神相同 → 取沖
                zhong = (chu + 6) % 12
                notes.append("干支上神相同，中傳取沖")
        if zhong in _XING:
            mo = _XING[zhong]                                  # 中傳之刑（子卯互刑則末傳回初傳）
        else:
            mo = (zhong + 6) % 12                              # 中傳自刑 → 末傳取沖
            notes.append("中傳自刑，末傳取沖")
    elif shift == 6:                                           # 返吟
        kind = "返吟課"
        if zei or ke_:
            chu = resolve(zei or ke_, bool(zei))
            zhong, mo = up(chu), up(up(chu))
            kind = "返吟課（有剋取剋）"
        else:
            chu = _YIMA[db]
            zhong, mo = k3, k1
            notes.append("返吟無剋，初傳取日支驛馬，中傳支上神，末傳干上神")
    elif zei or ke_:
        chu = resolve(zei or ke_, bool(zei))
        if not kind:
            kind = "重審課（下賊上）" if zei else "元首課（上克下）"
        zhong, mo = up(chu), up(up(chu))
    else:
        yao = [c for c in courses[1:] if _ke(BE[c[2]], de)]    # 遙克: 上神剋日干 (蒿矢)
        if not yao:
            yao = [c for c in courses[1:] if _ke(de, BE[c[2]])]  # 日干剋上神 (彈射)
            label = "遙克課（彈射）"
        else:
            label = "遙克課（蒿矢）"
        if yao:
            chu = resolve(yao, False)
            kind = label if not kind else f"{label}・{kind}"
            zhong, mo = up(chu), up(up(chu))
        elif len(distinct) == 2 and g == db:                   # 八專: 干支同位
            kind = "八專課"
            if yang:
                chu = up((k1 + 2) % 12) if False else (k1 + 2) % 12
                notes.append("陽日自干上神順數三位")
            else:
                chu = (k4 - 2) % 12
                notes.append("陰日自第四課上神逆數三位")
            zhong = mo = k1
        elif len(distinct) == 3:                               # 別責: 一課不備
            kind = "別責課"
            if yang:
                chu = up(JI_GONG[_HE_STEM[ds]])
                notes.append("陽日取日干合神寄宮之上神")
            else:
                chu = _SANHE_NEXT[db]
                notes.append("陰日取日支三合之次支")
            zhong = mo = k1
        else:                                                  # 昴星
            if yang:
                kind = "昴星課（虎視）"
                chu, zhong, mo = up(9), k3, k1
            else:
                kind = "昴星課（冬蛇掩目）"
                chu, zhong, mo = down(9), k1, k3
    gen = generals(ds, hb, shift)
    return {
        "yang_day": yang, "shift": shift,
        "generals": {BRANCHES[b]: g for b, g in gen.items()},
        "transmission_generals": [gen[chu], gen[zhong], gen[mo]],
        "course_generals": [gen[u] for _n, _l, u, _e, _s in courses],
        "guiren_day": 3 <= hb <= 8,
        "courses": [{"name": n, "lower": (STEMS[ds] if is_stem else BRANCHES[l]), "lower_branch": BRANCHES[l], "upper": BRANCHES[u]}
                    for n, l, u, _e, is_stem in courses],
        "kind": kind, "notes": notes,
        "transmissions": [BRANCHES[chu], BRANCHES[zhong], BRANCHES[mo]],
        "chu": chu, "heaven_plate": [{"ground": BRANCHES[i], "sky": BRANCHES[up(i)], "general": gen[up(i)]} for i in range(12)],
    }
