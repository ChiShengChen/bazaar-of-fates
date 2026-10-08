"""Chart → reading / 命盤 → 解讀.

Turns a cast Chart's deterministic facts into a readable, bilingual (English + 中文)
divination reading. The author prompts (prompts/<system>/*.md) supply each
tradition's voice; the deterministic facts are handed over verbatim so the model
narrates the real 命盤 rather than inventing one. On the mock backend this returns a
faithful facts digest. / mock 後端回傳忠實的事實摘要。
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from fortune.schemas import Chart, Reading
from fortune.shared.llm import complete, stream

_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

LANGS = ("zh", "en", "both")
_LANG = {
    "zh": "Write the reading in 繁體中文 only (keep the divination terms as they are). 全文只用繁體中文。",
    "en": "Write the reading in English only (keep the divination terms 干支/卦名/宮名 in their original script, glossed once).",
    "both": "Write the reading BILINGUALLY: an English section first, then a 中文 section (同樣內容的中文解讀). 先英文、後中文。",
}


def lang_instruction(lang: str | None) -> str:
    return _LANG.get(lang or "both", _LANG["both"])

_SYSTEM = (
    "You are a rigorous yet warm diviner. The facts below were cast by deterministic "
    "code (planetary longitudes / four pillars / hexagram / nine palaces… all really "
    "computed, never fabricated). Read ONLY from these facts, in the idiom and voice of "
    "the given tradition; be clear, honest, and never fear-mongering. Do NOT invent any "
    "chart element not present in the facts.\n"
    "Keep the divination terms (干支/卦名/宮名…) in their original form.\n"
    "你是一位嚴謹而溫暖的命理師：只依據以上確定性排出的事實解讀，術語保留原形，結尾以一段白話總結。\n"
    "When the facts include houses, an ascendant, a chart ruler (命主星), angular planets, "
    "aspects, 喜用神, 四化, daśā, 大運/流年, or a Solar/Lunar Return (太陽/月亮回歸) ascendant & "
    "highlights for the year/month ahead, weave those structures into the reading "
    "(e.g. the chart ruler's sign & house, planets on the angles, the tightest aspects) "
    "rather than reading planets in isolation. / 若事實含宮位、上升、命主星、四正星、相位、"
    "喜用神、四化、大運流年，請把這些結構納入解讀，不要孤立論斷。"
)


def _voice(system: str) -> str:
    d = _PROMPTS / system
    if not d.is_dir():
        return ""
    text = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(d.glob("*.md")))
    return f"\n\n[Style reference for {system} / {system} 門派風格參考]\n{text[:4000]}" if text else ""


def _prompts(chart: Chart, focus: str | None, lang: str | None = None) -> tuple[str, str]:
    """(system, user) prompts shared by the sync and streaming paths.
    `subject` (who) and `focus` (what they ask) are surfaced prominently up top. When a focus
    is given, the topic-relevant facts (fortune.focus.extract) lead the prompt and the model is
    asked to answer that question first."""
    from fortune.focus import classify, extract, topic_label
    facts = {
        "system": chart.system_en, "system_zh": chart.system_zh,
        "subject": chart.subject, "summary": chart.summary,
        "reasoning_chain": chart.reasoning_chain, "chart_elements": chart.readings,
    }
    if chart.ascendant:
        facts["ascendant"] = {k: chart.ascendant.get(k) for k in ("sign", "sign_zh", "house_system", "longitude")}
    head = f"命主 / Subject: {chart.subject}\n"
    focus_block = ""
    if focus:
        topic = classify(focus)
        fx = extract(chart, topic)
        chart.readings.setdefault("focus_topic", topic_label(topic))
        head += (f"★ 命主特別想問 / The subject specifically asks about: {focus}（主題 topic: {topic_label(topic)}）\n"
                 "  （先針對此問題回答，再補充整體 / answer this question FIRST, then the wider picture）\n")
        focus_block = (f"\n★ Facts bearing on the question / 與本題直接相關的事實 (this tradition's own rule gives: "
                       f"{fx['verdict']} — {fx['reason']})：\n{json.dumps(fx['facts'], ensure_ascii=False, indent=2)}\n")
    user = (
        head + focus_block
        + f"\nChart facts (JSON) / 命盤事實：\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\n"
        + "Read from the facts above. / 請依上述事實解讀。 " + lang_instruction(lang)
    )
    return _SYSTEM + "\n" + lang_instruction(lang) + _voice(chart.system), user


def interpret(chart: Chart, *, focus: str | None = None, lang: str | None = None) -> Reading:
    system, user = _prompts(chart, focus, lang)
    return Reading(**chart.model_dump(), interpretation=complete(system, user))


def interpret_stream(chart: Chart, *, focus: str | None = None, lang: str | None = None) -> Iterator[str]:
    """Yield the reading text incrementally (for SSE)."""
    system, user = _prompts(chart, focus, lang)
    yield from stream(system, user)


_SYNTHESIS_SYSTEM = (
    "You are a senior diviner chairing a panel: several traditions have each cast the same person's chart "
    "and each has given a short, rule-based verdict on ONE question. Use ONLY the per-system facts below. "
    "Write: (1) a direct answer to the question in 2–4 sentences, stating the overall lean; (2) where the "
    "systems AGREE and what they jointly point at; (3) where they CONFLICT, explaining in each tradition's own "
    "terms why it reads differently (timing vs. natal disposition, etc.) rather than papering over it; "
    "(4) timing cues (大運/流年/daśā/transits) if present; (5) one practical, kind takeaway. Never fear-mongering, "
    "never deterministic; cite systems by name. "
    "你主持一場跨門派會診：多套命理對同一個問題各給了依規則的判斷，只依下列事實，先直接回答問題與整體傾向，"
    "再講各系統一致之處、衝突之處（用各門派自己的道理解釋為何不同，不要含糊帶過）、時間線索，最後給一句務實的建議。"
)


def interpret_synthesis(syn: dict, *, focus: str | None, lang: str | None = None) -> str:
    rows = [{"system": f"{r['system_en']} · {r['system_zh']}", "verdict": r["verdict"], "why": r["reason"], "facts": r["facts"]}
            for r in syn.get("systems", [])]
    head = (f"Question / 問題: {focus or '整體運勢 overall'}（topic: {syn.get('topic_label')}）\n"
            f"Tally / 統計: {syn.get('tally')} → lean {syn.get('lean')}；agree: {syn.get('consensus')}；conflict: {syn.get('conflicts')}\n")
    user = head + f"\nPer-system facts (JSON):\n{json.dumps(rows, ensure_ascii=False, indent=2)}\n\n" + lang_instruction(lang)
    return complete(_SYNTHESIS_SYSTEM + "\n" + lang_instruction(lang), user)


_SYNASTRY_SYSTEM = (
    "You are a relationship astrologer reading a 合盤 (synastry). Use ONLY the two charts "
    "and their cross-aspects below. Discuss the relationship dynamic — where the two charts "
    "support each other (trine/sextile/conjunction) and where they challenge (square/opposition) "
    "— honestly and kindly, never deterministically. "
    "你是合盤占星師：只依據以下兩張命盤與星際相位，論關係的契合與張力。"
)


_COMPOSITE_SYSTEM = (
    "You are an astrologer reading a COMPOSITE chart — the midpoint chart that represents "
    "the relationship itself as a single entity (not either person). Use ONLY the planets, "
    "aspects, and ascendant below. Describe the relationship's purpose, character, and growth "
    "edges, honestly and kindly. "
    "你在讀『組合中點盤』——代表這段關係本身的命盤，只依據以下資料。"
)


def interpret_composite(composite: dict, *, focus: str | None = None, lang: str | None = None) -> str:
    asc = composite.get("ascendant") or {}
    facts = {
        "composite_ascendant": f"{asc.get('sign', '?')} {asc.get('sign_zh', '')}".strip() or None,
        "planets": [f"{p['body']} {p['sign']} {p['sign_zh']}" for p in composite.get("planets", [])],
        "aspects": [f"{x['a']} {x['type']} {x['b']} ({x['orb']}°)" for x in composite.get("aspects", [])],
    }
    head = "Composite (midpoint) chart of the relationship.\n組合中點盤（關係本身的命盤）。\n"
    if focus:
        head += f"★ They ask about / 想問: {focus}\n"
    user = head + f"\nFacts (JSON):\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\nRead from the facts."
    return complete(_COMPOSITE_SYSTEM + "\n" + lang_instruction(lang), user + " " + lang_instruction(lang))


_DAVISON_SYSTEM = (
    "You are an astrologer reading a DAVISON relationship chart — a real ephemeris chart "
    "cast for the midpoint moment in time and the midpoint location of the two births "
    "(unlike the composite, this is an actual sky at an actual time/place). Use ONLY the "
    "data below; describe the relationship's lived character and timing. "
    "你在讀 Davison 時空中點盤（兩人生時與生地的真實中點所排的實際天象盤），只依資料。"
)


def interpret_davison(davison: dict, *, focus: str | None = None, lang: str | None = None) -> str:
    asc = davison.get("ascendant") or {}
    facts = {
        "midpoint_datetime_UT": davison.get("datetime"),
        "midpoint_location": [davison.get("latitude"), davison.get("longitude")],
        "ascendant": f"{asc.get('sign', '?')} {asc.get('sign_zh', '')}".strip() or None,
        "planets": [f"{p['body']} {p['sign']} {p['sign_zh']}" for p in davison.get("planets", [])],
        "aspects": [f"{x['a']} {x['type']} {x['b']} ({x['orb']}°)" for x in davison.get("aspects", [])],
    }
    head = "Davison time-space midpoint chart.\nDavison 時空中點盤。\n"
    if focus:
        head += f"★ They ask about / 想問: {focus}\n"
    user = head + f"\nFacts (JSON):\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\nRead from the facts."
    return complete(_DAVISON_SYSTEM + "\n" + lang_instruction(lang), user + " " + lang_instruction(lang))


_GROUP_SYSTEM = (
    "You are an astrologer reading GROUP dynamics (團體合盤) from the pairwise cross-aspect "
    "scores below. Describe the group's overall cohesion, the bonds that flow easily, and the "
    "tensions to mind — honestly and kindly, never deterministically. "
    "你在讀團體合盤：依下列兩兩相位分數，論整體默契、順暢的連結與需留意的張力。"
)


def interpret_group(grp: dict, *, focus: str | None = None, lang: str | None = None) -> str:
    facts = {
        "people": [p["summary"] for p in grp.get("people", [])],
        "pairs": [f"{p['a']}↔{p['b']}: net {p['net']} (harmonious {p['harmonious']} / challenging {p['challenging']})"
                  for p in grp.get("pairs", [])],
        "most_in_sync": (grp.get("best_pair") or {}).get("a") and
        f"{grp['best_pair']['a']}↔{grp['best_pair']['b']}",
        "most_tension": (grp.get("tense_pair") or {}).get("a") and
        f"{grp['tense_pair']['a']}↔{grp['tense_pair']['b']}",
    }
    head = "Group dynamics 團體合盤.\n"
    if focus:
        head += f"★ They ask about / 想問: {focus}\n"
    user = head + f"\nFacts (JSON):\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\nRead from the facts."
    return complete(_GROUP_SYSTEM + "\n" + lang_instruction(lang), user + " " + lang_instruction(lang))


_ANNUAL_SYSTEM = (
    "You are a diviner writing a person's ANNUAL report (年度報告) for one year, drawing on "
    "several traditions at once: the Western Solar Return, BaZi 流年/大運, 紫微 流年四化, and "
    "Jyotiṣa Mahādaśā. Use ONLY the facts below; synthesise them into one coherent year-ahead "
    "outlook — note where the systems agree, be honest and kind, never fear-mongering. Give a "
    "short overview, then a few themes (career/relationships/wellbeing as the facts suggest), "
    "then a one-line takeaway. "
    "你在寫某人某年的年度報告，綜合太陽回歸、八字流年大運、紫微流年四化、Jyotiṣa 大運。"
)


def interpret_annual(report: dict, *, focus: str | None = None, lang: str | None = None) -> str:
    head = f"Annual report 年度報告 · {report.get('subject')} · {report.get('year')}\n"
    if focus:
        head += f"★ They ask about / 想問: {focus}\n"
    user = head + f"\nFacts (JSON):\n{json.dumps(report.get('sections', {}), ensure_ascii=False, indent=2)}\n\nWrite the report."
    return complete(_ANNUAL_SYSTEM + "\n" + lang_instruction(lang), user + " " + lang_instruction(lang))


_OVERVIEW_SYSTEM = (
    "You are a diviner sketching a person's MULTI-YEAR arc from a compact per-year table "
    "(Solar Return ascendant, BaZi 流年 element & favourability, BaZi 大運 period, 紫微 year "
    "stem, Jyotiṣa daśā lord). Use ONLY the table; describe the overall trajectory — the "
    "smoother stretches and the more demanding ones, and any turning points (a new 大運, a "
    "daśā change). Be honest and kind, not deterministic. "
    "你在勾勒某人連續數年的運勢起伏：依下表的逐年資料，講整體走向與轉折。"
)


def interpret_overview(ov: dict, *, focus: str | None = None, lang: str | None = None) -> str:
    head = f"Multi-year outlook 多年運勢 · {ov.get('subject')} · {ov.get('start_year')}–{ov.get('start_year', 0) + ov.get('count', 1) - 1}\n"
    if focus:
        head += f"★ They ask about / 想問: {focus}\n"
    facts = {"years": ov.get("years", []), "turning_points": ov.get("turning_points", [])}
    user = head + f"\nFacts (JSON):\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\nSketch the arc; call out the turning-point years."
    return complete(_OVERVIEW_SYSTEM + "\n" + lang_instruction(lang), user + " " + lang_instruction(lang))


def interpret_synastry(syn, *, focus: str | None = None, lang: str | None = None) -> str:
    facts = {
        "person_A": {"subject": syn.a.subject, "summary": syn.a.summary},
        "person_B": {"subject": syn.b.subject, "summary": syn.b.summary},
        "cross_aspects": [f"A {x['a']} {x['type']} B {x['b']} ({x['orb']}°)" for x in syn.cross_aspects],
        "headline": syn.summary,
    }
    head = "合盤 / Synastry reading.\n"
    if focus:
        head += f"★ They ask about / 想問: {focus}\n"
    user = (head + f"\nFacts (JSON):\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\n"
            "Read the relationship from the facts.")
    return complete(_SYNASTRY_SYSTEM + "\n" + lang_instruction(lang), user + " " + lang_instruction(lang))


_ZERI_SYSTEM = (
    "You are a diviner helping someone choose a date for a specific purpose. The candidate days below have "
    "already been scored by rules (黃曆 宜忌/建除/神煞, 八字 流日 vs 喜用 and 沖破空亡, 紫微 流日四化, 奇門 值使與吉方, "
    "小六壬). Use ONLY those facts. Recommend the top 2–3 days and, for each, the best 時辰 and 方位; say in one "
    "line why each works for THIS person (their 喜用/日柱), and name the days to avoid and why. Short, practical, kind. "
    "你在幫人擇日：依下列已評分的日期事實，推薦 2–3 個最佳日期與各自的吉時吉方，一句說明為何合此人命局，並點出應避開的日子。"
)


def interpret_zeri(out: dict, *, lang: str | None = None) -> str:
    best = [d for d in out.get("days", []) if d["date"] in out.get("best", [])][:5]
    rows = [{"date": d["date"], "weekday": d["weekday"], "lunar": d["lunar"], "干支": d["gz"], "score": d["score"], "grade": d["grade"],
             "reasons": [f"{r['src']} {r['delta']:+} {r['text']}" for r in d["reasons"][:7]],
             "best_hours": [f"{h['branch']}時 {h['hours']}（{h['score']:+}）" for h in d.get("hours", []) if h.get("best")],
             "lucky_dirs": d["qimen"]["lucky_dirs"]} for d in best]
    avoid = [{"date": d["date"], "why": [r["text"] for r in d["reasons"] if r["delta"] <= -2][:2]} for d in out.get("days", []) if d["grade"] == 1][:6]
    head = f"Purpose / 目的: {out.get('purpose_label')}　Range: {out.get('start')} → {out.get('end')}　Subject: {out.get('subject')}\n"
    user = head + f"\nTop days (JSON):\n{json.dumps(rows, ensure_ascii=False, indent=1)}\n\nDays to avoid:\n{json.dumps(avoid, ensure_ascii=False)}\n\n" + lang_instruction(lang)
    return complete(_ZERI_SYSTEM + "\n" + lang_instruction(lang), user)
