"""問事 / divination on demand — 奇門・六壬・梅花・六爻・小六壬 cast for the moment of the question (or the numbers given), not a birth.

  ask(system, question, at=…, numbers=…, text=…, coins=…)  → the chart + a question-oriented verdict with every term listed

  qimen      時盤：the hour chart at `at`; 日干宮 = the asker, 時干宮 = the matter, 用神宮 by topic (開門 事業・生門 財・六合 感情・天芮 病・天輔 學業),
             門迫 / 空亡 / 三奇 / 八神 / 九星 / 宮位生剋 scored; 吉方 for action
  liuren     時課：月將加占時 at `at`; 類神 by topic (官鬼・妻財・父母・六合天后・朱雀・白虎螣蛇) in the 三傳, 末傳 vs 日干, 課體, 旬空 scored
  iching     梅花：時間起卦 (default) · 數字起卦 (`numbers`: 1 / 2 / 3 numbers) · 字占 (`text`: character counts, 少為上 多為下, ＋時數)
  liuyao     六爻：時間起卦 (default) · 金錢卦 (`coins`: six values 6/7/8/9 bottom→top; 6 老陰、9 老陽 動)
  xiaoliuren 小六壬：農曆月日時 at `at`

Everything is deterministic; `read=True` adds the system's own 解讀 (question-focused).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fortune import bazi_ext as X
from fortune import casting
from fortune import focus as F
from fortune import geo
from fortune import liuyao_ext as LY
from fortune.birth import BirthInput
from fortune.engines.iching import iching as IC
from fortune.schemas import Chart

SYSTEMS = {"qimen": "奇門遁甲", "liuren": "大六壬", "iching": "梅花易數", "liuyao": "六爻", "xiaoliuren": "小六壬"}
_B = X.BRANCHES
_PAL_ELEM = {1: "水", 2: "土", 3: "木", 4: "木", 5: "土", 6: "金", 7: "金", 8: "土", 9: "火"}
_PAL_BRANCH = {1: "子", 8: "丑寅", 3: "卯", 4: "辰巳", 9: "午", 2: "未申", 7: "酉", 6: "戌亥", 5: ""}
_GATE_ELEM = {"休門": "水", "生門": "土", "傷門": "木", "杜門": "木", "景門": "火", "死門": "土", "驚門": "金", "開門": "金"}
_GOOD_STARS = {"天輔", "天心", "天任", "天沖"}
_BAD_STARS = {"天蓬", "天芮", "天柱"}
_GOOD_GODS = {"值符", "九天", "六合", "太陰", "九地"}
_BAD_GODS = {"白虎", "玄武", "騰蛇"}
_QIMEN_YONG = {"career": ("gate", "開門", "開門（事業・官職）"), "wealth": ("gate", "生門", "生門（財・營生）"), "love": ("god", "六合", "六合（婚姻・合作）"),
               "health": ("star", "天芮", "天芮（病星）"), "study": ("star", "天輔", "天輔（文書・學業）"), "family": ("gate", "生門", "生門（家宅）"), "general": ("zhishi", "", "值使門")}
_LR_GOOD = {"貴人", "六合", "青龍", "太常", "太陰", "天后"}
_LR_BAD = {"螣蛇", "朱雀", "勾陳", "天空", "白虎", "玄武"}
_LR_TOPIC = {"career": (["官"], {"貴人", "青龍"}, "官鬼（剋日干之支）・貴人／青龍"), "wealth": (["財"], {"青龍", "太常"}, "妻財（日干所剋之支）・青龍／太常"),
             "love": (["財", "官"], {"六合", "天后"}, "財／官・六合／天后"), "health": ([], {"天醫"}, "白虎／螣蛇為病"), "study": (["父"], {"朱雀", "貴人"}, "父母（生日干之支）・朱雀（文書）"),
             "family": (["父"], {"太常", "六合"}, "父母・太常／六合"), "general": ([], set(), "初傳")}
_LY_YONG = {"career": ["官鬼"], "wealth": ["妻財"], "study": ["父母"], "family": ["父母", "子孫"], "health": [], "love": [], "general": []}


def _label(score: float) -> tuple[str, str]:
    return ("favourable", "吉") if score >= 2 else ("unfavourable", "凶") if score <= -1.5 else ("neutral", "平")


def _moment(at: datetime | None, tz: float, place: str | None) -> tuple[BirthInput, datetime]:
    at = at or datetime.now().replace(second=0, microsecond=0)
    lat = lon = None
    if place:
        hit = geo.lookup(place, at.date())
        if hit:
            lat, lon, tz = hit["latitude"], hit["longitude"], hit["tz_offset_hours"]
    b = BirthInput(name="問事", birth_date=at.date(), birth_time=at.time(), place=place, latitude=lat, longitude=lon, tz_offset_hours=tz)
    return b, at


# --- 奇門 問事 -----------------------------------------------------------------------------------

def _qimen_ask(chart: Chart, topic: str, at: datetime, tz: float) -> dict:
    c = chart.chart
    palaces = {p["palace"]: p for p in c["palaces"]}
    p = X.exact_pillars(at, tz)
    ds, hs, hb = p["day"]["stem_idx"], p["hour"]["stem_idx"], p["hour"]["branch_idx"]
    xun_yi = {0: "戊", 10: "己", 20: "庚", 30: "辛", 40: "壬", 50: "癸"}
    def stem_for(s_idx, b_idx):
        return X.STEMS[s_idx] if X.STEMS[s_idx] != "甲" else xun_yi[X.gz_index(s_idx, b_idx) // 10 * 10]
    day_stem, hour_stem = stem_for(ds, p["day"]["branch_idx"]), stem_for(hs, hb)
    def find(key, val):
        return next((q for q in c["palaces"] if q.get(key) == val or (key == "star" and str(q.get("star", "")).startswith(val))), None)
    person = find("sky_stem", day_stem)
    matter = find("sky_stem", hour_stem)
    kind, name, yong_zh = _QIMEN_YONG.get(topic, _QIMEN_YONG["general"])
    yong = find("gate", c["zhishi"]) if kind == "zhishi" else find(kind, name)
    kong = X.kong_wang(hs, hb)
    score, reasons = 0.0, []
    def judge(q, who):
        nonlocal score
        if not q:
            return
        pe = _PAL_ELEM[q["palace"]]
        if q.get("gate"):
            ge = _GATE_ELEM[q["gate"]]
            if X.KE[ge] == pe:
                score -= 1
                reasons.append(f"{who}落{q['name']}宮，{q['gate']}（{ge}）剋宮（{pe}）→ 門迫，事多阻")
            elif q["gate_cls"] == "吉":
                score += 1
                reasons.append(f"{who}落{q['name']}宮臨{q['gate']}（三吉門）→ 順")
            elif q["gate_cls"] == "凶":
                score -= 0.5 if topic == "health" and q["gate"] == "死門" else 1
                reasons.append(f"{who}落{q['name']}宮臨{q['gate']}（凶門）→ 阻滯")
        st = str(q.get("star", "")).replace("禽", "")
        if st in _GOOD_STARS:
            score += 0.5
            reasons.append(f"{who}得{st}（吉星）")
        elif st in _BAD_STARS and not (topic == "health" and st == "天芮"):
            score -= 0.5
            reasons.append(f"{who}臨{st}（凶星）")
        if q.get("god") in _GOOD_GODS:
            score += 0.5
            reasons.append(f"{who}臨{q['god']}（吉神）")
        elif q.get("god") in _BAD_GODS:
            score -= 0.5
            reasons.append(f"{who}臨{q['god']}（凶神）→ {'驚恐虛詐' if q['god'] == '騰蛇' else '暗昧盜失' if q['god'] == '玄武' else '刑傷病訟'}")
        if q.get("sky_stem") in ("乙", "丙", "丁"):
            score += 0.5
            reasons.append(f"{who}得三奇 {q['sky_stem']}")
        if q.get("sky_stem") == "庚" and who != "求測人":
            score -= 0.5
            reasons.append(f"{who}臨庚 → 阻隔、對手")
        if any(b in kong for b in _PAL_BRANCH[q["palace"]]):
            score -= 1
            reasons.append(f"{who}落{q['name']}宮逢時旬空亡（{kong}）→ 事虛、未定，待出空")
    judge(yong, f"用神{name or c['zhishi']}")
    if yong and matter and yong["palace"] != matter["palace"]:
        judge(matter, "時干（所問之事）")
    if person and matter:
        pe, me = _PAL_ELEM[person["palace"]], _PAL_ELEM[matter["palace"]]
        if person["palace"] == matter["palace"]:
            score += 0.5
            reasons.append("日干與時干同宮 → 人事相隨，事在身邊")
        elif pe == me:
            score += 0.5
            reasons.append(f"事宮（{me}）與人宮（{pe}）比和 → 可成，需自己動")
        elif X.SHENG[me] == pe:
            score += 1
            reasons.append(f"事宮{matter['name']}（{me}）生人宮{person['name']}（{pe}）→ 事來就我，順")
        elif X.KE[me] == pe:
            score -= 1
            reasons.append(f"事宮{matter['name']}（{me}）剋人宮{person['name']}（{pe}）→ 事壓人，宜緩")
        elif X.KE[pe] == me:
            score += 0.5
            reasons.append(f"人宮（{pe}）剋事宮（{me}）→ 事可控，但費力")
        else:
            score -= 0.5
            reasons.append(f"人宮（{pe}）生事宮（{me}）→ 我耗於事，付出多")
    lucky = [f"{q['direction']}（{q['gate']}）" for q in c["palaces"] if q.get("gate_cls") == "吉"]
    v, vz = _label(score)
    facts = {"局": c["ju"], "值符／值使": f"{c['zhifu']}／{c['zhishi']}", "日干（求測人）": f"{X.STEMS[ds]}→{day_stem} 落{person['name'] if person else '—'}宮",
             "時干（所問之事）": f"{X.STEMS[hs]}→{hour_stem} 落{matter['name'] if matter else '—'}宮", "用神": yong_zh + (f" 落{yong['name']}宮（{yong['direction']}）：{yong['god']}・{yong['star']}・{yong['gate']}・{yong['sky_stem']}/{yong['earth_stem']}" if yong else " 未見"),
             "時旬空亡": kong, "吉方（三吉門）": lucky}
    period = _PAL_BRANCH[yong["palace"]] if yong else ""
    return {"verdict": v, "verdict_zh": vz, "score": round(score, 1), "reasons": reasons, "facts": facts, "lucky_directions": lucky,
            "timing_hint": f"應期參考：用神宮 {yong['name']} 之支 {'／'.join(period) or '—'}（逢{'／'.join(period)}日、時或月）" if yong and period else ""}


# --- 六壬 問事 -----------------------------------------------------------------------------------

def _liuren_ask(chart: Chart, topic: str, at: datetime, tz: float) -> dict:
    c = chart.chart
    de = c["day_stem_elem"]
    tr, gens = c["transmissions"], c["transmission_generals"]
    p = X.exact_pillars(at, tz)
    kong = X.kong_wang(p["day"]["stem_idx"], p["day"]["branch_idx"])
    rel_names = {"官": X._CTRL_OF[de], "財": X.KE[de], "父": X._GEN_OF[de], "子": X.SHENG[de], "兄": de}
    kinds, good_gens, yong_zh = _LR_TOPIC.get(topic, _LR_TOPIC["general"])
    score, reasons = 0.0, []
    elems = [X.BRANCH_ELEM[_B.index(b)] for b in tr]
    for k in kinds:
        hits = [b for b, e in zip(tr, elems) if e == rel_names[k]]
        if hits:
            score += 1
            reasons.append(f"類神（{k}，{rel_names[k]}）入傳：{'、'.join(hits)} → 所問之事有應")
        else:
            score -= 0.5
            reasons.append(f"類神（{k}，{rel_names[k]}）不入三傳 → 事未明，需靠他力")
    chu, mo = tr[0], tr[-1]
    e_mo = elems[-1]
    if X.SHENG[e_mo] == de or e_mo == de:
        score += 1
        reasons.append(f"末傳 {mo}（{e_mo}）{'生' if e_mo != de else '比和'}日干（{de}）→ 結果歸於己、終吉")
    elif X.KE[e_mo] == de:
        score -= 1
        reasons.append(f"末傳 {mo}（{e_mo}）剋日干（{de}）→ 終有壓力、結果不利")
    elif X.SHENG[de] == e_mo:
        score -= 0.5
        reasons.append(f"日干生末傳 {mo} → 終耗於事")
    else:
        score += 0.3
        reasons.append(f"日干剋末傳 {mo} → 事可制，但需出力")
    g_good = [g for g in gens if g in good_gens]
    g_bad = [g for g in gens if g in _LR_BAD and not (topic == "love" and g == "六合")]
    if g_good:
        score += 1
        reasons.append(f"三傳見{'、'.join(dict.fromkeys(g_good))}（本題吉將）")
    if topic == "health" and any(g in ("白虎", "螣蛇") for g in gens):
        score -= 1
        reasons.append("三傳見白虎／螣蛇 → 病訟驚恐之象，宜就醫")
    elif g_bad:
        score -= 0.5 * len(set(g_bad))
        reasons.append(f"三傳見{'、'.join(dict.fromkeys(g_bad))}（凶將）")
    kind = c["kind"]
    if "元首" in kind or "知一" in kind or "比用" in kind:
        score += 0.5
        reasons.append(f"課體 {kind.split('（')[0]} → 事有條理、順")
    elif "重審" in kind:
        score -= 0.5
        reasons.append("課體 重審（下賊上）→ 事從下起、需再審")
    elif "伏吟" in kind:
        reasons.append("課體 伏吟 → 事遲、宜靜守")
    elif "返吟" in kind:
        score -= 0.5
        reasons.append("課體 返吟 → 反覆、去而復來")
    elif "八專" in kind or "別責" in kind:
        reasons.append(f"課體 {kind.split('（')[0]} → 事涉他人、曖昧不清")
    if chu in kong:
        score -= 1
        reasons.append(f"初傳 {chu} 落日旬空亡（{kong}）→ 事虛、起而無成，待出空")
    v, vz = _label(score)
    facts = {"日干": f"{c['day_stem']}（{de}）", "月將加時": f"{c['yue_jiang']}將加{c['occupy']}時", "課體": kind,
             "三傳": "・".join(f"{b}（{g}）" for b, g in zip(tr, gens)), "類神": yong_zh, "日旬空亡": kong,
             "四課": [f"{k['upper']}/{k['lower']}（{k.get('general', '')}）" for k in c["courses"]]}
    return {"verdict": v, "verdict_zh": vz, "score": round(score, 1), "reasons": reasons, "facts": facts,
            "timing_hint": f"應期參考：末傳 {mo} 之日或時" + (f"；初傳 {chu} 出空之後" if chu in kong else "")}


# --- 梅花 數字起卦 / 字占 ---------------------------------------------------------------------------

def _hexagram(upper: str, lower: str, moving: int) -> dict:
    ben_num, ben_name = IC.kingwen(upper, lower)
    lines = IC._lines_bottom_top(upper, lower)
    hu_num, hu_name = IC.kingwen(IC._trigram_by_lines(tuple(lines[2:5])), IC._trigram_by_lines(tuple(lines[1:4])))
    changed = list(lines)
    changed[moving - 1] ^= 1
    bian_num, bian_name = IC.kingwen(IC._trigram_by_lines(tuple(changed[3:6])), IC._trigram_by_lines(tuple(changed[0:3])))
    yong, ti = (lower, upper) if moving <= 3 else (upper, lower)
    relation, verdict, auspicious = IC.wuxing_relation(ti, yong)
    return {"upper": upper, "lower": lower, "moving": moving, "lines": lines, "ben_num": ben_num, "ben_name": ben_name, "hu_num": hu_num, "hu_name": hu_name,
            "bian_num": bian_num, "bian_name": bian_name, "ti": ti, "yong": yong, "ti_wuxing": IC.TRIGRAMS[ti]["wuxing"], "yong_wuxing": IC.TRIGRAMS[yong]["wuxing"],
            "relation": relation, "verdict": verdict, "auspicious": auspicious, "ti_is_yang": IC.TRIGRAMS[ti]["yang"]}


def meihua_numbers(numbers: list[int] | None = None, text: str | None = None, *, hour_branch: int | None = None, add_hour: bool | None = None) -> dict:
    """梅花易數 數字起卦 / 字占.
    numbers: one number (split in halves: 前為上、後為下, 動爻 = 總和), two (上、下, 動爻 = 和), or three (上、下、動爻).
    text: character counts — 少為上、多為下 (even: halves; odd: the smaller first half is 上), 動爻 = 總字數 (+時數 by default).
    add_hour adds 時辰數 (子=1…亥=12) to the 動爻 sum; default True for text, False for numbers."""
    if text is not None and not numbers:
        chars = [ch for ch in text if not ch.isspace()]
        if not chars:
            raise ValueError("text is empty / 字占需至少一字")
        n = len(chars)
        n1 = n // 2
        n2 = n - n1
        numbers = [n1 or n2, n2]
        how = f"字占：{n} 字 → 前 {n1 or n2} 字為上卦、後 {n2} 字為下卦（少為上，多為下）"
        add_hour = True if add_hour is None else add_hour
    elif numbers:
        numbers = [int(x) for x in numbers]
        if any(x < 0 for x in numbers) or len(numbers) > 3:
            raise ValueError("numbers: 1–3 non-negative integers / 數字起卦需 1–3 個非負整數")
        if len(numbers) == 1:
            s = str(numbers[0])
            if len(s) >= 2:
                a, b = int(s[: len(s) // 2]), int(s[len(s) // 2:])
                how = f"單數起卦：{s} → 前半 {a} 為上卦、後半 {b} 為下卦"
                numbers = [a, b]
            else:
                how = f"單數起卦：{s} 為上卦亦為下卦"
                numbers = [numbers[0], numbers[0]]
        elif len(numbers) == 2:
            how = f"雙數起卦：{numbers[0]} 為上卦、{numbers[1]} 為下卦"
        else:
            how = f"三數起卦：{numbers[0]} 為上卦、{numbers[1]} 為下卦、{numbers[2]} 定動爻"
        add_hour = False if add_hour is None else add_hour
    else:
        raise ValueError("give numbers or text / 請給數字或字句")
    a, b = numbers[0], numbers[1]
    upper = IC.ORDER[(a % 8 or 8) - 1]
    lower = IC.ORDER[(b % 8 or 8) - 1]
    h = (hour_branch + 1) if (add_hour and hour_branch is not None) else 0
    if len(numbers) == 3:
        total = numbers[2] + h
    else:
        total = a + b + h
    moving = total % 6 or 6
    div = _hexagram(upper, lower, moving)
    div["numbers"] = {"input": numbers, "how": how, "hour": h, "upper_sum": a, "lower_sum": b, "moving_sum": total}
    return div


def _meihua_chart(div: dict, subject: str, at: datetime, method: str) -> Chart:
    n = div["numbers"]
    chain = [f"起卦（{method}）：{n['how']}" + (f"；＋時數 {n['hour']}" if n.get("hour") else "") + f" → 上卦 {div['upper']}、下卦 {div['lower']}、動爻 {div['moving']}（{n['moving_sum']} mod 6）",
             f"本卦：{div['ben_name']}（第 {div['ben_num']} 卦）", f"互卦：{div['hu_name']}　變卦：{div['bian_name']}（動爻 第 {div['moving']} 爻）",
             f"體用：體={div['ti']}（{div['ti_wuxing']}）・用={div['yong']}（{div['yong_wuxing']}）", f"五行：{div['relation']} → {div['verdict']}"]
    return Chart(system="iching", system_en="Plum-Blossom I Ching", system_zh="梅花易數", subject=subject, cast_at=at,
                 chart={"hexagram": div, "diagram": IC.line_diagram(div)}, reasoning_chain=chain,
                 readings={"起卦": n["how"], "本卦": div["ben_name"], "互卦": div["hu_name"], "變卦": div["bian_name"], "動爻": div["moving"],
                           "體用關係": div["relation"], "斷": div["verdict"], "auspicious": div["auspicious"]},
                 summary=f"{div['ben_name']}・{div['relation']}・{div['verdict']}")


def _meihua_ask(chart: Chart, topic: str) -> dict:
    h = chart.chart["hexagram"]
    score = 2 if h["verdict"] == "吉" else 1 if h["verdict"].startswith("小吉") else -2 if h["verdict"].startswith("凶") else 0
    reasons = [f"體 {h['ti']}（{h['ti_wuxing']}）・用 {h['yong']}（{h['yong_wuxing']}）：{h['relation']} → {h['verdict']}"]
    # 變卦 trigram that replaces the 用: its element vs 體
    changed = list(h["lines"]); changed[h["moving"] - 1] ^= 1
    new_yong = IC._trigram_by_lines(tuple(changed[0:3] if h["moving"] <= 3 else changed[3:6]))
    rel2, v2, _ = IC.wuxing_relation(h["ti"], new_yong)
    reasons.append(f"變卦 {h['bian_name']}：變後用卦 {new_yong}（{IC.TRIGRAMS[new_yong]['wuxing']}）對體 {rel2} → 結局{v2}")
    score += 1 if v2 == "吉" else 0.5 if v2.startswith("小吉") else -1 if v2.startswith("凶") else 0
    reasons.append(f"互卦 {h['hu_name']} 為過程")
    v, vz = _label(score)
    return {"verdict": v, "verdict_zh": vz, "score": round(score, 1), "reasons": reasons,
            "facts": {"本卦": h["ben_name"], "互卦": h["hu_name"], "變卦": h["bian_name"], "動爻": h["moving"], "體用": f"體{h['ti']}・用{h['yong']}・{h['relation']}", "起卦": h.get("numbers", {}).get("how", "時間起卦")},
            "timing_hint": f"應期參考：用卦 {h['yong']}（{h['yong_wuxing']}）之日月，或動爻數 {h['moving']}（日／月／時）"}


# --- 六爻 金錢卦 -----------------------------------------------------------------------------------

def liuyao_coins(coins: list[int], at: datetime, tz: float) -> tuple[dict, list[int], list[int]]:
    """Six coin throws bottom→top as 6 (老陰, 動) / 7 (少陽) / 8 (少陰) / 9 (老陽, 動). Returns (納甲 chart, moving lines, lines)."""
    coins = [int(x) for x in coins]
    if len(coins) != 6 or any(x not in (6, 7, 8, 9) for x in coins):
        raise ValueError("coins: six values of 6/7/8/9, bottom line first / 六個 6–9 的數，自初爻起")
    lines = [1 if x in (7, 9) else 0 for x in coins]
    moving_all = [i + 1 for i, x in enumerate(coins) if x in (6, 9)]
    moving = moving_all[-1] if moving_all else 0            # 多爻動：以上爻為主（其餘列為亦動）
    p = X.exact_pillars(at, tz)
    g = LY.cast(lines, moving, p["day"]["stem_idx"], p["day"]["branch_idx"], p["month"]["branch_idx"])
    for r in g["lines"]:
        if r["pos"] in moving_all and r["pos"] != moving:
            r["notes"].append("亦動")
    return g, moving_all, lines


def _liuyao_chart(g: dict, moving_all: list[int], lines: list[int], coins: list[int], subject: str, at: datetime) -> Chart:
    rows = g["lines"]
    shi_line = rows[g["shi"] - 1]
    mv = rows[g["moving"] - 1] if g["moving"] else None
    chain = [f"金錢卦：{'、'.join(map(str, coins))}（自初爻起；6 老陰動、9 老陽動）→ 本卦 {g['name']}（第 {g['num']} 卦），{g['palace']}宮（{g['palace_elem']}），"
             f"世在{g['shi']}爻、應在{g['ying']}爻；動爻 {'、'.join(map(str, moving_all)) or '無'}；月建 {g['month_branch']}、日辰 {g['day_gz']}（旬空 {g['kong_wang']}）。",
             "納甲：" + "、".join(f"{r['pos']}爻{r['stem']}{r['branch']}{r['relative']}{'（世）' if r['shi'] else '（應）' if r['ying'] else ''}" for r in rows) + "。",
             "六神：" + "、".join(f"{r['pos']}爻{r['god']}" for r in rows) + "。",
             "旺衰：" + "、".join(f"{r['pos']}爻{r['branch']}{r['relative']} " + "/".join(r["notes"]) for r in rows) + "。"]
    if g["hidden"]:
        chain.append("伏神：" + "、".join(f"{h['relative']}{h['stem']}{h['branch']} 伏於{h['pos']}爻{h['under']}之下" for h in g["hidden"]) + "。")
    if g["changed"]:
        c = g["changed"]
        chain.append(f"動爻：{g['moving']}爻 {mv['relative']}{mv['stem']}{mv['branch']} 動，變 {c['line']['relative']}{c['line']['stem']}{c['line']['branch']}（{c['relation']}）→ 變卦 {c['name']}（{c['palace']}宮）。")
    div = {"lines": lines, "moving": g["moving"]}
    return Chart(system="liuyao", system_en="Liu Yao · Six Lines", system_zh="六爻（納甲）", subject=subject, cast_at=at,
                 chart={"hexagram": g, "diagram": IC.line_diagram(div), "coins": coins, "moving_all": moving_all}, reasoning_chain=chain,
                 readings={"本卦": f"{g['name']}（{g['palace']}宮{g['palace_elem']}）", "世應": f"世{g['shi']}爻 {shi_line['relative']}{shi_line['branch']}・應{g['ying']}爻 {rows[g['ying'] - 1]['relative']}{rows[g['ying'] - 1]['branch']}",
                           "六爻": "　".join(f"{r['pos']}:{r['god']}{r['relative']}{r['stem']}{r['branch']}{'動' if r['moving'] else ''}[{'/'.join(r['notes'])}]" for r in rows),
                           "伏神": "、".join(f"{h['relative']}{h['stem']}{h['branch']}伏{h['pos']}爻" for h in g["hidden"]) or "—",
                           "動爻": f"{g['moving']}爻 {mv['relative']}{mv['branch']} → {g['changed']['line']['relative']}{g['changed']['line']['branch']}（{g['changed']['relation']}）" if g["changed"] else "—",
                           "變卦": g["changed"]["name"] if g["changed"] else "—", "月建日辰": f"月建 {g['month_branch']}・日辰 {g['day_gz']}・旬空 {g['kong_wang']}"},
                 summary=f"{g['name']}（{g['palace']}宮）・世 {shi_line['relative']}{shi_line['branch']}" + (f"・{g['moving']}爻{mv['relative']}動→{g['changed']['name']}" if g["changed"] else "・無動爻"))


def _liuyao_ask(chart: Chart, topic: str) -> dict:
    g = chart.chart["hexagram"]
    rows = g["lines"]
    yong = list(_LY_YONG.get(topic, []))
    shi = next(r for r in rows if r["shi"])
    ying = next(r for r in rows if r["ying"])
    targets = [r for r in rows if r["relative"] in yong] if yong else [shi]
    score, reasons = 0.0, []
    def strength(r):
        n = r["notes"]
        s = 0
        if any(x.startswith(("月旺", "月相")) for x in n) or "日生" in n or "日臨" in n:
            s += 1
        if any(x.startswith(("月囚", "月死")) for x in n) or "日剋" in n:
            s -= 1
        if "月破" in n or "旬空" in n:
            s -= 1
        return s
    who = "用神" if yong else "世爻"
    if yong and not targets:
        score -= 1
        hid = [h for h in g["hidden"] if h["relative"] in yong]
        reasons.append(f"用神{'／'.join(yong)}不上卦" + (f"，伏於{hid[0]['pos']}爻{hid[0]['under']}之下 → 事隱而未現，需等引拔" if hid else " → 事未明"))
    for r in targets:
        s = strength(r)
        score += s
        reasons.append(f"{who} {r['pos']}爻{r['relative']}{r['branch']}：{'/'.join(r['notes'])} → {'旺相有氣' if s > 0 else '休囚無力' if s < 0 else '平'}" + ("，臨世爻" if r["shi"] else "，臨應爻" if r["ying"] else ""))
        if r["moving"] and g["changed"]:
            rel = g["changed"]["relation"]
            d = 1 if rel in ("化回頭生", "化進神") else -1 if rel in ("化回頭剋", "化退神") else -0.5 if rel == "化洩" else 0
            score += d
            reasons.append(f"{who}動而{rel} → {'吉' if d > 0 else '凶' if d < 0 else '平'}")
    ss = strength(shi)
    score += 0.5 * ss
    reasons.append(f"世爻 {shi['pos']}爻{shi['relative']}{shi['branch']}（{'/'.join(shi['notes'])}）→ 自身{'有力' if ss > 0 else '無力' if ss < 0 else '平'}")
    if (ying["branch_idx"] - shi["branch_idx"]) % 12 == 6:
        score -= 0.5
        reasons.append("世應相沖 → 人事不合、反覆")
    elif tuple(sorted((ying["branch_idx"], shi["branch_idx"]))) in X._LIUHE:
        score += 0.5
        reasons.append("世應相合 → 人事相合、可成")
    if g["moving"]:
        mv = rows[g["moving"] - 1]
        if mv["relative"] == "官鬼" and topic == "health":
            score -= 1
            reasons.append("官鬼動 → 病勢動，宜就醫")
        elif mv["relative"] == "子孫" and topic == "health":
            score += 1
            reasons.append("子孫（醫藥）動 → 病有解")
        if mv["relative"] == "兄弟" and topic in ("wealth", "love"):
            score -= 1
            reasons.append(f"兄弟動 → {'劫財、破耗' if topic == 'wealth' else '競爭、阻隔'}")
    if topic == "health":
        ghosts = [r for r in rows if r["relative"] == "官鬼" and strength(r) > 0]
        if ghosts:
            score -= 1
            reasons.append(f"官鬼{'、'.join(r['branch'] for r in ghosts)}旺 → 病根有力")
    v, vz = _label(score)
    facts = {"卦": f"{g['name']}（{g['palace']}宮）世{g['shi']}應{g['ying']}", "用神": yong or "世爻", "動爻": f"{g['moving']}爻 → {g['changed']['name']}（{g['changed']['relation']}）" if g["changed"] else "無",
             "月建日辰": f"{g['month_branch']}月 {g['day_gz']}日・旬空 {g['kong_wang']}", "六爻": [f"{r['pos']}{r['god']}{r['relative']}{r['branch']}{'動' if r['moving'] else ''}[{'/'.join(r['notes'])}]" for r in rows]}
    tgt = targets[0] if targets else shi
    return {"verdict": v, "verdict_zh": vz, "score": round(score, 1), "reasons": reasons, "facts": facts,
            "timing_hint": f"應期參考：{who} {tgt['branch']} 值日／月，或合{tgt['branch']}、沖{tgt['branch']}之時" + ("；旬空者出空之日" if "旬空" in tgt["notes"] else "")}


# --- the sitting ------------------------------------------------------------------------------------

def ask(system: str, question: str | None = None, *, at: datetime | None = None, tz: float = 8.0, place: str | None = None,
        numbers: list[int] | None = None, text: str | None = None, coins: list[int] | None = None, qimen_method: str = "chaibu",
        read: bool = False, lang: str = "zh") -> dict[str, Any]:
    """One question, one cast at the moment of asking (or from the numbers / coins given), with a question-oriented verdict."""
    if system not in SYSTEMS:
        raise ValueError(f"ask: system must be one of {', '.join(SYSTEMS)}")
    b, at = _moment(at, tz, place)
    tz = b.tz_offset_hours
    topic = F.classify(question)
    subject = f"問事：{question or '—'} · {at.isoformat(timespec='minutes')}" + (f" · {place}" if place else "")
    method = "時間起卦" if system in ("iching", "liuyao") else "時盤" if system == "qimen" else "時課"
    if system == "iching" and (numbers or text):
        hb = X.exact_pillars(at, tz)["hour"]["branch_idx"]
        div = meihua_numbers(numbers, text, hour_branch=hb)
        method = "字占" if text and not numbers else "數字起卦"
        chart = _meihua_chart(div, subject, at, method)
    elif system == "liuyao" and coins:
        g, moving_all, lines = liuyao_coins(coins, at, tz)
        method = "金錢卦"
        chart = _liuyao_chart(g, moving_all, lines, [int(x) for x in coins], subject, at)
    else:
        chart = casting.cast(system, b, qimen_method=qimen_method)
        chart.subject = subject
    if system == "qimen":
        verdict = _qimen_ask(chart, topic, at, tz)
    elif system == "liuren":
        verdict = _liuren_ask(chart, topic, at, tz)
    elif system == "iching":
        verdict = _meihua_ask(chart, topic)
    elif system == "liuyao":
        verdict = _liuyao_ask(chart, topic)
    else:
        c = chart.chart
        s = 2 if c.get("luck") == "吉" else -2
        verdict = {"verdict": "favourable" if s > 0 else "unfavourable", "verdict_zh": "吉" if s > 0 else "凶", "score": s,
                   "reasons": [f"落{c['result']}（{c['luck']}）：{c['text']}", f"路徑 {' → '.join(c['path'])}"],
                   "facts": {"課": c["result"], "五行": c["elem"], "方位": c["direction"]}, "timing_hint": f"應期參考：{c['result']}屬{c['elem']}，方位{c['direction']}"}
    out = {"system": system, "system_zh": SYSTEMS[system], "question": question, "topic": topic, "topic_label": F.topic_label(topic),
           "at": at.isoformat(timespec="minutes"), "tz_offset_hours": tz, "place": place, "method": method,
           "chart": chart.model_dump(mode="json"), "verdict": verdict,
           "summary": f"{SYSTEMS[system]}問事「{question or '—'}」（{method}）：{chart.summary} → {verdict['verdict_zh']}（{verdict['score']:+}）"}
    if read:
        from fortune.interpret import interpret
        q = (question or "") + f"\n\n[問事判斷 / verdict: {verdict['verdict_zh']} {verdict['score']:+}]\n" + "\n".join(f"- {r}" for r in verdict["reasons"]) + ("\n" + verdict.get("timing_hint", "") if verdict.get("timing_hint") else "")
        out["interpretation"] = interpret(chart, focus=q, lang=lang).interpretation
    return out
