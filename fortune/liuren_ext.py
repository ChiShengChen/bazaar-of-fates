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
_MENG = {2, 5, 8, 11}
_ZHONG = {0, 3, 6, 9}


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

    zei = [c for c in courses if _ke(c[3], BE[c[2]])]          # 下賊上
    ke_ = [c for c in courses if _ke(BE[c[2]], c[3])]          # 上克下

    def resolve(cands, lower_attacks: bool):
        """比用 → 涉害 among several 賊克/遙克 candidates."""
        nonlocal kind
        if len(cands) == 1:
            return cands[0][2]
        bi = [c for c in cands if (c[2] % 2 == 0) == yang]
        if len(bi) == 1:
            kind = "知一課（比用）"
            return bi[0][2]
        pool = bi if bi else cands
        # 涉害: depth = number of 地盤 branches, from the branch the 上神 sits on back to its 本家,
        # that 剋 the 上神 (下賊上) / are 剋ed by it (上克下)
        scored = []
        for c in pool:
            u = c[2]
            b = down(u)
            depth = 0
            while True:
                if (lower_attacks and _ke(BE[b], BE[u])) or (not lower_attacks and _ke(BE[u], BE[b])):
                    depth += 1
                if b == u:
                    break
                b = (b + 1) % 12
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
            notes.append("涉害深淺相等且無孟仲，取首課（簡化）")
        return tops[0]

    if shift == 0:                                             # 伏吟
        kind = "伏吟課"
        if zei or ke_:
            chu = resolve(zei or ke_, bool(zei))
            kind = "伏吟課（有剋取剋）"
        else:
            chu = k1 if yang else k3
        zhong = _XING.get(chu)
        if zhong is None:                                      # 自刑 → 取另一上神
            zhong = k3 if chu == k1 else k1
            notes.append("初傳自刑，中傳取支上神" if chu == k1 else "初傳自刑，中傳取干上神")
        mo = _XING.get(zhong, (zhong + 6) % 12)
        if mo == chu:
            mo = (zhong + 6) % 12
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
        if yao and len(distinct) == 4:
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
    return {
        "yang_day": yang, "shift": shift,
        "courses": [{"name": n, "lower": (STEMS[ds] if is_stem else BRANCHES[l]), "lower_branch": BRANCHES[l], "upper": BRANCHES[u]}
                    for n, l, u, _e, is_stem in courses],
        "kind": kind, "notes": notes,
        "transmissions": [BRANCHES[chu], BRANCHES[zhong], BRANCHES[mo]],
        "chu": chu, "heaven_plate": [{"ground": BRANCHES[i], "sky": BRANCHES[up(i)]} for i in range(12)],
    }
