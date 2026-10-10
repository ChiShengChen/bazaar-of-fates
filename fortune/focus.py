"""Question-oriented reading / 問題導向解讀 — pick, per system, the facts that bear on what the
person asked, give each system a deterministic verdict on that topic, and tally the systems.

  classify(focus)            → topic key (career / love / wealth / health / study / family / general)
  extract(chart, topic)      → {"facts": {...}, "verdict": "favourable|neutral|unfavourable", "reason": "…"}
  synthesize(charts, topic)  → per-system verdicts + tally + consensus / conflicts

The facts dict is what goes to the LLM (instead of the whole chart); the verdict is a small,
auditable rule per tradition — the LLM is told to weigh them, not to invent beyond them.
"""

from __future__ import annotations

from datetime import date

from fortune.schemas import Chart

TOPICS = {
    "career": {"zh": "事業", "en": "career / work", "kw": ["事業", "工作", "職", "升遷", "創業", "career", "job", "work", "promotion", "business", "boss", "老闆", "轉職", "跳槽", "考試", "面試"]},
    "love": {"zh": "感情", "en": "love / relationships", "kw": ["感情", "愛情", "婚", "戀", "桃花", "伴侶", "對象", "love", "marriage", "relationship", "partner", "romance", "dating", "另一半", "分手", "復合", "正緣", "緣分", "脫單", "喜歡", "曖昧", "交往", "crush", "ex"]},
    "wealth": {"zh": "財運", "en": "wealth / money", "kw": ["財", "錢", "投資", "收入", "理財", "money", "wealth", "finance", "income", "invest", "salary", "薪", "偏財", "正財", "買房"]},
    "health": {"zh": "健康", "en": "health", "kw": ["健康", "身體", "病", "疾", "health", "illness", "body", "醫", "手術", "開刀", "養生", "壓力", "失眠", "睡眠", "焦慮", "憂鬱", "過敏", "體質", "檢查", "sleep", "stress", "anxiety", "surgery"]},
    "study": {"zh": "學業", "en": "study / learning", "kw": ["學業", "讀書", "學習", "升學", "考試", "study", "school", "exam", "learning", "academic", "留學", "研究"]},
    "family": {"zh": "家庭", "en": "family", "kw": ["家庭", "父母", "子女", "小孩", "家人", "家運", "family", "parents", "children", "kids", "home", "搬家", "房"]},
}
VERDICT_ZH = {"favourable": "利", "neutral": "平", "unfavourable": "不利"}
_HARMONIOUS = {"trine", "sextile", "conjunction"}
_CHALLENGING = {"square", "opposition"}
_RULER = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
          "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"}
_VEDIC_RULER = {"Mesha": "Mars", "Vrishabha": "Venus", "Mithuna": "Mercury", "Karka": "Moon", "Simha": "Sun", "Kanya": "Mercury",
                "Tula": "Venus", "Vrischika": "Mars", "Dhanu": "Jupiter", "Makara": "Saturn", "Kumbha": "Saturn", "Meena": "Jupiter"}
_HOUSES = {"career": [10, 6], "love": [7, 5], "wealth": [2, 8], "health": [6, 1], "study": [3, 9], "family": [4], "general": [1]}
_PALACE = {"career": "官祿", "love": "夫妻", "wealth": "財帛", "health": "疾厄", "study": "父母", "family": "田宅", "general": "命宮"}
_BAZI_STARS = {"career": ["正官", "七殺", "正印", "偏印"], "wealth": ["正財", "偏財", "食神", "傷官"], "health": [],
               "study": ["正印", "偏印", "食神", "傷官"], "family": ["正印", "偏印", "食神", "傷官", "正財"], "general": []}
_LIUYAO_YONG = {"career": ["官鬼"], "wealth": ["妻財"], "study": ["父母"], "family": ["父母", "子孫"], "health": [], "general": []}
_QIMEN_YONG = {"career": ("gate", "開門"), "wealth": ("gate", "生門"), "love": ("god", "六合"), "health": ("star", "天芮"),
               "study": ("star", "天輔"), "family": ("gate", "生門"), "general": ("zhishi", "")}
_GOOD_GENERALS = {"貴人", "六合", "青龍", "太常", "太陰", "天后"}
_BAD_GENERALS = {"螣蛇", "朱雀", "勾陳", "天空", "白虎", "玄武"}
_SHA = {"擎羊", "陀羅", "火星", "鈴星", "地空", "地劫"}


def classify(focus: str | None) -> str:
    if not focus:
        return "general"
    f = focus.lower()
    best, score = "general", 0
    for key, t in TOPICS.items():
        s = sum(1 for k in t["kw"] if k.lower() in f)
        if s > score:
            best, score = key, s
    return best


def topic_label(topic: str) -> str:
    t = TOPICS.get(topic)
    return f"{t['zh']} / {t['en']}" if t else "整體 / general"


# --- per-system extractors ------------------------------------------------------------------

def _bazi(c: dict, r: dict, topic: str, male: bool | None) -> dict:
    stars = list(_BAZI_STARS.get(topic, []))
    if topic == "love":
        stars = ["正財", "偏財"] if male else ["正官", "七殺"] if male is False else ["正財", "偏財", "正官", "七殺"]
    pillars = c.get("pillars", [])
    where = []
    for p in pillars:
        if p.get("stem_god") in stars:
            where.append(f"{p['pillar']}天干 {p['stem']}（{p['stem_god']}）")
        for h in p.get("hidden", []):
            if h["god"] in stars:
                where.append(f"{p['pillar']}藏干 {h['stem']}（{h['god']}）")
    strength = c.get("strength", {})
    cur_dy = next((d for d in c.get("dayun", []) if d.get("current")), None)
    cur_ln = next((l for d in c.get("dayun", []) for l in d.get("liunian", []) if l.get("current")), None)
    facts = {
        "日主": f"{strength.get('day_master', '')}{strength.get('dm_elem', '')}・{strength.get('label', '')}",
        "用神": f"{strength.get('yongshen', '')}（{strength.get('yongshen_why', '')}）", "喜": strength.get("favourable"), "忌": strength.get("avoid"),
        "本題相關十神": stars or "整體", "出現位置": where or "原局未見（弱或伏）",
    }
    if topic == "love":
        day = next((p for p in pillars if p.get("role") == "day"), None)
        if day:
            facts["夫妻宮（日支）"] = f"{day['branch']}：藏 " + "、".join(f"{h['stem']}{h['god']}" for h in day.get("hidden", []))
        facts["桃花類神煞"] = [s for p in pillars for s in p.get("shensha", []) if s in ("桃花", "紅鸞", "天喜", "天乙貴人", "孤辰", "寡宿")] or "無"
    if topic == "health":
        counts: dict[str, int] = {}
        for p in pillars:
            for e in (p.get("stem_elem"), p.get("branch_elem")):
                counts[e] = counts.get(e, 0) + 1
        facts["五行分佈"] = counts
        facts["調候"] = strength.get("tiaohou_note")
    if topic == "study":
        facts["文昌/學堂"] = [s for p in pillars for s in p.get("shensha", []) if s in ("文昌貴人", "學堂", "天乙貴人")] or "無"
    if cur_dy:
        facts["現行大運"] = f"{cur_dy['gz']}（{cur_dy['stem_god']}・{cur_dy['nature']}・{cur_dy['start_year']}–{cur_dy['end_year']}）" + ("；".join(cur_dy.get("branch_notes", [])) and "；留意 " + "；".join(cur_dy.get("branch_notes", [])))
    if cur_ln:
        facts["今年流年"] = f"{cur_ln['year']} {cur_ln['gz']}（{cur_ln['stem_god']}・{cur_ln['nature']}）神煞 {'、'.join(cur_ln.get('shensha', [])) or '無'}；留意 {'；'.join(cur_ln.get('stem_notes', []) + cur_ln.get('branch_notes', [])) or '無'}"
    score = 0
    reason = []
    if cur_ln:
        score += 1 if cur_ln["nature"] == "favourable" else -1
        reason.append(f"流年{cur_ln['gz']}為{'喜用' if cur_ln['nature'] == 'favourable' else '忌耗'}五行")
        if stars and cur_ln["stem_god"] in stars:
            score += 1
            reason.append(f"流年透{cur_ln['stem_god']}（本題之星）")
    if cur_dy:
        score += 1 if cur_dy["nature"] == "favourable" else -1
        reason.append(f"大運{cur_dy['gz']}{'順' if cur_dy['nature'] == 'favourable' else '逆'}")
    if stars and not where:
        score -= 1
        reason.append("原局不見本題之星")
    return {"facts": facts, "verdict": "favourable" if score >= 2 else "unfavourable" if score <= -1 else "neutral", "reason": "；".join(reason) or "依喜用與大運流年"}


def _ziwei(c: dict, r: dict, topic: str) -> dict:
    pal_name = _PALACE.get(topic, "命宮")
    palaces = c.get("palaces", [])
    by_name = {p["name"]: p for p in palaces}
    by_branch = {p["branch"]: p for p in palaces}
    B = "子丑寅卯辰巳午未申酉戌亥"
    pal = by_name.get(pal_name)
    if not pal:
        return {"facts": {}, "verdict": "neutral", "reason": "無此宮"}
    bi = B.index(pal["branch"])
    trine = [by_branch[B[(bi + k) % 12]] for k in (4, 8)]
    opp = by_branch[B[(bi + 6) % 12]]
    def stars(p):
        return [f"{s}{'(' + p['brightness'][s.split('(')[0]] + ')' if p.get('brightness', {}).get(s.split('(')[0]) else ''}" for s in p.get("stars", [])] or ["空宮"]
    luck = c.get("luck", {})
    cur_dx = next((d for d in luck.get("daxian", []) if d.get("current")), None)
    cur_ln = next((l for d in luck.get("daxian", []) for l in d.get("liunian", []) if l.get("current")), None)
    facts = {
        "本題宮位": f"{pal_name}（{pal['stem']}{pal['branch']}）：" + "、".join(stars(pal)),
        "三方": {p["name"]: "、".join(stars(p)) for p in trine}, "對宮": f"{opp['name']}：" + "、".join(stars(opp)),
        "雜曜": pal.get("adjective_stars", []), "長生/博士": f"{pal.get('changsheng', '')}・{pal.get('boshi', '')}",
    }
    related = {pal_name, opp["name"], *[p["name"] for p in trine]}
    score, reason = 0, []
    sha = sum(1 for s in pal.get("stars", []) if s.split("(")[0] in _SHA)
    if sha >= 2:
        score -= 1
        reason.append(f"{pal_name}煞星{sha}顆")
    for label, item in (("大限", cur_dx), ("流年", cur_ln)):
        if not item:
            continue
        landing = item.get("sihua_landing", {})
        facts[f"{label}四化落宮"] = {f"化{k}": v for k, v in landing.items()}
        if label == "流年":
            facts["流年太歲宮"] = item.get("taisui_palace")
        good = [k for k in ("祿", "權", "科") if landing.get(k) in related]
        bad = landing.get("忌") in related
        if good:
            score += 1
            reason.append(f"{label}化{'/'.join(good)}入{pal_name}三方四正")
        if bad:
            score -= 1
            reason.append(f"{label}化忌入{pal_name}三方四正")
    return {"facts": facts, "verdict": "favourable" if score >= 1 else "unfavourable" if score <= -1 else "neutral", "reason": "；".join(reason) or f"{pal_name}無流年四化出入"}


def _liuyao(c: dict, topic: str, male: bool | None) -> dict:
    g = c.get("hexagram", {})
    lines = g.get("lines", [])
    yong = list(_LIUYAO_YONG.get(topic, []))
    if topic == "love":
        yong = ["妻財"] if male else ["官鬼"] if male is False else ["妻財", "官鬼"]
    shi = next((l for l in lines if l.get("shi")), None)
    targets = [l for l in lines if l.get("relative") in yong] if yong else ([shi] if shi else [])
    hidden = [h for h in g.get("hidden", []) if h.get("relative") in yong]
    def desc(l):
        return f"{l['pos']}爻 {l['relative']}{l['stem']}{l['branch']}（{l['god']}）{'動' if l.get('moving') else ''} {'/'.join(l.get('notes', []))}"
    facts = {"卦": f"{g.get('name')}（{g.get('palace')}宮）世{g.get('shi')}應{g.get('ying')}", "用神": yong or "世爻",
             "用神爻": [desc(l) for l in targets] or "不上卦", "伏神": [f"{h['relative']}{h['stem']}{h['branch']}伏{h['pos']}爻" for h in hidden] or "無",
             "世爻": desc(shi) if shi else "", "動爻": f"{g['moving']}爻 → {g['changed']['line']['relative']}（{g['changed']['relation']}）" if g.get("changed") else "無"}
    if topic == "health":
        facts["官鬼（病）"] = [desc(l) for l in lines if l.get("relative") == "官鬼"] or "不上卦"
    score, reason = 0, []
    for l in targets:
        n = l.get("notes", [])
        if any(x.startswith("月旺") or x.startswith("月相") for x in n) or "日生" in n or "日臨" in n:
            score += 1
            reason.append(f"{l['relative']}{l['branch']}得月日之氣")
        if any(x in n for x in ("旬空", "月破")) or "日剋" in n or any(x.startswith("月囚") or x.startswith("月死") for x in n):
            score -= 1
            reason.append(f"{l['relative']}{l['branch']}" + "、".join(x for x in n if x in ("旬空", "月破", "日剋") or x.startswith(("月囚", "月死"))))
        if l.get("moving") and g.get("changed"):
            rel = g["changed"]["relation"]
            score += 1 if rel in ("化回頭生", "化進神") else -1 if rel in ("化回頭剋", "化退神") else 0
            reason.append(f"動爻{rel}")
    if yong and not targets:
        score -= 1
        reason.append("用神不上卦（伏）")
    if topic == "health":
        ghosts = [l for l in lines if l.get("relative") == "官鬼" and (l.get("moving") or any(x.startswith(("月旺", "月相")) for x in l.get("notes", [])))]
        if ghosts:
            score -= 1
            reason.append("官鬼旺動")
    return {"facts": facts, "verdict": "favourable" if score >= 1 else "unfavourable" if score <= -1 else "neutral", "reason": "；".join(reason) or "用神平"}


def _astrology(ch: Chart, topic: str) -> dict:
    c = ch.chart
    planets = c.get("planets", [])
    houses = _HOUSES.get(topic, [1])
    facts: dict = {}
    score, reason = 0, []
    if ch.ascendant:
        cusps = {h["house"]: h for h in ch.ascendant.get("houses", [])}
        inhouse = [f"{p['body']} {p['sign']} (H{p.get('house')})" for p in planets if p.get("house") in houses]
        facts["本題宮位"] = [f"H{h} {cusps[h]['sign']}" for h in houses if h in cusps]
        facts["宮內行星"] = inhouse or "空"
        for h in houses[:1]:
            ruler = _RULER.get(cusps.get(h, {}).get("sign", ""))
            rp = next((p for p in planets if p["body"] == ruler), None)
            if rp:
                facts[f"H{h}宮主"] = f"{ruler} in {rp['sign']} H{rp.get('house')}"
                asp = [x for x in c.get("aspects_detail", []) if ruler in (x["a"], x["b"])]
                facts["宮主相位"] = [f"{x['a']} {x['type']} {x['b']} ({x['orb']}°)" for x in asp]
                harm = sum(1 for x in asp if x["type"] in _HARMONIOUS and ruler not in (x["a"], x["b"]) or x["type"] in _HARMONIOUS)
                chal = sum(1 for x in asp if x["type"] in _CHALLENGING)
                score += (1 if harm > chal else -1 if chal > harm else 0)
                reason.append(f"H{h}宮主{ruler}相位 和諧{harm}/緊張{chal}")
        trans = [x for x in c.get("transit_aspects", []) if x["b"] in ("Jupiter", "Saturn")]
        if trans:
            facts["行運木土"] = [f"transit {x['b']} {x['type']} natal {x['a']} ({x['phase']})" for x in trans[:6]]
    else:
        facts["註"] = "無時辰/出生地，無宮位；僅看行星與相位"
        facts["行星"] = [f"{p['body']} {p['sign']}" for p in planets]
    facts["主要相位"] = c.get("aspects", [])[:6]
    return {"facts": facts, "verdict": "favourable" if score > 0 else "unfavourable" if score < 0 else "neutral", "reason": "；".join(reason) or "無宮位資料，中性"}


def _jyotish(ch: Chart, topic: str) -> dict:
    grahas = ch.chart.get("grahas", [])
    bh = {"career": [10], "love": [7], "wealth": [2, 11], "health": [6], "study": [5, 9], "family": [4], "general": [1]}[topic if topic in _HOUSES else "general"]
    facts: dict = {"daśā": f"{ch.readings.get('mahadasha_lord')}（{ch.readings.get('dasha_nature')}）", "月宿": ch.readings.get("moon_nakshatra")}
    score = 1 if ch.readings.get("dasha_nature") == "benefic" else -1
    reason = [f"daśā {ch.readings.get('mahadasha_lord')} {ch.readings.get('dasha_nature')}"]
    if ch.ascendant:
        hs = {h["house"]: h["rashi"] for h in ch.ascendant.get("houses", [])}
        facts["本題 bhāva"] = [f"{b}: {hs.get(b)}" for b in bh]
        facts["bhāva 內九曜"] = [f"{g['graha']} {g['rashi']} (B{g.get('bhava')})" for g in grahas if g.get("bhava") in bh] or "空"
        lord = _VEDIC_RULER.get(hs.get(bh[0], ""))
        lp = next((g for g in grahas if g["graha"] == lord), None)
        if lp:
            facts[f"B{bh[0]} lord"] = f"{lord} in {lp['rashi']} B{lp.get('bhava')}"
            if lp.get("bhava") in (6, 8, 12):
                score -= 1
                reason.append(f"{lord} 落 dusthāna B{lp['bhava']}")
    return {"facts": facts, "verdict": "favourable" if score > 0 else "unfavourable" if score < 0 else "neutral", "reason": "；".join(reason)}


def _qimen(c: dict, r: dict, topic: str) -> dict:
    kind, name = _QIMEN_YONG.get(topic, ("zhishi", ""))
    palaces = c.get("palaces", [])
    if kind == "zhishi":
        target = next((p for p in palaces if p.get("gate") == c.get("zhishi")), None)
        label = f"值使 {c.get('zhishi')}"
    else:
        target = next((p for p in palaces if p.get(kind) == name or (kind == "star" and str(p.get("star", "")).startswith(name))), None)
        label = f"用神 {name}"
    facts = {"局": c.get("ju"), "值符/值使": f"{c.get('zhifu')} / {c.get('zhishi')}"}
    score, reason = 0, []
    if target:
        facts[label] = f"落 {target['name']}（{target['direction']}）：{target.get('god')}・{target.get('star')}・{target.get('gate')}・{target.get('sky_stem')}/{target.get('earth_stem')}"
        cls = target.get("gate_cls")
        if topic == "health":
            score += -1 if cls == "凶" else 1 if cls == "吉" else 0
            reason.append(f"天芮（病星）落{target['name']}，臨{target.get('gate')}")
        else:
            score += 1 if cls == "吉" else -1 if cls == "凶" else 0
            reason.append(f"{label}落{target['name']}{target.get('gate')}（{cls}）")
        if target.get("god") in ("值符", "九天", "六合", "太陰", "九地"):
            score += 0 if score else 0
            reason.append(f"神為{target.get('god')}")
    return {"facts": facts, "verdict": "favourable" if score > 0 else "unfavourable" if score < 0 else "neutral", "reason": "；".join(reason) or "用神宮平"}


def _liuren(c: dict, r: dict, topic: str) -> dict:
    tr, gens = c.get("transmissions", []), c.get("transmission_generals", [])
    facts = {"課體": c.get("kind"), "三傳": [f"{b}（{g}）" for b, g in zip(tr, gens)], "初傳與日主": r.get("relation"),
             "四課": [f"{k['upper']}/{k['lower']}（{k.get('general', '')}）" for k in c.get("courses", [])]}
    score = 1 if r.get("liuren_regime") == "supported" else -1
    reason = [f"初傳{r.get('relation')}"]
    good = sum(1 for g in gens if g in _GOOD_GENERALS)
    bad = sum(1 for g in gens if g in _BAD_GENERALS)
    score += 1 if good > bad else -1 if bad > good else 0
    reason.append(f"三傳吉將{good}凶將{bad}")
    if topic == "love" and any(g in ("六合", "天后") for g in gens):
        score += 1
        reason.append("三傳見六合/天后")
    if topic == "health" and any(g in ("白虎", "螣蛇") for g in gens):
        score -= 1
        reason.append("三傳見白虎/螣蛇")
    if topic in ("career", "wealth") and "青龍" in gens:
        score += 1
        reason.append("三傳見青龍")
    return {"facts": facts, "verdict": "favourable" if score >= 1 else "unfavourable" if score <= -1 else "neutral", "reason": "；".join(reason)}


def extract(ch: Chart, topic: str, male: bool | None = None) -> dict:
    """Topic-relevant facts + a deterministic verdict for one cast chart."""
    s, c, r = ch.system, ch.chart or {}, ch.readings or {}
    if s == "bazi":
        return _bazi(c, r, topic, male)
    if s == "ziwei":
        return _ziwei(c, r, topic)
    if s == "liuyao":
        return _liuyao(c, topic, male)
    if s == "astrology":
        return _astrology(ch, topic)
    if s == "jyotish":
        return _jyotish(ch, topic)
    if s == "qimen":
        return _qimen(c, r, topic)
    if s == "liuren":
        return _liuren(c, r, topic)
    if s == "iching":
        h = c.get("hexagram", {})
        v = "favourable" if h.get("auspicious") else "unfavourable"
        return {"facts": {"本卦": h.get("ben_name"), "變卦": h.get("bian_name"), "體用": h.get("relation")}, "verdict": v, "reason": f"體用 {h.get('relation')} → {h.get('verdict')}"}
    if s == "xiaoliuren":
        return {"facts": {"課": c.get("result"), "斷": c.get("text")}, "verdict": "favourable" if c.get("luck") == "吉" else "unfavourable", "reason": f"落{c.get('result')}（{c.get('luck')}）"}
    if s == "suimei":
        from fortune import bazi_ext as X
        from fortune.engines.suimei import suimei
        ds = X.STEMS.index(r.get("day_master", "甲"))
        yb = (date.today().year - 4) % 12
        tf = suimei.twelve_fortune(ds, yb)
        v = "favourable" if tf in suimei.THRIVING else "unfavourable" if tf in suimei.WEAK else "neutral"
        return {"facts": {"流年十二運星": f"{X.BRANCHES[yb]}年 {tf}", "天中殺": r.get("tenchusatsu"), "流年在天中殺": X.BRANCHES[yb] in (r.get("tenchusatsu") or "")},
                "verdict": "unfavourable" if X.BRANCHES[yb] in (r.get("tenchusatsu") or "") else v, "reason": f"流年{tf}" + ("，且逢天中殺" if X.BRANCHES[yb] in (r.get("tenchusatsu") or "") else "")}
    if s == "qizheng":
        reg = r.get("qizheng_regime", "neutral")
        return {"facts": {"命主太陽": r.get("ming_zhu_sign"), "歲星": r.get("jupiter_sign"), "火星": r.get("mars_sign"), "羅睺": r.get("rahu_sign")},
                "verdict": "favourable" if reg == "benefic_blessing" else "unfavourable" if reg == "malefic_affliction" else "neutral", "reason": reg}
    if s == "tieban":
        reg = r.get("tieban_regime", "neutral")
        return {"facts": {"命數": r.get("ming_number"), "流年條文": r.get("liunian_verse_no"), "斷": r.get("liunian_verdict")},
                "verdict": "favourable" if reg == "auspicious" else "unfavourable" if reg == "inauspicious" else "neutral", "reason": f"流年條文 {r.get('liunian_verdict')}"}
    if s == "xingming":
        grids = {g["name"]: g for g in c.get("grids", [])}
        ren = grids.get("人格", {})
        rel = c.get("relations", {})
        sc = c.get("score", 0)
        facts = {"人格": f"{ren.get('number')}・{ren.get('element')}・{ren.get('luck')}", "三才": c.get("sancai"), "總格": f"{grids.get('總格', {}).get('number')}・{grids.get('總格', {}).get('luck')}",
                 "成功運／基礎運／社交運": "、".join(rel.get(k, {}).get("kind", "") for k in ("成功運", "基礎運", "社交運")), "人格對八字": ren.get("bazi") or "—"}
        if topic in ("career", "wealth"):
            facts["本題"] = f"成功運 {rel.get('成功運', {}).get('text', '')}；總格（後運）{grids.get('總格', {}).get('luck')}"
        elif topic in ("love", "family"):
            facts["本題"] = f"基礎運 {rel.get('基礎運', {}).get('text', '')}（家庭、子女）；社交運 {rel.get('社交運', {}).get('text', '')}"
        elif topic == "health":
            facts["本題"] = f"人格數理 {ren.get('luck')}；三才{'相剋' if any(rel.get(k, {}).get('kind') == '相剋' for k in ('成功運', '基礎運')) else '無剋'}"
        return {"facts": facts, "verdict": "favourable" if sc >= 1.5 else "unfavourable" if sc <= -1 else "neutral", "reason": f"人格{ren.get('luck')}・三才生剋合計 {sc:+}"}
    if s == "taiyi":
        return {"facts": {"流年": r.get("liunian_host_guest"), "命局": r.get("natal_host_guest")}, "verdict": "favourable" if r.get("verdict") == "主勝" else "unfavourable", "reason": f"流年{r.get('verdict')}"}
    return {"facts": {"summary": ch.summary}, "verdict": "neutral", "reason": "無專項規則"}


def synthesize(charts: dict[str, Chart], topic: str, male: bool | None = None) -> dict:
    rows = []
    for key, ch in charts.items():
        try:
            e = extract(ch, topic, male)
        except Exception as ex:  # noqa: BLE001 — one system must never sink the synthesis
            e = {"facts": {"error": str(ex)}, "verdict": "neutral", "reason": "抽取失敗"}
        rows.append({"system": key, "system_zh": ch.system_zh, "system_en": ch.system_en, "summary": ch.summary,
                     "verdict": e["verdict"], "verdict_zh": VERDICT_ZH[e["verdict"]], "reason": e["reason"], "facts": e["facts"]})
    tally = {v: sum(1 for r in rows if r["verdict"] == v) for v in ("favourable", "neutral", "unfavourable")}
    fav = [r["system_zh"] for r in rows if r["verdict"] == "favourable"]
    unf = [r["system_zh"] for r in rows if r["verdict"] == "unfavourable"]
    lean = "favourable" if tally["favourable"] > tally["unfavourable"] else "unfavourable" if tally["unfavourable"] > tally["favourable"] else "neutral"
    return {
        "topic": topic, "topic_label": topic_label(topic), "systems": rows, "tally": tally, "lean": lean, "lean_zh": VERDICT_ZH[lean],
        "consensus": fav if lean == "favourable" else unf if lean == "unfavourable" else [],
        "conflicts": unf if lean == "favourable" else fav if lean == "unfavourable" else fav + unf,
        "summary": f"{topic_label(topic)}：{len(rows)} 套中 利 {tally['favourable']}・平 {tally['neutral']}・不利 {tally['unfavourable']} → 整體偏{VERDICT_ZH[lean]}",
    }
