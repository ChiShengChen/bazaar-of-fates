"""Build a deterministic chart dataset (no LLM) as gzipped JSONL.

  紫微 — the whole input space: 60 年干支 × 12 農曆月 × 30 日 × 12 時辰 × 2 性別 = 518,400 charts
         (one 甲子 cycle of 農曆 years; any birth maps onto one of them). Each row: palaces (stars with
         brightness / 雜曜 when x-iztro is installed), 命主/身主/五行局, 生年四化, 12 大限 (ages, 宮干四化),
         and a rule-based verdict + facts for 7 topics (fortune.focus) — the "reading skeleton".
  八字 — by solar date over a year range × 12 時辰 × 2 性別 (the real-world input), each row: exact-節氣
         四柱 with 十神/藏干/納音/空亡/神煞, 胎元/命宮, 旺衰/用神/格局, 起運, 9 大運 (optionally with 流年),
         稱骨, and the 7-topic verdicts.

Usage:
  python scripts/build_dataset.py ziwei --out data/ziwei.jsonl.gz [--limit N] [--liunian]
  python scripts/build_dataset.py bazi  --out data/bazi.jsonl.gz --years 1960-2030 [--hours 0,2,...] [--limit N] [--liunian]
Row sizes: 紫微 ≈ 4 KB (≈ 45 KB with 流年), 八字 ≈ 3 KB (≈ 70 KB with 流年).
"""

from __future__ import annotations

import argparse, gzip, json, sys, time
from datetime import date, datetime, time as _time, timedelta

from fortune.lunar import to_solar

from fortune import bazi_ext as X
from fortune import focus as F
from fortune import ziwei_ext as ZX
from fortune.birth import BirthInput
from fortune.engines.ziwei import ziwei as ZW
from fortune.schemas import Chart

TOPICS = ["career", "love", "wealth", "health", "study", "family", "general"]


def _verdicts(chart: Chart, male: bool) -> dict:
    out = {}
    for t in TOPICS:
        e = F.extract(chart, t, male)
        out[t] = {"verdict": e["verdict"], "reason": e["reason"], "facts": e["facts"]}
    return out


def ziwei_rows(limit: int, with_liunian: bool, enrich: bool, asof: date):
    astro = None
    if enrich:
        try:
            from x_iztro import Astro
            astro = Astro()
        except Exception:  # noqa: BLE001
            astro = None
    n = 0
    for ly in range(1924, 1984):                                   # 甲子 … 癸亥
        for lm in range(1, 13):
            for ld in range(1, 31):
                try:
                    sd = to_solar(ly, lm, ld, False)
                except Exception:  # noqa: BLE001
                    sd = None
                for hb in range(12):
                    for male in (True, False):
                        natal = ZX.build_chart_lunar(ly, lm, ld, hb)
                        stem = natal["lunar"]["year_gz"][0]
                        hua = {s: ZW.HUA[i] for i, s in enumerate(ZW.SIHUA[stem])}
                        for p in natal["palaces"]:
                            p["stars"] = [s + (f"({hua[s]})" if s in hua else "") for s in p["stars"]]
                        luck = ZX.luck(natal, male, asof)
                        if astro is not None and sd is not None:
                            try:
                                ch = astro.by_solar(f"{sd.year}-{sd.month}-{sd.day}", hb, "male" if male else "female", language="zh-TW")
                                br = {pal.earthly_branch: ({st.name: (st.brightness or "") for st in pal.major_stars + pal.minor_stars},
                                                           [st.name for st in pal.adjective_stars]) for pal in ch.palaces}
                                for p in natal["palaces"]:
                                    p["brightness"], p["adjective_stars"] = br.get(p["branch"], ({}, []))
                            except Exception:  # noqa: BLE001
                                pass
                        daxian = [{k: v for k, v in d.items() if k != "liunian"} | ({"liunian": d["liunian"]} if with_liunian else {}) for d in luck["daxian"]]
                        chart = Chart(system="ziwei", system_zh="紫微斗數", subject="", cast_at=datetime(2000, 1, 1),
                                      chart={"palaces": natal["palaces"], "star_palace": natal["star_palace"], "luck": {**luck, "daxian": luck["daxian"]}},
                                      readings={}, summary="")
                        row = {
                            "id": f"{natal['lunar']['year_gz']}-{lm:02d}-{ld:02d}-{ZX.BRANCHES[hb]}-{'M' if male else 'F'}",
                            "input": {"lunar_year_gz": natal["lunar"]["year_gz"], "lunar_month": lm, "lunar_day": ld, "hour_branch": ZX.BRANCHES[hb],
                                      "gender": "male" if male else "female", "example_solar_date": sd.isoformat() if sd else None},
                            "soul": natal["soul"], "body": natal["body"], "five_elements_class": natal["five_elements_class"],
                            "life_branch": natal["life_branch"], "natal_sihua": "、".join(f"{s}化{ZW.HUA[i]}" for i, s in enumerate(ZW.SIHUA[stem])),
                            "palaces": natal["palaces"], "daxian": daxian, "start_age": luck["start_age"], "forward": luck["forward"],
                            "topics": _verdicts(chart, male), "asof": asof.isoformat(),
                        }
                        yield row
                        n += 1
                        if limit and n >= limit:
                            return


def bazi_rows(years: tuple[int, int], hours: list[int], limit: int, with_liunian: bool, asof: date):
    n = 0
    d = date(years[0], 1, 1)
    end = date(years[1], 12, 31)
    while d <= end:
        for h in hours:
            for male in (True, False):
                birth = BirthInput(birth_date=d, birth_time=_time(h, 0), gender="male" if male else "female")
                full = X.full_chart(birth, today=asof)
                dayun = [{k: v for k, v in dy.items() if k != "liunian"} | ({"liunian": dy["liunian"]} if with_liunian else {}) for dy in full["dayun"]]
                chart = Chart(system="bazi", system_zh="八字（四柱）", subject="", cast_at=birth.dt, chart=full, readings={}, summary="")
                row = {
                    "id": f"{d.isoformat()}-{h:02d}-{'M' if male else 'F'}",
                    "input": {"solar_date": d.isoformat(), "hour": h, "gender": "male" if male else "female", "tz": 8},
                    "pillars": [{k: p[k] for k in ("pillar", "gz", "stem_god", "hidden", "nayin", "kong_wang", "changsheng", "shensha")} for p in full["pillars"]],
                    "lunar": full["lunar"]["text"], "tai_yuan": full["tai_yuan"], "ming_gong": full["ming_gong"],
                    "strength": {k: full["strength"][k] for k in ("label", "ratio", "favourable", "avoid", "yongshen", "yongshen_why", "tiaohou_note", "pattern")},
                    "relations": full["stem_notes"] + full["branch_notes"], "qi_yun": full["qi_yun"]["text"], "jiao_yun": full["qi_yun"]["jiao_yun"],
                    "dayun": dayun, "cheng_gu": full["cheng_gu"]["label"],
                    "topics": _verdicts(chart, male), "asof": asof.isoformat(),
                }
                yield row
                n += 1
                if limit and n >= limit:
                    return
        d += timedelta(days=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("system", choices=["ziwei", "bazi"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--liunian", action="store_true", help="include the per-year 流年 lists (much larger)")
    ap.add_argument("--years", default="1960-2030")
    ap.add_argument("--hours", default="0,2,4,6,8,10,12,14,16,18,20,22")
    ap.add_argument("--no-enrich", action="store_true", help="紫微: skip x-iztro brightness/雜曜")
    ap.add_argument("--asof", default="2026-01-01", help="the 'today' used for current 大運/流年 flags and topic verdicts")
    a = ap.parse_args()
    y0, y1 = (int(x) for x in a.years.split("-"))
    asof = date.fromisoformat(a.asof)
    rows = ziwei_rows(a.limit, a.liunian, not a.no_enrich, asof) if a.system == "ziwei" else bazi_rows((y0, y1), [int(h) for h in a.hours.split(",")], a.limit, a.liunian, asof)
    t0, n = time.time(), 0
    with gzip.open(a.out, "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
            if n % 20000 == 0:
                print(f"{n} rows, {time.time() - t0:.0f}s", flush=True)
    print(f"DONE {n} rows → {a.out} in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
