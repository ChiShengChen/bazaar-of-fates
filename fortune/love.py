"""感情專科 / The love-specialist reader — one question type, read deeply instead of widely.

  classify(question)                  → sub-intent: timing | match | reconcile | breakup | marriage | affair | current
  natal(charts, male)                 → 命：感情格局 — 八字 配偶星/夫妻宮(日支)/桃花神煞, 紫微 夫妻宮三方四正 + 桃花曜,
                                         西洋 金星/火星/七宮, Jyotiṣa 七宮/Śukra — each with a scored, listed verdict
  timing(birth, charts, start, count) → 運：桃花年/婚緣年 — every year scored from 八字 流年 (配偶星透干, 紅鸞天喜,
                                         合/沖夫妻宮), 紫微 流年四化入夫妻宮 + 流年夫妻宮坐紅鸞天喜, 西洋 木土行運對金星/七宮,
                                         Jyotiṣa daśā — every +/− listed
  match(a, b)                         → 合婚：八字 (日柱 干合支合/沖刑害, 生肖, 喜用互補, 夫妻星) + 西洋 synastry
                                         (日月金火土 cross-aspects), scored with reasons
  consult(birth, question, partner…)  → the whole consultation: profile + timing (+ match) + the reading

Everything but the prose is deterministic and auditable; the 命理師 prompt (prompts/love/) is told to read
only from these facts, answer the sub-question first, and never to pronounce fate.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import ephem

from fortune import astro_ext as AX
from fortune import bazi_ext as X
from fortune import casting
from fortune import focus as F
from fortune.birth import BirthInput
from fortune.engines.astrology import astro
from fortune.engines.ziwei import ziwei as ZW
from fortune.schemas import Chart
from fortune.shared.llm import complete

_PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "love" / "love_master.md"

INTENTS = {
    "timing": {"zh": "何時有緣（桃花／婚緣時機）", "en": "when — timing of love / marriage",
               "kw": ["何時", "什麼時候", "甚麼時候", "幾歲", "哪一年", "那一年", "今年", "明年", "桃花", "脫單", "有對象", "遇到", "正緣", "會不會遇", "when", "year", "single", "meet"]},
    "match": {"zh": "合不合（合婚／合盤）", "en": "compatibility — is this person right for me",
              "kw": ["合不合", "適合", "合婚", "合盤", "相配", "配不配", "我們", "他跟我", "她跟我", "跟他", "跟她", "和他", "和她", "compatib", "match", "together", "right for me"]},
    "reconcile": {"zh": "復合", "en": "reconciliation with an ex",
                  "kw": ["復合", "回來", "再聯絡", "前任", "前男友", "前女友", "挽回", "ex ", "ex-", "back together", "get back"]},
    "breakup": {"zh": "該不該分開", "en": "whether to end it",
                "kw": ["分手", "離婚", "結束", "離開", "該不該分", "放下", "breakup", "break up", "divorce", "leave", "end it"]},
    "marriage": {"zh": "婚姻", "en": "marriage",
                 "kw": ["結婚", "婚姻", "求婚", "娶", "嫁", "成家", "婚後", "marry", "marriage", "wedding", "husband", "wife", "spouse"]},
    "affair": {"zh": "第三者／曖昧", "en": "a third party / ambiguity",
               "kw": ["第三者", "小三", "外遇", "劈腿", "曖昧", "出軌", "偷吃", "affair", "cheat", "someone else", "flirt"]},
    "current": {"zh": "現況（這段關係）", "en": "the current relationship", "kw": []},
}
_SPOUSE_STAR = {True: ["正財", "偏財"], False: ["正官", "七殺"], None: ["正財", "偏財", "正官", "七殺"]}
_PEACH = ("桃花", "紅鸞", "天喜")
_LONELY = ("孤辰", "寡宿")
_ZW_STEADY = {"天同", "天相", "天府", "太陰", "天梁", "紫微"}
_ZW_ROUGH = {"貪狼", "廉貞", "七殺", "破軍", "巨門", "武曲"}
_ZW_PEACH = {"紅鸞", "天喜", "天姚", "咸池", "沐浴"}
_SHA = {"擎羊", "陀羅", "火星", "鈴星", "地空", "地劫"}
_HARM = {"trine", "sextile"}
_HARD = {"square", "opposition"}
_B = "子丑寅卯辰巳午未申酉戌亥"


def _grade(score: float) -> tuple[int, str]:
    return (5, "上吉") if score >= 5 else (4, "吉") if score >= 3 else (3, "可") if score >= 1 else (2, "平") if score >= -1 else (1, "宜守")


def _verdict(score: float, hi: float = 1, lo: float = -1) -> str:
    return "favourable" if score >= hi else "unfavourable" if score <= lo else "neutral"


def _male(birth: BirthInput) -> bool | None:
    return X._is_male(birth)


# --- the question ---------------------------------------------------------------------------

def classify(question: str | None, *, has_partner: bool = False) -> str:
    """Sub-intent of a love question. A partner birth pins it to `match` unless the words say otherwise."""
    if not question:
        return "match" if has_partner else "current"
    q = question.lower()
    best, score = "current", 0
    for key, t in INTENTS.items():
        s = sum(1 for k in t["kw"] if k.lower() in q)
        if s > score:
            best, score = key, s
    if best == "current" and has_partner:
        return "match"
    return best


def intent_label(intent: str) -> str:
    t = INTENTS.get(intent, INTENTS["current"])
    return f"{t['zh']} / {t['en']}"


# --- 命：natal disposition -------------------------------------------------------------------

def _bazi_natal(c: dict, male: bool | None) -> dict:
    pillars = c.get("pillars", [])
    day = next((p for p in pillars if p.get("role") == "day"), None) or pillars[2]
    stars = _SPOUSE_STAR[male]
    db = day["branch_idx"]
    score, reasons = 0.0, []
    seen = []
    for p in pillars:
        if p.get("stem_god") in stars:
            seen.append(f"{p['pillar']}干{p['stem']}（{p['stem_god']}）")
        for i, h in enumerate(p.get("hidden", [])):
            if h["god"] in stars:
                seen.append(f"{p['pillar']}支藏{h['stem']}（{h['god']}{'・本氣' if i == 0 else ''}）")
    day_hidden = day.get("hidden", [])
    spouse_in_palace = any(h["god"] in stars for h in day_hidden)
    if spouse_in_palace:
        score += 1.5
        reasons.append(f"配偶星坐夫妻宮（日支{day['branch']}藏{'/'.join(h['stem'] + h['god'] for h in day_hidden if h['god'] in stars)}）→ 配偶緣分直接、對方貼近")
    transparent = [p for p in pillars if p.get("stem_god") in stars and p["role"] != "day"]
    if transparent:
        score += 1
        reasons.append(f"配偶星透干（{'、'.join(p['pillar'] + '干' + p['stem_god'] for p in transparent)}）→ 感情緣分明顯、易被看見")
    if len(seen) >= 4:
        score -= 0.5
        reasons.append(f"配偶星多見（{len(seen)} 處）→ 選擇多、也易同時有競爭或拉扯")
    if not seen:
        score -= 1
        reasons.append("原局不見配偶星 → 緣分來得較晚或需靠行運引動，宜主動")
    # 夫妻宮 (日支) relations with the other three branches
    others = [p["branch_idx"] for p in pillars if p["role"] != "day"]
    for ob, role in zip(others, [p["pillar"] for p in pillars if p["role"] != "day"]):
        a, b = sorted((db, ob))
        if (db - ob) % 12 == 6:
            score -= 1.5
            reasons.append(f"夫妻宮逢沖（{role}支{_B[ob]}沖日支{_B[db]}）→ 關係易動盪、聚少離多或先合後分")
        elif (a, b) in X._LIUHE:
            score += 1
            reasons.append(f"夫妻宮逢合（{role}支{_B[ob]}六合日支{_B[db]}）→ 關係有黏著、合得來")
        elif (a, b) in X._HAI:
            score -= 0.5
            reasons.append(f"夫妻宮逢害（{role}支{_B[ob]}害日支{_B[db]}）→ 相處易有暗傷、小事積怨")
        elif a == b and a in X._ZIXING:
            score -= 0.5
            reasons.append(f"夫妻宮自刑（{_B[db]}{_B[db]}）→ 自我拉扯、想太多")
    if _B[db] in (c.get("pillars", [{}])[0].get("kong_wang", "") or ""):
        score -= 1
        reasons.append(f"夫妻宮坐空亡（年柱旬空 {c['pillars'][0].get('kong_wang')}）→ 感情易有空等、虛應")
    peach = [s for p in pillars for s in p.get("shensha", []) if s in _PEACH]
    lonely = [s for p in pillars for s in p.get("shensha", []) if s in _LONELY]
    if peach:
        score += min(2, len(peach))
        reasons.append(f"桃花類神煞：{'、'.join(dict.fromkeys(peach))} → 異性緣、魅力明顯")
    if lonely:
        score -= len(lonely)
        reasons.append(f"孤辰／寡宿：{'、'.join(dict.fromkeys(lonely))} → 慣於獨處、對親密有保留")
    if day.get("changsheng") == "沐浴":
        reasons.append("日主坐沐浴（桃花煞）→ 感情上易多情、需自我把持")
    gods = [p.get("stem_god") for p in pillars if p["role"] != "day"]
    if male is False and "傷官" in gods and "正官" in gods:
        score -= 1
        reasons.append("女命傷官見官 → 易挑剔或與另一半對立，婚姻需多溝通")
    if male and gods.count("比肩") + gods.count("劫財") >= 2 and any(g in ("正財", "偏財") for g in gods):
        score -= 1
        reasons.append("男命比劫爭財 → 感情易有競爭者、宜專一經營")
    if day.get("gz") in ("庚辰", "壬辰", "戊戌", "庚戌"):
        reasons.append("日柱魁罡 → 個性剛強、感情中宜柔軟")
    facts = {
        "日主": f"{day['stem']}{day['stem_elem']}（{c.get('day_master', {}).get('yinyang', '')}）",
        "配偶星": "、".join(stars) + ("（男命以財星為妻星）" if male else "（女命以官殺為夫星）" if male is False else "（性別未填，財官並看）"),
        "配偶星所在": seen or "原局未見",
        "夫妻宮（日支）": f"{day['branch']}：藏 " + "、".join(f"{h['stem']}{h['god']}" for h in day_hidden) + f"・{day.get('changsheng', '')}・納音{day.get('nayin', '')}",
        "桃花類神煞": list(dict.fromkeys(peach)) or "無", "孤寡": list(dict.fromkeys(lonely)) or "無",
        "旺衰喜用": f"{c.get('strength', {}).get('label', '')}・喜 {'/'.join(c.get('strength', {}).get('favourable', []))}",
    }
    return {"system": "bazi", "system_zh": "八字", "score": round(score, 1), "verdict": _verdict(score), "reasons": reasons, "facts": facts}


def _ziwei_natal(c: dict) -> dict:
    palaces = c.get("palaces", [])
    by_name = {p["name"]: p for p in palaces}
    by_branch = {p["branch"]: p for p in palaces}
    pal = by_name.get("夫妻")
    if not pal:
        return {"system": "ziwei", "system_zh": "紫微", "score": 0, "verdict": "neutral", "reasons": ["無夫妻宮"], "facts": {}}
    bi = _B.index(pal["branch"])
    opp = by_branch[_B[(bi + 6) % 12]]
    trine = [by_branch[_B[(bi + 4) % 12]], by_branch[_B[(bi + 8) % 12]]]
    life = by_name.get("命宮", {})
    bare = lambda s: s.split("(")[0]  # noqa: E731
    majors = [bare(s) for s in pal.get("stars", []) if bare(s) in _ZW_STEADY | _ZW_ROUGH]
    score, reasons = 0.0, []
    if not majors:
        bm = [bare(s) for s in opp.get("stars", []) if bare(s) in _ZW_STEADY | _ZW_ROUGH]
        reasons.append(f"夫妻宮無主星，借對宮{opp['name']}（{'、'.join(bm) or '空'}）→ 感情受外在、對方主導較多")
        majors = bm
        score -= 0.5
    steady = [m for m in majors if m in _ZW_STEADY]
    rough = [m for m in majors if m in _ZW_ROUGH]
    if steady:
        score += 1
        reasons.append(f"夫妻宮主星 {'、'.join(steady)} → 配偶溫和、關係求穩")
    if rough:
        score -= 1
        reasons.append(f"夫妻宮主星 {'、'.join(rough)} → 感情起伏大、對方個性強或緣分晚成")
    tags = {bare(s): s[s.find("(") + 1:-1] for s in pal.get("stars", []) if "(" in s}
    if "祿" in tags.values():
        score += 1
        reasons.append(f"生年化祿在夫妻宮（{next(k for k, v in tags.items() if v == '祿')}）→ 因情得福、配偶助力")
    if "忌" in tags.values():
        score -= 1.5
        reasons.append(f"生年化忌在夫妻宮（{next(k for k, v in tags.items() if v == '忌')}）→ 感情是此生功課，易糾結、晚婚較穩")
    sha = [bare(s) for s in pal.get("stars", []) if bare(s) in _SHA]
    if len(sha) >= 2:
        score -= 1
        reasons.append(f"夫妻宮煞星 {'、'.join(sha)} → 關係多磨、宜慢熱")
    elif sha:
        score -= 0.5
        reasons.append(f"夫妻宮見{sha[0]} → 關係中有一項持續的摩擦")
    peach_pal = list(dict.fromkeys(bare(s) for s in pal.get("stars", []) + pal.get("adjective_stars", []) if bare(s) in _ZW_PEACH))
    peach_life = list(dict.fromkeys(bare(s) for s in life.get("stars", []) + life.get("adjective_stars", []) if bare(s) in _ZW_PEACH))
    if peach_pal or peach_life:
        score += 1
        reasons.append(f"桃花曜（夫妻宮 {'、'.join(peach_pal) or '—'}；命宮 {'、'.join(peach_life) or '—'}）→ 異性緣佳")
    lonely = list(dict.fromkeys(bare(s) for s in pal.get("stars", []) + pal.get("adjective_stars", []) if bare(s) in _LONELY))
    if lonely:
        score -= 0.5
        reasons.append(f"夫妻宮見{'、'.join(lonely)} → 感情中有距離感")
    def stars(p):
        return "、".join(p.get("stars", [])) or "空宮"
    facts = {
        "夫妻宮": f"{pal['stem']}{pal['branch']}：{stars(pal)}",
        "亮度": pal.get("brightness") or "—", "雜曜": pal.get("adjective_stars") or "—",
        "對宮（官祿）": f"{opp['name']}：{stars(opp)}", "三方": {p["name"]: stars(p) for p in trine},
        "命宮": stars(life), "身宮": next((p["name"] for p in palaces if p.get("is_body")), ""),
    }
    return {"system": "ziwei", "system_zh": "紫微", "score": round(score, 1), "verdict": _verdict(score), "reasons": reasons, "facts": facts}


def _astro_natal(ch: Chart) -> dict:
    c = ch.chart
    planets = {p["body"]: p for p in c.get("planets", [])}
    asp = c.get("aspects_detail", [])
    score, reasons = 0.0, []
    ven, mars, moon = planets.get("Venus"), planets.get("Mars"), planets.get("Moon")
    def aspects_of(body):
        return [x for x in asp if body in (x["a"], x["b"])]
    va = aspects_of("Venus")
    harm = [x for x in va if x["type"] in _HARM or (x["type"] == "conjunction" and {x["a"], x["b"]} & {"Jupiter", "Moon", "Sun", "Mars"})]
    hard = [x for x in va if x["type"] in _HARD or (x["type"] == "conjunction" and "Saturn" in (x["a"], x["b"]))]
    for x in harm:
        other = x["b"] if x["a"] == "Venus" else x["a"]
        score += 1 if other in ("Jupiter", "Moon", "Mars") else 0.5
        reasons.append(f"Venus {x['type']} {other}（{x['orb']}°）→ {'愛得慷慨、人緣好' if other == 'Jupiter' else '吸引力強、熱情' if other == 'Mars' else '情感柔軟、重感覺' if other == 'Moon' else '討喜'}")
    for x in hard:
        other = x["b"] if x["a"] == "Venus" else x["a"]
        score -= 1 if other == "Saturn" else 0.5
        reasons.append(f"Venus {x['type']} {other}（{x['orb']}°）→ {'慢熱、怕受傷、把承諾看得很重' if other == 'Saturn' else '愛與欲望拉扯、易衝動' if other == 'Mars' else '情感需求與愛的方式不同步' if other == 'Moon' else '愛與自我之間拉扯'}")
    if ch.ascendant:
        cusps = {h["house"]: h for h in ch.ascendant.get("houses", [])}
        seven = cusps.get(7, {})
        ruler = F._RULER.get(seven.get("sign", ""))
        rp = planets.get(ruler)
        in7 = [p for p in planets.values() if p.get("house") == 7]
        in5 = [p for p in planets.values() if p.get("house") == 5]
        if in7:
            names = "、".join(p["body"] for p in in7)
            if any(p["body"] in ("Venus", "Jupiter", "Moon", "Sun") for p in in7):
                score += 1
            if any(p["body"] == "Saturn" for p in in7):
                score -= 0.5
            reasons.append(f"七宮（伴侶宮）有 {names} → {'伴侶是人生重心、緣分明顯' if any(p['body'] in ('Venus', 'Jupiter', 'Sun') for p in in7) else '伴侶關係帶著責任與考驗、晚婚較穩' if any(p['body'] == 'Saturn' for p in in7) else '伴侶關係火熱但易爭' if any(p['body'] == 'Mars' for p in in7) else '伴侶關係重溝通'}")
        if rp:
            r_asp = aspects_of(ruler)
            h, d = sum(1 for x in r_asp if x["type"] in _HARM), sum(1 for x in r_asp if x["type"] in _HARD)
            score += 0.5 if h > d else -0.5 if d > h else 0
            reasons.append(f"七宮主 {ruler} 在 {rp['sign']} 第{rp.get('house')}宮（和諧{h}／緊張{d}）→ 伴侶多來自{'事業/社交圈' if rp.get('house') in (10, 11) else '朋友或學習場合' if rp.get('house') in (3, 9) else '日常生活/工作場合' if rp.get('house') in (6, 2) else '親近的生活圈'}")
        facts7 = {"七宮": f"{seven.get('sign')} {seven.get('sign_zh', '')}", "七宮內行星": [f"{p['body']} {p['sign']}" for p in in7] or "空",
                  "五宮（戀愛宮）": [f"{p['body']} {p['sign']}" for p in in5] or "空", "七宮主": f"{ruler} in {rp['sign']} H{rp.get('house')}" if rp else "—"}
    else:
        facts7 = {"註": "無時辰／出生地，無宮位：只看金星、火星、月亮與相位"}
    facts = {"金星 Venus（愛的方式）": f"{ven['sign']} {ven['sign_zh']}" + (f" H{ven['house']}" if ven and ven.get("house") else "") if ven else "—",
             "火星 Mars（欲望／追求）": f"{mars['sign']} {mars['sign_zh']}" + (f" H{mars['house']}" if mars and mars.get("house") else "") if mars else "—",
             "月亮 Moon（情感需求）": f"{moon['sign']} {moon['sign_zh']}" + (f" H{moon['house']}" if moon and moon.get("house") else "") if moon else "—",
             "金星相位": [f"{x['a']} {x['type']} {x['b']} ({x['orb']}°)" for x in va] or "無", **facts7}
    return {"system": "astrology", "system_zh": "西洋占星", "score": round(score, 1), "verdict": _verdict(score), "reasons": reasons, "facts": facts}


def _jyotish_natal(ch: Chart) -> dict:
    grahas = {g["graha"]: g for g in ch.chart.get("grahas", [])}
    score, reasons = 0.0, []
    facts = {"Śukra（金星）": f"{grahas['Venus']['rashi']}" + (f" B{grahas['Venus'].get('bhava')}" if grahas.get("Venus", {}).get("bhava") else "") if "Venus" in grahas else "—",
             "月宿": ch.readings.get("moon_nakshatra"), "現行 daśā": f"{ch.readings.get('mahadasha_lord')}（{ch.readings.get('dasha_nature')}）"}
    lord7 = None
    if ch.ascendant:
        hs = {h["house"]: h["rashi"] for h in ch.ascendant.get("houses", [])}
        lord7 = F._VEDIC_RULER.get(hs.get(7, ""))
        lp = grahas.get(lord7)
        in7 = [g for g in grahas.values() if g.get("bhava") == 7]
        facts["第七 bhāva"] = f"{hs.get(7)}；內有 {'、'.join(g['graha'] for g in in7) or '無'}"
        if lp:
            facts["七宮主"] = f"{lord7} in {lp['rashi']} B{lp.get('bhava')}"
            if lp.get("bhava") in (6, 8, 12):
                score -= 1
                reasons.append(f"七宮主 {lord7} 落 dusthāna B{lp['bhava']} → 伴侶關係需多經營、晚成較穩")
            elif lp.get("bhava") in (1, 4, 5, 7, 9, 10, 11):
                score += 1
                reasons.append(f"七宮主 {lord7} 落 B{lp['bhava']}（吉位）→ 伴侶緣分有支撐")
        if any(g["graha"] in ("Saturn", "Rahu", "Ketu", "Mars") for g in in7):
            score -= 0.5
            reasons.append(f"第七 bhāva 見 {'、'.join(g['graha'] for g in in7 if g['graha'] in ('Saturn', 'Rahu', 'Ketu', 'Mars'))} → 傳統視為婚姻需審慎擇日、擇人")
        if any(g["graha"] in ("Venus", "Jupiter", "Moon") for g in in7):
            score += 0.5
            reasons.append("第七 bhāva 見吉曜 → 伴侶溫和")
    else:
        facts["註"] = "無時辰／出生地，無 bhāva：只看 Śukra 與 daśā"
    v = grahas.get("Venus")
    if v and v.get("bhava") in (6, 8, 12):
        score -= 0.5
        reasons.append(f"Śukra 落 B{v['bhava']} → 愛裡容易付出多、回報慢")
    return {"system": "jyotish", "system_zh": "Jyotiṣa", "score": round(score, 1), "verdict": _verdict(score), "reasons": reasons, "facts": facts, "lord7": lord7}


def natal(charts: dict[str, Chart], male: bool | None) -> dict:
    """命：the four systems that have a natal 夫妻宮 / 7th house, each scored on love disposition."""
    rows = []
    if "bazi" in charts:
        rows.append(_bazi_natal(charts["bazi"].chart, male))
    if "ziwei" in charts:
        rows.append(_ziwei_natal(charts["ziwei"].chart))
    if "astrology" in charts:
        rows.append(_astro_natal(charts["astrology"]))
    if "jyotish" in charts:
        rows.append(_jyotish_natal(charts["jyotish"]))
    total = sum(r["score"] for r in rows)
    g, label = _grade(total)
    return {"systems": rows, "score": round(total, 1), "grade": g, "label": label,
            "summary": "命中感情格局：" + "；".join(f"{r['system_zh']}{F.VERDICT_ZH[r['verdict']]}" for r in rows) + f" → 合計 {total:+.1f}（{label}）"}


# --- 運：the years ---------------------------------------------------------------------------

def _bazi_year(full: dict, yr: int, male: bool | None) -> tuple[list[dict], dict | None]:
    stars = _SPOUSE_STAR[male]
    ln = next((l for d in full["dayun"] for l in d["liunian"] if l["year"] == yr), None)
    dy = next((d for d in full["dayun"] if d["start_year"] <= yr <= d["end_year"]), None)
    if not ln:
        return [], None
    day = full["pillars"][2]
    db, lb = day["branch_idx"], _B.index(ln["gz"][1])
    rs: list[dict] = []
    def add(delta, text):
        rs.append({"src": "八字", "delta": delta, "text": text})
    if ln["stem_god"] in stars:
        add(2, f"流年{ln['gz']}透{ln['stem_god']}（配偶星）→ 正緣／婚緣易現")
    elif ln["hidden"] and ln["hidden"][0]["god"] in stars:
        add(1, f"流年支{ln['gz'][1]}本氣藏{ln['hidden'][0]['god']}（配偶星）→ 有緣但不明顯，需主動")
    for s in ln.get("shensha", []):
        if s in ("紅鸞", "天喜"):
            add(2, f"流年逢{s}（婚喜之星）→ 喜事、訂婚結婚之應")
        elif s == "桃花":
            add(1, "流年逢桃花 → 異性緣、新對象")
        elif s in _LONELY:
            add(-1, f"流年逢{s} → 感情上較孤單、少社交")
    a, b = sorted((db, lb))
    if (lb - db) % 12 == 6:
        add(-2, f"流年{_B[lb]}沖夫妻宮（日支{_B[db]}）→ 關係動盪、分合、或搬遷分隔")
    elif (a, b) in X._LIUHE:
        add(1.5, f"流年{_B[lb]}六合夫妻宮（日支{_B[db]}）→ 關係拉近、定下來之應")
    elif X._SANHE_GROUP.get(lb) == X._SANHE_GROUP.get(db) and lb != db:
        add(1, f"流年{_B[lb]}三合夫妻宮（日支{_B[db]}）→ 合緣、貴人介紹")
    elif (a, b) in X._HAI:
        add(-0.5, f"流年{_B[lb]}害夫妻宮 → 相處易生嫌隙")
    elif lb == db:
        add(-0.5, f"流年{_B[lb]}伏吟夫妻宮 → 感情原地踏步、舊事重提")
    add(1 if ln["nature"] == "favourable" else -1, f"流年{ln['gz']}為{'喜用' if ln['nature'] == 'favourable' else '忌耗'}五行 → 整體{'順' if ln['nature'] == 'favourable' else '需忍耐'}")
    if male is False and ln["stem_god"] == "傷官":
        add(-1, "女命流年傷官（剋官星）→ 易與另一半對立、單身者挑剔")
    if male and ln["stem_god"] in ("比肩", "劫財"):
        add(-1, "男命流年比劫（爭財）→ 感情易有競爭者或因錢起爭")
    if dy and dy["stem_god"] in stars:
        add(1, f"大運{dy['gz']}透{dy['stem_god']}（配偶星，{dy['start_year']}–{dy['end_year']}）→ 十年感情運底色佳")
    ctx = {"流年": f"{ln['gz']}（{ln['stem_god']}・{ln['nature']}）", "神煞": ln.get("shensha", []), "大運": f"{dy['gz']}（{dy['stem_god']}）" if dy else None, "age": ln["age"]}
    return rs, ctx


def _ziwei_year(natal_chart: dict, yr: int) -> tuple[list[dict], dict]:
    stem = X.STEMS[(yr - 4) % 10]
    lyb = (yr - 4) % 12
    mut = ZW.SIHUA[stem]
    sp = natal_chart.get("star_palace", {})
    by_branch = {p["branch"]: p for p in natal_chart.get("palaces", [])}
    bare = lambda s: s.split("(")[0]  # noqa: E731
    rs: list[dict] = []
    def add(delta, text):
        rs.append({"src": "紫微", "delta": delta, "text": text})
    landing = {ZW.HUA[i]: sp.get(mut[i], "?") for i in range(4)}
    for hua, w, why in (("祿", 2, "感情有進展、遇對的人"), ("權", 1, "關係中主導權變化、談婚論嫁"), ("科", 1, "有名分、關係公開"), ("忌", -2, "感情糾結、執著或分離之應")):
        if landing[hua] == "夫妻":
            add(w, f"流年{stem}干 {mut[ZW.HUA.index(hua)]}化{hua}入夫妻宮 → {why}")
    if landing["忌"] == "命宮":
        add(-0.5, f"流年化忌入命宮（{mut[3]}）→ 自己鑽牛角尖、影響關係")
    taisui = by_branch.get(_B[lyb])
    if taisui and taisui["name"] == "夫妻":
        add(1, "流年太歲入本命夫妻宮 → 感情為當年主題")
    peach_t = list(dict.fromkeys(bare(s) for s in (taisui or {}).get("stars", []) + (taisui or {}).get("adjective_stars", []) if bare(s) in ("紅鸞", "天喜", "天姚")))
    if peach_t:
        add(1.5, f"流年命宮坐{'、'.join(peach_t)} → 當年桃花／喜事明顯")
    ln_spouse = by_branch.get(_B[(lyb - 2) % 12])
    peach_s = list(dict.fromkeys(bare(s) for s in (ln_spouse or {}).get("stars", []) + (ln_spouse or {}).get("adjective_stars", []) if bare(s) in ("紅鸞", "天喜", "天姚")))
    if peach_s:
        add(1.5, f"流年夫妻宮（{_B[(lyb - 2) % 12]}）坐{'、'.join(peach_s)} → 婚緣之應")
    sha_s = [bare(s) for s in (ln_spouse or {}).get("stars", []) if bare(s) in _SHA]
    if len(sha_s) >= 2:
        add(-1, f"流年夫妻宮見{'、'.join(sha_s)} → 當年感情多磨")
    return rs, {"流年四化": [f"{mut[i]}化{ZW.HUA[i]}→{landing[ZW.HUA[i]]}" for i in range(4)], "太歲宮": (taisui or {}).get("name"), "流年夫妻宮": _B[(lyb - 2) % 12]}


def _astro_year(ch: Chart, yr: int) -> tuple[list[dict], dict]:
    planets = {p["body"]: p for p in ch.chart.get("planets", [])}
    ven = planets.get("Venus")
    asc = ch.ascendant
    rs: list[dict] = []
    seen: set[str] = set()
    def add(key, delta, text):
        if key in seen:
            return
        seen.add(key)
        rs.append({"src": "西洋", "delta": delta, "text": text})
    ctx = {}
    for body, cls in (("Jupiter", ephem.Jupiter), ("Saturn", ephem.Saturn)):
        for m in (1, 4, 7, 10):
            lon = AX.lon_on(cls, date(yr, m, 1))
            if m == 7:
                ctx[body] = f"{AX.sign_of(lon)} {lon:.0f}°"
            if ven:
                sep = astro._separation(lon, ven["ecliptic_lon"])
                for name, ang in astro._ASPECTS.items():
                    if abs(sep - ang) <= 6:
                        if body == "Jupiter" and name in ("conjunction", "trine", "sextile"):
                            add(f"J-V-{name}", 1.5, f"行運木星 {name} 本命金星（{yr} 年）→ 愛的機會擴張、容易遇見與被愛")
                        elif body == "Jupiter":
                            add(f"J-V-{name}", 0.5, f"行運木星 {name} 本命金星 → 感情放大，注意過度期待")
                        elif body == "Saturn" and name in ("conjunction", "square", "opposition"):
                            add(f"S-V-{name}", -1, f"行運土星 {name} 本命金星（{yr} 年）→ 承諾的考驗：定下來或看清楚")
                        elif body == "Saturn":
                            add(f"S-V-{name}", 0.5, f"行運土星 {name} 本命金星 → 關係踏實、適合長期規劃")
                        break
            if asc:
                h = AX.house_of(lon, asc["longitude"])
                if h == 7:
                    add(f"{body}-H7", 1.5 if body == "Jupiter" else 0, f"行運{'木星' if body == 'Jupiter' else '土星'}過七宮（伴侶宮，{yr} 年）→ {'伴侶緣分擴張、結婚年常見' if body == 'Jupiter' else '關係進入現實檢驗：成熟的定下來，或結束不合的'}")
                if h == 5 and body == "Jupiter":
                    add("J-H5", 1, f"行運木星過五宮（戀愛宮，{yr} 年）→ 戀愛機會、浪漫")
    return rs, ctx


def _jyotish_year(ch: Chart, birth: BirthInput, yr: int, lord7: str | None) -> tuple[list[dict], dict]:
    from fortune import jyotish_ext as JX
    lord = JX.mahadasha_lord(AX.birth_utc(birth), date(yr, 7, 1))
    rs: list[dict] = []
    if lord == "Venus":
        rs.append({"src": "Jyotiṣa", "delta": 1.5, "text": f"Śukra（金星）大運 → 愛情、婚姻、享受為主題（{yr}）"})
    elif lord7 and lord == lord7:
        rs.append({"src": "Jyotiṣa", "delta": 1.5, "text": f"七宮主 {lord} 大運 → 伴侶之事被啟動（{yr}）"})
    elif lord == "Rahu":
        rs.append({"src": "Jyotiṣa", "delta": 0, "text": f"Rāhu 大運 → 感情易遇非典型對象、迷戀（{yr}）"})
    elif lord == "Saturn":
        rs.append({"src": "Jyotiṣa", "delta": -0.5, "text": f"Śani 大運 → 感情步調慢、講責任（{yr}）"})
    return rs, {"daśā": lord}


def timing(birth: BirthInput, charts: dict[str, Chart], start_year: int, count: int = 8) -> dict:
    """運：桃花年／婚緣年 — each year scored across 八字, 紫微, 西洋行運 and Jyotiṣa daśā, every term listed."""
    male = _male(birth)
    full = charts["bazi"].chart if "bazi" in charts else None
    zw = charts.get("ziwei")
    lord7 = _jyotish_natal(charts["jyotish"]).get("lord7") if "jyotish" in charts else None
    years = []
    for yr in range(start_year, start_year + count):
        reasons: list[dict] = []
        ctx: dict = {}
        if full:
            r, c = _bazi_year(full, yr, male)
            reasons += r
            ctx["bazi"] = c
        if zw:
            r, c = _ziwei_year(zw.chart, yr)
            reasons += r
            ctx["ziwei"] = c
        if "astrology" in charts:
            r, c = _astro_year(charts["astrology"], yr)
            reasons += r
            ctx["astrology"] = c
        if "jyotish" in charts:
            r, c = _jyotish_year(charts["jyotish"], birth, yr, lord7)
            reasons += r
            ctx["jyotish"] = c
        score = round(sum(r["delta"] for r in reasons), 1)
        g, label = _grade(score)
        marriage = any(("紅鸞" in r["text"] or "天喜" in r["text"] or "配偶星" in r["text"] or "化祿入夫妻" in r["text"] or "過七宮" in r["text"]) and r["delta"] > 0 for r in reasons)
        years.append({"year": yr, "age": (ctx.get("bazi") or {}).get("age") or (yr - birth.birth_date.year + 1), "score": score, "grade": g, "label": label,
                      "marriage_sign": marriage and score >= 3, "reasons": sorted(reasons, key=lambda r: -abs(r["delta"])), "context": ctx})
    best = [y["year"] for y in sorted(years, key=lambda y: -y["score"]) if y["score"] >= 3][:3]
    caution = [y["year"] for y in years if y["grade"] == 1]
    return {"start_year": start_year, "count": count, "years": years, "best": best, "caution": caution,
            "summary": "桃花／婚緣年：" + ("、".join(f"{y}（{next(x['label'] for x in years if x['year'] == y)}）" for y in best) or "此區間無明顯婚緣年") + (f"；宜守 {'、'.join(map(str, caution))}" if caution else "")}


# --- 合婚 --------------------------------------------------------------------------------------

_PAIR_RULES = {
    ("Venus", "Mars"): {"conjunction": (1.5, "吸引力強、化學反應明顯"), "trine": (1, "情慾與愛意順暢"), "sextile": (0.5, "有火花"), "square": (-0.5, "愛與欲望節奏不同、易吵易和"), "opposition": (-0.5, "拉扯強烈、愛恨交織")},
    ("Sun", "Moon"): {"conjunction": (1.5, "一方的自我與另一方的情感需求相合，經典夫妻相位"), "trine": (1, "互補、相處自然"), "sextile": (0.5, "相處舒服"), "square": (-1, "需求與表達方式錯位，需學習"), "opposition": (-0.5, "互補但常站對立面")},
    ("Moon", "Moon"): {"conjunction": (1, "情感頻率相同"), "trine": (1, "情緒上彼此懂"), "sextile": (0.5, "情感相容"), "square": (-1, "情緒需求衝突、安全感來源不同"), "opposition": (-0.5, "情緒互補但易感到不被理解")},
    ("Venus", "Venus"): {"conjunction": (1, "愛的語言相同"), "trine": (1, "價值觀與品味相近"), "sextile": (0.5, "相處愉快"), "square": (-0.5, "愛的方式不同"), "opposition": (-0.5, "品味與價值觀相反")},
    ("Sun", "Venus"): {"conjunction": (1, "彼此欣賞"), "trine": (0.5, "互相欣賞"), "sextile": (0.5, "好感"), "square": (-0.5, "自我與對方的愛有摩擦"), "opposition": (0, "互補的吸引")},
    ("Moon", "Venus"): {"conjunction": (1, "溫柔契合"), "trine": (1, "情感滋養"), "sextile": (0.5, "溫暖"), "square": (-0.5, "情感與愛的方式錯位"), "opposition": (0, "互補")},
    ("Saturn", "Venus"): {"conjunction": (0.5, "有責任感的黏著，長久但需避免壓抑"), "trine": (1, "穩定、經得起時間"), "sextile": (0.5, "踏實"), "square": (-1, "一方讓另一方感到被限制、冷淡"), "opposition": (-1, "承諾與自由的拉扯")},
    ("Saturn", "Moon"): {"conjunction": (0, "安全感建立在責任上"), "trine": (0.5, "穩定依靠"), "sextile": (0.5, "可靠"), "square": (-1, "情感被壓抑、易覺得不被接住"), "opposition": (-1, "一方管束一方")},
    ("Mars", "Mars"): {"conjunction": (0, "能量同頻，可能很合也可能很衝"), "trine": (0.5, "行動一致"), "sextile": (0.5, "合作順"), "square": (-1, "容易起衝突、競爭"), "opposition": (-1, "對立、爭執")},
    ("Sun", "Sun"): {"conjunction": (0.5, "個性相像"), "trine": (0.5, "互相理解"), "sextile": (0.5, "相合"), "square": (-0.5, "自我碰撞"), "opposition": (0, "互補的兩極")},
}


def _bazi_match(fa: dict, fb: dict, male_a: bool | None, male_b: bool | None) -> tuple[list[dict], dict]:
    rs: list[dict] = []
    def add(delta, text):
        rs.append({"src": "八字", "delta": delta, "text": text})
    pa, pb = fa["pillars"], fb["pillars"]
    da, dbb = pa[2], pb[2]
    sa, sb = da["stem_idx"], dbb["stem_idx"]
    k = tuple(sorted((sa, sb)))
    if k in X._WUHE:
        add(2, f"日主天干相合（{X.STEMS[sa]}{X.STEMS[sb]}合化{X._WUHE[k]}）→ 兩人本性相吸、容易互相遷就")
    elif k in X._GANCHONG:
        add(-1, f"日主天干相沖（{X.STEMS[sa]}{X.STEMS[sb]}）→ 個性直接碰撞，需各退一步")
    for role, ia, ib, w in (("日支（夫妻宮）", da["branch_idx"], dbb["branch_idx"], 1.0), ("年支（生肖）", pa[0]["branch_idx"], pb[0]["branch_idx"], 0.6)):
        a, b = sorted((ia, ib))
        if (ia - ib) % 12 == 6:
            add(round(-2 * w, 1), f"{role}相沖（{_B[ia]}{_B[ib]}）→ {'夫妻宮對沖：聚少離多或易分合' if w == 1 else '生肖相沖：家庭、長輩層面易有磨擦'}")
        elif (a, b) in X._LIUHE:
            add(round(2 * w, 1), f"{role}六合（{_B[ia]}{_B[ib]}合化{X._LIUHE[(a, b)]}）→ {'夫妻宮相合：感情黏著、互相照顧' if w == 1 else '生肖相合：家庭相處融洽'}")
        elif X._SANHE_GROUP.get(ia) == X._SANHE_GROUP.get(ib) and ia != ib:
            add(round(1.5 * w, 1), f"{role}三合（{_B[ia]}{_B[ib]}）→ 合得來、有默契")
        elif (a, b) in X._HAI:
            add(round(-1 * w, 1), f"{role}相害（{_B[ia]}{_B[ib]}）→ 暗中生怨、小事累積")
        elif {a, b} == {0, 3} or (a == b and a in X._ZIXING):
            add(round(-1 * w, 1), f"{role}相刑（{_B[ia]}{_B[ib]}）→ 彼此折磨、需要界線")
        elif (a, b) in X._PO:
            add(round(-0.5 * w, 1), f"{role}相破（{_B[ia]}{_B[ib]}）→ 小破耗、不致大礙")
        elif ia == ib:
            add(0.3 if w == 1 else 0, f"{role}相同（{_B[ia]}）→ 習性相近，合則很合、悶則一起悶")
    ea, eb = X.STEM_ELEM[sa], X.STEM_ELEM[sb]
    fav_a, fav_b = set(fa["strength"]["favourable"]), set(fb["strength"]["favourable"])
    avo_a, avo_b = set(fa["strength"]["avoid"]), set(fb["strength"]["avoid"])
    na, nb = fa.get("name") or "A", fb.get("name") or "B"
    if eb in fav_a:
        add(1, f"{nb} 日主{eb}為 {na} 之喜用 → {nb} 能補 {na} 的不足")
    elif eb in avo_a:
        add(-1, f"{nb} 日主{eb}為 {na} 之忌神 → 相處久了 {na} 易感到消耗")
    if ea in fav_b:
        add(1, f"{na} 日主{ea}為 {nb} 之喜用 → {na} 能補 {nb} 的不足")
    elif ea in avo_b:
        add(-1, f"{na} 日主{ea}為 {nb} 之忌神 → 相處久了 {nb} 易感到消耗")
    if male_a is True and X.KE.get(ea) == eb:
        add(1, f"{nb} 日主{eb}為 {na}（男命）之財星 → 正是其妻星之象")
    if male_a is False and X.KE.get(eb) == ea:
        add(1, f"{nb} 日主{eb}為 {na}（女命）之官星 → 正是其夫星之象")
    if male_b is True and X.KE.get(eb) == ea:
        add(1, f"{na} 日主{ea}為 {nb}（男命）之財星 → 正是其妻星之象")
    if male_b is False and X.KE.get(ea) == eb:
        add(1, f"{na} 日主{ea}為 {nb}（女命）之官星 → 正是其夫星之象")
    facts = {na: f"日柱 {da['gz']}（{ea}・{fa['strength']['label']}・喜 {'/'.join(fav_a)}）年支 {pa[0]['branch']}",
             nb: f"日柱 {dbb['gz']}（{eb}・{fb['strength']['label']}・喜 {'/'.join(fav_b)}）年支 {pb[0]['branch']}"}
    return rs, facts


def match(a: BirthInput, b: BirthInput, *, charts_a: dict[str, Chart] | None = None) -> dict:
    """合婚：八字 + 西洋 synastry, scored with every term listed."""
    from fortune import synastry as S
    ca_bazi = charts_a["bazi"] if charts_a and "bazi" in charts_a else casting.cast("bazi", a)
    cb_bazi = casting.cast("bazi", b)
    fa, fb = dict(ca_bazi.chart, name=a.name), dict(cb_bazi.chart, name=b.name)
    reasons, facts = _bazi_match(fa, fb, _male(a), _male(b))
    syn = S.compute(a, b)
    for x in syn.cross_aspects:
        key = tuple(sorted((x["a"], x["b"])))
        rule = _PAIR_RULES.get(key) or _PAIR_RULES.get((key[1], key[0]))
        if not rule or x["type"] not in rule:
            continue
        w, why = rule[x["type"]]
        reasons.append({"src": "西洋", "delta": w, "text": f"{a.name or 'A'} {x['a']} {x['type']} {b.name or 'B'} {x['b']}（{x['orb']}°）→ {why}"})
    score = round(sum(r["delta"] for r in reasons), 1)
    g, label = _grade(score)
    comp = syn.composite or {}
    cs = {p["body"]: p for p in comp.get("planets", [])}
    facts["合盤 composite"] = f"Sun {cs['Sun']['sign']}・Venus {cs['Venus']['sign']}・Moon {cs['Moon']['sign']}" if cs else "—"
    facts["星際相位"] = syn.summary
    return {"a": a.label(), "b": b.label(), "score": score, "grade": g, "label": label,
            "reasons": sorted(reasons, key=lambda r: -abs(r["delta"])), "facts": facts,
            "summary": f"合婚 {a.name or 'A'} ✕ {b.name or 'B'}：{score:+}（{label}）— 八字 {sum(r['delta'] for r in reasons if r['src'] == '八字'):+.1f}・西洋 {sum(r['delta'] for r in reasons if r['src'] == '西洋'):+.1f}"}


# --- the consultation ------------------------------------------------------------------------

def consult(birth: BirthInput, question: str | None = None, *, partner: BirthInput | None = None,
            start_year: int | None = None, years: int = 8, read: bool = False, lang: str = "zh",
            house_system: str = "whole_sign") -> dict:
    """One sitting with the 感情命理師: cast once, then 命 (natal), 運 (timing), 合婚 (if a partner), and the reading."""
    male = _male(birth)
    charts: dict[str, Chart] = {}
    errors: dict[str, str] = {}
    for k in casting.REGISTRY:
        try:
            charts[k] = casting.cast(k, birth, house_system=house_system, transits=(k == "astrology"))
        except Exception as e:  # noqa: BLE001 — one system never sinks the sitting
            errors[k] = str(e)
    intent = classify(question, has_partner=partner is not None)
    this_year = F.synthesize(charts, "love", male)
    out = {
        "subject": birth.label(), "question": question, "intent": intent, "intent_label": intent_label(intent),
        "natal": natal(charts, male),
        "this_year": {k: this_year[k] for k in ("systems", "tally", "lean", "lean_zh", "consensus", "conflicts", "summary")},
        "timing": timing(birth, charts, start_year or date.today().year, years),
        "match": match(birth, partner, charts_a=charts) if partner else None,
        "errors": errors,
    }
    out["summary"] = " ｜ ".join(s for s in (out["natal"]["summary"], out["this_year"]["summary"], out["timing"]["summary"], (out["match"] or {}).get("summary")) if s)
    if read:
        out["interpretation"] = interpret(out, lang=lang)
    return out


def _persona() -> str:
    return _PROMPT.read_text(encoding="utf-8") if _PROMPT.exists() else "You are a warm, rigorous love-specialist diviner. Read only from the facts."


def prompts(out: dict, *, lang: str = "zh") -> tuple[str, str]:
    """(system, user) for the 感情命理師 reading — the facts that the sub-question needs, in the order it needs them."""
    from fortune.interpret import lang_instruction
    intent = out["intent"]
    order = {"timing": ["timing", "natal", "this_year"], "match": ["match", "natal", "this_year", "timing"],
             "reconcile": ["this_year", "timing", "natal", "match"], "breakup": ["this_year", "natal", "timing", "match"],
             "marriage": ["timing", "natal", "match", "this_year"], "affair": ["this_year", "natal", "timing"],
             "current": ["this_year", "natal", "timing", "match"]}[intent]
    slim = {}
    for k in order:
        v = out.get(k)
        if not v:
            continue
        if k == "timing":
            v = {"summary": v["summary"], "best": v["best"], "caution": v["caution"],
                 "years": [{"year": y["year"], "age": y["age"], "score": y["score"], "label": y["label"], "marriage_sign": y["marriage_sign"],
                            "reasons": [f"{r['src']} {r['delta']:+} {r['text']}" for r in y["reasons"][:6]]} for y in v["years"]]}
        elif k == "this_year":
            v = {"summary": v["summary"], "systems": [{"system": r["system_zh"], "verdict": r["verdict_zh"], "why": r["reason"], "facts": r["facts"]} for r in v["systems"]]}
        elif k == "natal":
            v = {"summary": v["summary"], "systems": [{"system": r["system_zh"], "score": r["score"], "reasons": r["reasons"], "facts": r["facts"]} for r in v["systems"]]}
        elif k == "match":
            v = {"summary": v["summary"], "score": v["score"], "label": v["label"], "reasons": [f"{r['src']} {r['delta']:+} {r['text']}" for r in v["reasons"]], "facts": v["facts"]}
        slim[k] = v
    user = (f"命主 / Subject: {out['subject']}\n★ 問題 / Question: {out.get('question') or '（未指定，請看整體感情運）'}（子題 sub-intent: {out['intent_label']}）\n"
            f"（先回答這個子題，再補其餘 / answer this sub-question FIRST）\n\nFacts (JSON, in the order to use them):\n{json.dumps(slim, ensure_ascii=False, indent=1)}\n\n"
            "Read only from these facts. " + lang_instruction(lang))
    return _persona() + "\n" + lang_instruction(lang), user


def interpret(out: dict, *, lang: str = "zh") -> str:
    system, user = prompts(out, lang=lang)
    return complete(system, user)
