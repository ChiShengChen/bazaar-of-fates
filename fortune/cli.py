"""`bazaar` — cast charts in the terminal. No server, no API key.

  bazaar systems
  bazaar bazi 1990-06-15 14:30 --place 台北 --gender female
  bazaar ziwei 1990-06-15 14:30 --place Taipei
  bazaar all 1990-06-15 14:30 --place 台北
  bazaar synthesis 1990-06-15 14:30 --ask "明年事業"
  bazaar zeri 1990-06-15 14:30 --purpose wedding --from 2026-11-01 --to 2026-12-31
  bazaar today 1990-06-15 14:30
  add --read for the reading (mock digest unless LLM_BACKEND/ANTHROPIC_API_KEY are set), --json for raw JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, time

from fortune import casting, geo
from fortune.birth import BirthInput

_PILLAR_ROWS = (("十神", "stem_god"), ("天干", "stem"), ("地支", "branch"), ("納音", "nayin"), ("長生", "changsheng"), ("空亡", "kong_wang"))


def _birth(a) -> BirthInput:
    lat, lon, tz = a.lat, a.lon, a.tz
    if a.place and (lat is None or lon is None):
        hit = geo.lookup(a.place, date.fromisoformat(a.date))
        if hit:
            lat, lon = hit["latitude"], hit["longitude"]
            tz = hit["tz_offset_hours"] if a.tz is None else a.tz
            if hit.get("note"):
                print("·", hit["note"], file=sys.stderr)
    t = None
    if a.time:
        h, m = a.time.split(":")[:2]
        t = time(int(h), int(m))
    return BirthInput(name=a.name, birth_date=date.fromisoformat(a.date), birth_time=t, gender=a.gender, place=a.place,
                      latitude=lat, longitude=lon, tz_offset_hours=8.0 if tz is None else tz, true_solar_time=a.tst)


def _print_bazi(c: dict) -> None:
    rows = c["pillars"]
    print("  " + "".join(f"{p['pillar']:>10}" for p in rows))
    for label, key in _PILLAR_ROWS:
        print(f"{label:>4}" + "".join(f"{p[key]:>10}" for p in rows))
    print("  藏干" + "".join(f"{'/'.join(h['stem'] + h['god'][0] for h in p['hidden']):>10}" for p in rows))
    print("  神煞" + "".join(f"{'、'.join(p['shensha'][:2]) or '—':>10}" for p in rows))
    s = c["strength"]
    print(f"\n旺衰 {s['label']}（得力 {s['ratio']:.0%}）· 格局 {s['pattern']} · 用神 {s['yongshen']} · 喜 {'/'.join(s['favourable'])} 忌 {'/'.join(s['avoid'])}")
    print(f"胎元 {c['tai_yuan']} · 命宮 {c['ming_gong']} · {c['qi_yun']['text']} · 稱骨 {c['cheng_gu']['label']}")
    cur = next((d for d in c["dayun"] if d["current"]), None)
    if cur:
        print(f"現行大運 {cur['gz']}（{cur['stem_god']}・{cur['start_year']}–{cur['end_year']}）")
    print("大運 " + "  ".join(f"{d['start_age']}歲{d['gz']}" for d in c["dayun"]))


def _print_ziwei(c: dict) -> None:
    B = "子丑寅卯辰巳午未申酉戌亥"
    by = {p["branch"]: p for p in c["palaces"]}
    grid = [["巳", "午", "未", "申"], ["辰", "", "", "酉"], ["卯", "", "", "戌"], ["寅", "丑", "子", "亥"]]
    w = 22
    for row in grid:
        line1 = line2 = ""
        for b in row:
            if not b:
                line1 += " " * w; line2 += " " * w; continue
            p = by[b]
            stars = " ".join(s for s in p["stars"] if s.split("(")[0] in {"紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府", "太陰", "貪狼", "巨門", "天相", "天梁", "七殺", "破軍"}) or "空"
            minor = " ".join(s for s in p["stars"] if s.split("(")[0] not in {"紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府", "太陰", "貪狼", "巨門", "天相", "天梁", "七殺", "破軍"})
            line1 += f"{stars[:w - 1]:<{w}}"
            line2 += f"{(p['name'] + ' ' + p['stem'] + p['branch'] + (' 身' if p['is_body'] else '') + ' ' + minor)[:w - 1]:<{w}}"
        print(line1); print(line2); print()
    luck = c.get("luck", {})
    cur = next((d for d in luck.get("daxian", []) if d.get("current")), None)
    if cur:
        print(f"大限 {cur['palace']}（{cur['gz']}，{cur['ages'][0]}–{cur['ages'][1]} 虛歲）四化 {'、'.join(cur['sihua'])}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bazaar", description="Bazaar of Fates · 算命 — 13 divination systems in your terminal")
    ap.add_argument("system", help="bazi | ziwei | astrology | jyotish | iching | liuyao | xiaoliuren | suimei | qizheng | tieban | qimen | liuren | taiyi | all | synthesis | zeri | today | systems")
    ap.add_argument("date", nargs="?", help="birth date YYYY-MM-DD")
    ap.add_argument("time", nargs="?", help="birth time HH:MM (default noon)")
    ap.add_argument("--name"); ap.add_argument("--gender", choices=["male", "female"]); ap.add_argument("--place")
    ap.add_argument("--lat", type=float); ap.add_argument("--lon", type=float); ap.add_argument("--tz", type=float)
    ap.add_argument("--tst", action="store_true", help="true solar time for the 干支 systems")
    ap.add_argument("--read", action="store_true", help="also print the reading"); ap.add_argument("--lang", default="zh", choices=["zh", "en", "both"])
    ap.add_argument("--ask", help="question for the reading / synthesis"); ap.add_argument("--json", action="store_true")
    ap.add_argument("--purpose", default="wedding"); ap.add_argument("--from", dest="start"); ap.add_argument("--to", dest="end")
    ap.add_argument("--house-system", default="whole_sign"); ap.add_argument("--qimen-method", default="chaibu")
    a = ap.parse_args(argv)

    if a.system == "systems":
        for s in casting.systems():
            print(f"{s['key']:12s} {s['en']} · {s['zh']}")
        return 0
    if not a.date:
        ap.error("birth date required")
    b = _birth(a)

    if a.system == "synthesis":
        from fortune import focus as F
        from fortune.interpret import interpret_synthesis
        charts = {k: casting.cast(k, b, house_system=a.house_system, transits=(k == "astrology")) for k in casting.REGISTRY}
        male = {"male": True, "female": False}.get(a.gender or "")
        syn = F.synthesize(charts, F.classify(a.ask), male)
        if a.json:
            print(json.dumps(syn, ensure_ascii=False, indent=1)); return 0
        print(syn["summary"])
        for r in syn["systems"]:
            print(f"  {r['verdict_zh']:>2}  {r['system_zh']:10s} {r['reason']}")
        if a.read:
            print("\n" + interpret_synthesis(syn, focus=a.ask, lang=a.lang))
        return 0
    if a.system == "zeri":
        from fortune import zeri
        if not (a.start and a.end):
            ap.error("--from and --to required")
        out = zeri.select(b, date.fromisoformat(a.start), date.fromisoformat(a.end), a.purpose)
        if a.json:
            print(json.dumps(out, ensure_ascii=False, indent=1)); return 0
        print(f"擇日 {out['purpose_label']} {out['start']} → {out['end']}")
        by = {d["date"]: d for d in out["days"]}
        for i, d in enumerate(out["best"], 1):
            x = by[d]
            best_h = "、".join(f"{h['branch']}時" for h in x.get("hours", []) if h.get("best"))
            print(f"  #{i} {d} {x['weekday']} {x['gz']['day']} {'★' * x['grade']} {x['score']:+}  吉時 {best_h}  吉方 {'、'.join(x['qimen']['lucky_dirs'][:3])}")
            print("     " + "；".join(f"{r['src']}{r['delta']:+} {r['text']}" for r in x["reasons"][:4]))
        print("忌日 " + "、".join(out["avoid"][:12]))
        return 0
    if a.system == "today":
        from fortune import zeri
        out = zeri.day_outlook(b, date.today())
        if a.json:
            print(json.dumps(out, ensure_ascii=False, indent=1)); return 0
        print(f"{out['date']} {out['weekday']} 農曆 {out['lunar']} · {out['gz']['day']}日 · {'★' * out['grade']} {out['verdict']}（{out['score']:+}）")
        for r in out["reasons"]:
            print(f"  {r['src']} {r['delta']:+} {r['text']}")
        print("吉時 " + "、".join(f"{h['branch']}時 {h['hours']}" for h in out["hours"] if h["best"]) + " · 吉方 " + "、".join(out["qimen"]["lucky_dirs"]))
        return 0

    keys = list(casting.REGISTRY) if a.system == "all" else [a.system]
    for k in keys:
        if k not in casting.REGISTRY:
            ap.error(f"unknown system {k}")
        chart = casting.cast(k, b, house_system=a.house_system, qimen_method=a.qimen_method, transits=False)
        if a.json:
            print(chart.model_dump_json(indent=1) if len(keys) == 1 else json.dumps({k: chart.model_dump(mode="json")}, ensure_ascii=False)); continue
        print(f"\n== {chart.system_en} · {chart.system_zh} · {chart.subject}\n{chart.summary}\n")
        if k == "bazi":
            _print_bazi(chart.chart)
        elif k == "ziwei":
            _print_ziwei(chart.chart)
        else:
            for line in chart.reasoning_chain[:8]:
                print("  " + line)
        if a.read:
            from fortune.interpret import interpret
            print("\n" + interpret(chart, focus=a.ask, lang=a.lang).interpretation)
    return 0


if __name__ == "__main__":
    sys.exit(main())
