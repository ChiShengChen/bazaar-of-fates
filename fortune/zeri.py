"""擇日 / Date selection — score every day in a range for a purpose, from the facts the engines
already produce, and rank them. Also the per-day "今日運勢" outlook and the 吉時 of a day.

Per day (all deterministic, rules listed in the output as +/− reasons):
  黃曆   宜/忌 for the purpose, 建除十二值, 二十八宿 吉凶, 吉神/凶煞 counts, 彭祖百忌 (lunar-python, optional)
  八字   流日 stem element vs 喜用/忌, 沖日柱 (hard avoid), 歲破 / 月破, 日柱旬空, 合日支, 流日神煞 for the purpose
  紫微   流日四化 landing in the purpose palace (x-iztro, optional)
  奇門   值使門 class at noon (or the given hour) + the day's 吉方 (開/休/生門 or 三奇 palaces)
  小六壬 the day's palace at noon
Hours: 12 時辰 scored by 沖/合 with the day and the natal 日支, 時干 vs 喜用, 奇門 值使 at that hour, 小六壬.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fortune import bazi_ext as X
from fortune import qimen_ext as Q
from fortune.almanac import almanac
from fortune.birth import BirthInput
from fortune.casting.xiaoliuren import PALACES as XLR

PURPOSES = {
    "wedding": {"zh": "結婚", "en": "wedding", "yi": ["嫁娶", "納采", "纳采", "訂盟", "订盟", "合帳", "合帐", "納婿", "纳婿"], "ji": ["嫁娶", "納采", "纳采", "訂盟", "订盟"],
                "jianchu_good": ["成", "定", "開", "开", "執", "执", "平"], "jianchu_bad": ["破", "危", "閉", "闭", "收"], "palace": "夫妻",
                "shensha_good": ["紅鸞", "天喜", "天乙貴人", "天德貴人", "月德貴人", "桃花"], "shensha_bad": ["孤辰", "寡宿", "喪門", "吊客", "劫煞"]},
    "opening": {"zh": "開業", "en": "opening a business", "yi": ["開市", "开市", "開業", "开业", "立券", "交易", "納財", "纳财", "開工", "开工", "開張", "开张"], "ji": ["開市", "开市", "開業", "开业", "立券", "交易", "開工", "开工"],
                "jianchu_good": ["開", "开", "成", "滿", "满", "定"], "jianchu_bad": ["破", "閉", "闭", "危", "收"], "palace": "官祿",
                "shensha_good": ["祿神", "天乙貴人", "天德貴人", "月德貴人", "將星", "天廚貴人"], "shensha_bad": ["劫煞", "亡神", "喪門", "吊客"]},
    "moving": {"zh": "搬家", "en": "moving house", "yi": ["移徙", "入宅", "安床", "安香", "搬家", "遷移", "迁移"], "ji": ["移徙", "入宅", "安床"],
               "jianchu_good": ["成", "定", "滿", "满", "開", "开", "平"], "jianchu_bad": ["破", "危", "閉", "闭", "收", "建"], "palace": "田宅",
               "shensha_good": ["驛馬", "天乙貴人", "天德貴人", "月德貴人"], "shensha_bad": ["劫煞", "亡神", "喪門", "吊客"]},
    "contract": {"zh": "簽約", "en": "signing a contract", "yi": ["立券", "交易", "訂盟", "订盟", "納財", "纳财", "簽約", "签约", "會友", "会友"], "ji": ["立券", "交易", "訂盟", "订盟", "納財", "纳财"],
                 "jianchu_good": ["成", "定", "執", "执", "開", "开"], "jianchu_bad": ["破", "危", "閉", "闭"], "palace": "財帛",
                 "shensha_good": ["祿神", "天乙貴人", "文昌貴人", "天德貴人", "月德貴人"], "shensha_bad": ["劫煞", "亡神"]},
    "surgery": {"zh": "手術", "en": "surgery / medical", "yi": ["治病", "求醫", "求医", "針灸", "针灸", "療病", "疗病"], "ji": ["針灸", "针灸", "治病", "求醫", "求医", "療病", "疗病"],
                "jianchu_good": ["除", "破", "成", "開", "开"], "jianchu_bad": ["危", "閉", "闭", "收", "滿", "满"], "palace": "疾厄",
                "shensha_good": ["天醫", "天乙貴人", "天德貴人", "月德貴人"], "shensha_bad": ["喪門", "吊客", "劫煞", "亡神"]},
    "travel": {"zh": "出行", "en": "travel", "yi": ["出行", "移徙"], "ji": ["出行", "遠行", "远行"],
               "jianchu_good": ["成", "開", "开", "定", "平", "滿", "满"], "jianchu_bad": ["破", "危", "閉", "闭"], "palace": "遷移",
               "shensha_good": ["驛馬", "天乙貴人", "天德貴人", "月德貴人"], "shensha_bad": ["劫煞", "亡神", "喪門", "吊客"]},
    "wealth": {"zh": "求財", "en": "seeking wealth", "yi": ["納財", "纳财", "開市", "开市", "交易", "立券", "求財", "求财"], "ji": ["納財", "纳财", "開市", "开市", "交易"],
               "jianchu_good": ["成", "開", "开", "滿", "满", "定", "執", "执"], "jianchu_bad": ["破", "危", "閉", "闭", "收"], "palace": "財帛",
               "shensha_good": ["祿神", "天乙貴人", "天廚貴人", "天德貴人", "月德貴人"], "shensha_bad": ["劫煞", "亡神"]},
    "general": {"zh": "一般", "en": "general", "yi": ["祭祀", "祈福", "出行", "會友", "会友"], "ji": [],
                "jianchu_good": ["成", "開", "开", "定", "滿", "满", "平", "執", "执"], "jianchu_bad": ["破", "危", "閉", "闭"], "palace": "命宮",
                "shensha_good": ["天乙貴人", "天德貴人", "月德貴人"], "shensha_bad": ["劫煞", "亡神", "喪門", "吊客"]},
}
_WEEK = "一二三四五六日"


def _grade(score: float) -> tuple[int, str]:
    if score >= 5:
        return 5, "上吉"
    if score >= 3:
        return 4, "吉"
    if score >= 1:
        return 3, "可"
    if score >= -1:
        return 2, "平"
    return 1, "忌"


class Context:
    """Natal facts computed once for a whole date range."""

    def __init__(self, birth: BirthInput):
        self.birth = birth
        self.tz = birth.tz_offset_hours
        self.full = X.full_chart(birth)
        self.male = {"male": True, "female": False}.get((birth.gender or "").lower())
        self.star_palace: dict[str, str] | None = None
        self.iztro = None
        try:
            from x_iztro import Astro
            from fortune import ziwei_ext as ZX
            cdt = X.cast_dt(birth)
            hb = ZX.hour_branch_of(cdt.hour)
            natal = ZX.build_chart(cdt.date(), hb, clock_hour=cdt.hour)
            self.star_palace = natal["star_palace"]
            self.iztro = Astro().by_solar(f"{cdt.year}-{cdt.month}-{cdt.day}", hb, "male" if self.male else "female", language="zh-TW")
        except Exception:  # noqa: BLE001
            self.iztro = None


def _match(terms: list[str], words: list[str]) -> list[str]:
    return [w for w in words if any(t in w for t in terms)]


def score_day(ctx: Context, d: date, purpose: str, hour: int | None = None) -> dict:
    cfg = PURPOSES.get(purpose, PURPOSES["general"])
    reasons: list[dict] = []
    def add(src: str, delta: float, text: str):
        reasons.append({"src": src, "delta": round(delta, 1), "text": text})
    score = 0.0
    noon = datetime(d.year, d.month, d.day, hour if hour is not None else 12, 0)

    # --- 黃曆 ---
    alm = almanac(noon)
    if alm:
        yi_hit = _match(cfg["yi"], alm["yi"]); ji_hit = _match(cfg["ji"], alm["ji"])
        if yi_hit:
            score += 2; add("黃曆", +2, "宜 " + "、".join(yi_hit))
        if ji_hit:
            score -= 3; add("黃曆", -3, "忌 " + "、".join(ji_hit))
        jc = alm["jianchu"]
        if jc in cfg["jianchu_good"]:
            score += 1; add("黃曆", +1, f"建除「{jc}」日宜{cfg['zh']}")
        elif jc in cfg["jianchu_bad"]:
            score -= 1; add("黃曆", -1, f"建除「{jc}」日不宜{cfg['zh']}")
        xiu_luck = "吉" if "吉" in alm["xiu"] else "凶" if "凶" in alm["xiu"] else ""
        if xiu_luck:
            score += 0.5 if xiu_luck == "吉" else -0.5; add("黃曆", 0.5 if xiu_luck == "吉" else -0.5, f"二十八宿 {alm['xiu']}")
        jn, xs = min(len(alm["jishen"]), 5) * 0.3, min(len(alm["xiongsha"]), 5) * 0.3
        score += jn - xs
        if alm["jishen"]:
            add("黃曆", jn, "吉神 " + "、".join(alm["jishen"][:5]))
        if alm["xiongsha"]:
            add("黃曆", -xs, "凶煞 " + "、".join(alm["xiongsha"][:5]))
        pz = [t for t in alm["pengzu"] if any(k in t for k in cfg["ji"][:3])]
        if pz:
            score -= 1; add("黃曆", -1, "彭祖百忌 " + "；".join(pz))

    # --- 八字 流日 ---
    lr = X.liuri(ctx.full, d, ctx.tz)
    if lr["clash_natal_day"]:
        score -= 4; add("八字", -4, f"流日 {lr['branch']} 沖本命日柱 {ctx.full['pillars'][2]['branch']}（日沖，大忌）")
    if lr["clash_year"]:
        score -= 3; add("八字", -3, f"流日 {lr['branch']} 沖太歲（歲破）")
    if lr["clash_month"]:
        score -= 2; add("八字", -2, f"流日 {lr['branch']} 沖月建（月破）")
    if lr["in_natal_kong"]:
        score -= 1; add("八字", -1, f"流日 {lr['branch']} 落本命日柱旬空")
    if lr["nature"] == "favourable":
        score += 1.5; add("八字", +1.5, f"流日 {lr['gz']} 天干{lr['elem']}為喜用（{lr['stem_god']}）")
    else:
        score -= 1; add("八字", -1, f"流日 {lr['gz']} 天干{lr['elem']}為忌（{lr['stem_god']}）")
    db = ctx.full["pillars"][2]["branch"]
    he = [n for n in lr["branch_notes"] if n.startswith((db + lr["branch"], lr["branch"] + db)) and ("合" in n) and "暗合" not in n]
    if he and not lr["clash_natal_day"]:
        score += 1; add("八字", +1, "流日合本命日支：" + "、".join(he))
    good = [s for s in lr["shensha"] if s in cfg["shensha_good"]]
    bad = [s for s in lr["shensha"] if s in cfg["shensha_bad"]]
    if good:
        score += min(len(good), 2) * 0.8; add("八字", min(len(good), 2) * 0.8, "流日神煞 " + "、".join(good))
    if bad:
        score -= min(len(bad), 2) * 0.6; add("八字", -min(len(bad), 2) * 0.6, "流日神煞 " + "、".join(bad))

    # --- 紫微 流日四化 ---
    zw = None
    if ctx.iztro is not None and ctx.star_palace:
        try:
            hs = ctx.iztro.horoscope(f"{d.year}-{d.month}-{d.day}", (hour + 1) // 2 % 12 if hour is not None else 6)
            mut = list(hs.daily.mutagen)
            landing = {k: ctx.star_palace.get(st, "?") for k, st in zip("祿權科忌", mut)}
            zw = {"gz": hs.daily.heavenly_stem + hs.daily.earthly_branch, "mutagen": [f"{st}化{k}" for k, st in zip("祿權科忌", mut)], "landing": landing}
            pal = cfg["palace"]
            goods = [k for k in "祿權科" if landing.get(k) == pal]
            if goods:
                score += 1; add("紫微", +1, f"流日化{'/'.join(goods)}入{pal}宮")
            if landing.get("忌") == pal:
                score -= 1.5; add("紫微", -1.5, f"流日化忌入{pal}宮")
        except Exception:  # noqa: BLE001
            zw = None

    # --- 奇門 ---
    qm = Q.cast_hour(noon, ctx.tz)
    cls = qm["gate_class"]
    score += 1 if cls == "三吉門" else -1 if cls == "凶門" else 0
    add("奇門", 1 if cls == "三吉門" else -1 if cls == "凶門" else 0, f"{qm['ju_label']} 值使 {qm['zhishi']}（{cls}）")
    lucky = [f"{p['direction']}（{p['gate']}{'・' + p['sky_stem'] + '奇' if p['sky_stem'] in '乙丙丁' else ''}）"
             for p in qm["palaces"] if p["palace"] != 5 and p["gate_cls"] != "凶" and (p["gate_cls"] == "吉" or p["sky_stem"] in "乙丙丁")]
    unlucky = [f"{p['direction']}（{p['gate']}）" for p in qm["palaces"] if p["palace"] != 5 and p["gate_cls"] == "凶"]

    # --- 小六壬 ---
    hb = ((noon.hour + 1) // 2) % 12
    lunar = X.lunar_info(d, hb)
    idx = ((lunar["month"] - 1) + (lunar["day"] - 1) + hb) % 6
    xl = XLR[idx]
    score += 0.5 if xl[3] == "吉" else -0.5
    add("小六壬", 0.5 if xl[3] == "吉" else -0.5, f"{xl[0]}（{xl[3]}）")

    grade, verdict = _grade(score)
    hard_avoid = lr["clash_natal_day"] or lr["clash_year"] or (alm and _match(cfg["ji"], alm["ji"]) and purpose == "surgery")
    if hard_avoid and grade > 2:
        grade, verdict = 1, "忌"
    return {
        "date": d.isoformat(), "weekday": "週" + _WEEK[d.weekday()], "lunar": (lunar["text"].split("）")[1][:-2] if "）" in lunar["text"] else lunar["text"]),   # drop 「x時」
        "gz": {"year": lr["year_gz"], "month": lr["month_gz"], "day": lr["gz"]},
        "score": round(score, 1), "grade": grade, "verdict": verdict, "hard_avoid": bool(hard_avoid),
        "reasons": sorted(reasons, key=lambda r: -abs(r["delta"])),
        "almanac": {k: alm[k] for k in ("yi", "ji", "jishen", "xiongsha", "jianchu", "xiu", "positions")} if alm else None,
        "bazi": {"gz": lr["gz"], "stem_god": lr["stem_god"], "nature": lr["nature"], "shensha": lr["shensha"], "notes": lr["branch_notes"], "kong_wang": lr["kong_wang"], "changsheng": lr["changsheng"]},
        "ziwei": zw, "qimen": {"ju": qm["ju_label"], "zhishi": qm["zhishi"], "cls": cls, "lucky_dirs": lucky, "unlucky_dirs": unlucky},
        "xiaoliuren": xl[0],
    }


def score_hours(ctx: Context, d: date, purpose: str) -> list[dict]:
    out = []
    lunar_m, lunar_d = X.lunar_info(d, 0)["month"], X.lunar_info(d, 0)["day"]
    for h in X.liushi(ctx.full, d, ctx.tz):
        hb = X.BRANCHES.index(h["branch"])
        sc, why = 0.0, []
        if h["clash_day"]:
            sc -= 2; why.append("時沖日支")
        if h["clash_natal_day"]:
            sc -= 2; why.append("時沖本命日支")
        if h["he_day"] or h["he_natal_day"]:
            sc += 1; why.append("時合日支")
        sc += 1 if h["nature"] == "favourable" else -0.5
        why.append(f"時干{'喜用' if h['nature'] == 'favourable' else '忌'}（{h['stem_god']}）")
        clock = (hb * 2 + 23) % 24
        qm = Q.cast_hour(datetime(d.year, d.month, d.day, clock, 30), ctx.tz)
        cls = qm["gate_class"]
        sc += 1 if cls == "三吉門" else -1 if cls == "凶門" else 0
        why.append(f"奇門值使{qm['zhishi']}（{cls}）")
        xl = XLR[((lunar_m - 1) + (lunar_d - 1) + hb) % 6]
        sc += 0.5 if xl[3] == "吉" else -0.5
        why.append(f"小六壬{xl[0]}")
        out.append({**h, "score": round(sc, 1), "reasons": why})
    ranked = sorted(out, key=lambda x: -x["score"])
    top = {x["branch"] for x in ranked[:3] if x["score"] > 0}
    for x in out:
        x["best"] = x["branch"] in top
    return out


def select(birth: BirthInput, start: date, end: date, purpose: str, top: int = 10) -> dict:
    ctx = Context(birth)
    days = [score_day(ctx, start + timedelta(days=i), purpose) for i in range((end - start).days + 1)]
    ranked = sorted(days, key=lambda x: (-x["grade"], -x["score"]))
    best = [x for x in ranked if not x["hard_avoid"]][:top]
    for x in best:
        x["hours"] = score_hours(ctx, date.fromisoformat(x["date"]), purpose)
    cfg = PURPOSES.get(purpose, PURPOSES["general"])
    return {
        "purpose": purpose, "purpose_label": f"{cfg['zh']} / {cfg['en']}", "start": start.isoformat(), "end": end.isoformat(),
        "subject": birth.label(), "days": days, "best": [x["date"] for x in best],
        "avoid": [x["date"] for x in days if x["grade"] == 1],
        "rules": ["黃曆宜忌 ±2/−3、建除 ±1、二十八宿 ±0.5、吉神凶煞各 ±0.3/個（上限 5）、彭祖百忌 −1",
                  "八字：流日天干喜用 +1.5／忌 −1；沖本命日柱 −4、歲破 −3、月破 −2、落旬空 −1、合日支 +1；本題神煞 ±0.8/0.6",
                  f"紫微：流日化祿權科入{cfg['palace']}宮 +1、化忌 −1.5", "奇門：值使三吉門 +1／凶門 −1；另列當日吉方", "小六壬 ±0.5",
                  "★5 ≥5 分、★4 ≥3、★3 ≥1、★2 ≥−1、★1 其餘；沖日柱或歲破直接列為忌日"],
        "ziwei_available": ctx.iztro is not None, "almanac_available": days[0]["almanac"] is not None if days else False,
    }


def day_outlook(birth: BirthInput, d: date, hour: int | None = None) -> dict:
    """今日運勢: the general-purpose day score + 12 hours + the 流年/流月 context."""
    ctx = Context(birth)
    out = score_day(ctx, d, "general", hour)
    out["hours"] = score_hours(ctx, d, "general")
    cur_dy = next((x for x in ctx.full["dayun"] if x["current"]), None)
    cur_ln = next((l for x in ctx.full["dayun"] for l in x["liunian"] if l["year"] == d.year), None)
    out["context"] = {"dayun": f"{cur_dy['gz']}（{cur_dy['stem_god']}・{cur_dy['nature']}）" if cur_dy else None,
                      "liunian": f"{cur_ln['year']} {cur_ln['gz']}（{cur_ln['stem_god']}・{cur_ln['nature']}）" if cur_ln else None,
                      "liuyue": out["gz"]["month"], "strength": ctx.full["strength"]["label"], "favourable": ctx.full["strength"]["favourable"]}
    return out
