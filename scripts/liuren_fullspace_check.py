"""Full-space 大六壬 check against kinliuren: 60 日 × 12 占時 × 12 月將 = 8640 courses.
Compares 四課 (to confirm the same 月將), 十二天將, 三傳, and tabulates disagreements by course type.
Usage: python scripts/liuren_fullspace_check.py [--show N]
"""

from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

import kinliuren as _kl

sys.path.insert(0, os.path.dirname(_kl.__file__))
from kinliuren import kinliuren as KL  # noqa: E402

from fortune import bazi_ext as X  # noqa: E402
from fortune import liuren_ext as LX  # noqa: E402

# 中氣 → 月將 (太陽過宮): 雨水 亥(登明) … 大寒 子(神后)
TERM_OF_YJ = {11: "雨水", 10: "春分", 9: "穀雨", 8: "小滿", 7: "夏至", 6: "大暑", 5: "處暑", 4: "秋分", 3: "霜降", 2: "小雪", 1: "冬至", 0: "大寒"}
LUNAR_M = {11: "正", 10: "二", 9: "三", 8: "四", 7: "五", 6: "六", 5: "七", 4: "八", 3: "九", 2: "十", 1: "冬", 0: "臘"}


def main(show: int = 12) -> int:
    n = comparable = agree3 = agree1 = 0
    skipped = Counter()
    by_kind: dict[str, Counter] = defaultdict(Counter)
    examples: dict[str, list] = defaultdict(list)
    for gz_i in range(60):
        ds, db = gz_i % 10, gz_i % 12
        day_gz = X.STEMS[ds] + X.BRANCHES[db]
        for hb in range(12):
            hs = (ds % 5 * 2 + hb) % 10
            hour_gz = X.STEMS[hs] + X.BRANCHES[hb]
            for yj in range(12):
                n += 1
                try:
                    theirs = KL.Liuren(TERM_OF_YJ[yj], LUNAR_M[yj], day_gz, hour_gz).result(0)
                except Exception as e:  # noqa: BLE001
                    skipped[type(e).__name__] += 1
                    continue
                ours = LX.cast(ds, db, hb, yj)
                t_courses = [theirs["四課"][k][0] for k in ("一課", "二課", "三課", "四課")]
                o_courses = [c["upper"] + (c["lower"] if i else X.STEMS[ds]) for i, c in enumerate(ours["courses"])]
                if t_courses != o_courses:
                    skipped["月將 mismatch"] += 1
                    continue
                comparable += 1
                t_gen = dict(zip(theirs["天地盤"]["天盤"], theirs["天地盤"]["天將"]))
                for br, g in ours["generals"].items():
                    if t_gen.get(br) != LX.GENERAL_SHORT[LX.GENERALS.index(g)]:
                        by_kind["天將"]["mismatch"] += 1
                        break
                t3 = [theirs["三傳"][k][0] for k in ("初傳", "中傳", "末傳")]
                kind = ours["kind"].split("（")[0]
                ok = t3 == ours["transmissions"]
                agree3 += ok
                agree1 += t3[0] == ours["transmissions"][0]
                by_kind[kind]["total"] += 1
                by_kind[kind]["agree"] += ok
                if not ok and len(examples[kind]) < show:
                    examples[kind].append((day_gz, hour_gz, X.BRANCHES[yj], theirs["格局"], t3, ours["kind"], ours["transmissions"], ours["notes"]))
    print(f"cases {n}  comparable {comparable}  三傳 agree {agree3} ({agree3 / max(1, comparable):.1%})  初傳 agree {agree1} ({agree1 / max(1, comparable):.1%})")
    print("skipped:", dict(skipped))
    for kind, c in sorted(by_kind.items(), key=lambda kv: -kv[1]["total"]):
        if "total" in c:
            print(f"  {kind:10s} {c['agree']:5d}/{c['total']:5d}  {c['agree'] / c['total']:.1%}")
        else:
            print(f"  {kind}: {dict(c)}")
    for kind, ex in examples.items():
        print(f"\n== {kind} disagreements (first {len(ex)})")
        for e in ex:
            print("  ", e)
    return 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 12))
