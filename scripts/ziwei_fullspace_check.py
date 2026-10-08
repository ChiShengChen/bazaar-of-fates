"""Compare the native 紫微 engine with x-iztro over the WHOLE input space:
60 年干支 × 12 農曆月 × 30 日 × 12 時辰 (× gender for 大限 direction) = 518,400 charts.

Checks per chart: every star's palace (14 主星 + 22 輔煞), 命主/身主, 五行局, 十二長生, 博士十二神,
大限 age ranges. Prints a mismatch summary; exit code 1 if any.
Usage: python scripts/ziwei_fullspace_check.py [--years 1924-1983] [--step 1] [--out mismatches.jsonl]
"""

from __future__ import annotations

import argparse, json, sys, time
from datetime import date

from fortune.lunar import to_solar
from x_iztro import Astro

from fortune import ziwei_ext as ZX

STARS = {"紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府", "太陰", "貪狼", "巨門", "天相", "天梁", "七殺", "破軍",
         "文昌", "文曲", "左輔", "右弼", "祿存", "擎羊", "陀羅", "天魁", "天鉞", "火星", "鈴星", "地空", "地劫", "天馬",
         "紅鸞", "天喜", "龍池", "鳳閣", "天哭", "天虛", "天刑", "天姚", "天才", "天壽", "孤辰", "寡宿"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="1924-1983")          # one full 甲子 cycle of 農曆 years
    ap.add_argument("--step", type=int, default=1)           # sample every n-th day
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    y0, y1 = (int(x) for x in a.years.split("-"))
    astro = Astro()
    n = bad = 0
    t0 = time.time()
    outf = open(a.out, "w", encoding="utf-8") if a.out else None
    kinds: dict[str, int] = {}
    for ly in range(y0, y1 + 1):
        for lm in range(1, 13):
            for ld in range(1, 31):
                if (ld - 1) % a.step:
                    continue
                try:
                    sd = to_solar(ly, lm, ld, False)
                except Exception:  # noqa: BLE001 — day 30 absent in a 29-day month
                    continue
                for hb in range(12):
                    for male in (True, False):
                        n += 1
                        natal = ZX.build_chart_lunar(ly, lm, ld, hb)
                        luck = ZX.luck(natal, male, date(2026, 1, 1))
                        chart = astro.by_solar(f"{sd.year}-{sd.month}-{sd.day}", hb, "male" if male else "female", language="zh-TW")
                        theirs: dict[str, str] = {}
                        meta = {}
                        for pal in chart.palaces:
                            for st in list(pal.major_stars) + list(pal.minor_stars) + list(pal.adjective_stars):
                                theirs[st.name] = pal.earthly_branch
                            meta[pal.earthly_branch] = (pal.changsheng12, pal.boshi12, tuple(pal.decadal.range))
                        diffs = []
                        for p in natal["palaces"]:
                            for s in p["stars"]:
                                if s in STARS and theirs.get(s) != p["branch"]:
                                    diffs.append(f"{s}:{p['branch']}≠{theirs.get(s)}")
                            cs, bo, rng = meta[p["branch"]]
                            if p["changsheng"] != cs:
                                diffs.append(f"長生@{p['branch']}:{p['changsheng']}≠{cs}")
                            if p["boshi"] != bo:
                                diffs.append(f"博士@{p['branch']}:{p['boshi']}≠{bo}")
                            dx = next(d for d in luck["daxian"] if d["branch"] == p["branch"])
                            if tuple(dx["ages"]) != rng:
                                diffs.append(f"大限@{p['branch']}:{dx['ages']}≠{list(rng)}")
                        if natal["soul"] != chart.soul or natal["body"] != chart.body or natal["five_elements_class"] != chart.five_elements_class:
                            diffs.append(f"命身局:{natal['soul']}/{natal['body']}/{natal['five_elements_class']}≠{chart.soul}/{chart.body}/{chart.five_elements_class}")
                        if diffs:
                            bad += 1
                            for d in diffs:
                                kinds[d.split(":")[0].split("@")[0]] = kinds.get(d.split(":")[0].split("@")[0], 0) + 1
                            if outf:
                                outf.write(json.dumps({"lunar": [ly, lm, ld], "hour": hb, "male": male, "solar": sd.isoformat(), "diffs": diffs}, ensure_ascii=False) + "\n")
        print(f"{ly}: {n} charts, {bad} mismatches, {time.time() - t0:.0f}s", flush=True)
    print(f"DONE {n} charts, {bad} mismatches ({bad / max(n, 1):.4%}); kinds={kinds}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
