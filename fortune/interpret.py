"""Chart → reading / 命盤 → 解讀.

Turns a cast Chart's deterministic facts into a readable, bilingual (English + 中文)
divination reading. The synced author prompts (prompts/<system>/*.md) supply each
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

_SYSTEM = (
    "You are a rigorous yet warm diviner. The facts below were cast by deterministic "
    "code (planetary longitudes / four pillars / hexagram / nine palaces… all really "
    "computed, never fabricated). Read ONLY from these facts, in the idiom and voice of "
    "the given tradition; be clear, honest, and never fear-mongering. Do NOT invent any "
    "chart element not present in the facts.\n"
    "Write the reading BILINGUALLY: an English section first, then a 中文 section "
    "(同樣內容的中文解讀). Keep the divination terms (干支/卦名/宮名…) in their original form.\n"
    "你是一位嚴謹而溫暖的命理師：只依據以上確定性排出的事實解讀，先英文、後中文，"
    "術語保留原形，結尾各以一段白話總結。\n"
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


def _prompts(chart: Chart, focus: str | None) -> tuple[str, str]:
    """(system, user) prompts shared by the sync and streaming paths.
    `subject` (who) and `focus` (what they ask) are surfaced prominently up top."""
    facts = {
        "system": chart.system_en, "system_zh": chart.system_zh,
        "subject": chart.subject, "summary": chart.summary,
        "reasoning_chain": chart.reasoning_chain, "chart_elements": chart.readings,
    }
    if chart.ascendant:
        facts["ascendant"] = {k: chart.ascendant.get(k) for k in ("sign", "sign_zh", "house_system", "longitude")}
    head = f"命主 / Subject: {chart.subject}\n"
    if focus:
        head += (f"★ 命主特別想問 / The subject specifically asks about: {focus}\n"
                 "  （請在解讀中明確針對此重點回應 / address this focus directly）\n")
    user = (
        head + f"\nChart facts (JSON) / 命盤事實：\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\n"
        "Read from the facts above, bilingually (English then 中文). / 請依上述事實雙語解讀（先英後中）。"
    )
    return _SYSTEM + _voice(chart.system), user


def interpret(chart: Chart, *, focus: str | None = None) -> Reading:
    system, user = _prompts(chart, focus)
    return Reading(**chart.model_dump(), interpretation=complete(system, user))


def interpret_stream(chart: Chart, *, focus: str | None = None) -> Iterator[str]:
    """Yield the reading text incrementally (for SSE)."""
    system, user = _prompts(chart, focus)
    yield from stream(system, user)


_SYNASTRY_SYSTEM = (
    "You are a relationship astrologer reading a 合盤 (synastry). Use ONLY the two charts "
    "and their cross-aspects below. Discuss the relationship dynamic — where the two charts "
    "support each other (trine/sextile/conjunction) and where they challenge (square/opposition) "
    "— honestly and kindly, never deterministically. Write English first, then 中文. "
    "你是合盤占星師：只依據以下兩張命盤與星際相位，論關係的契合與張力，先英後中。"
)


_COMPOSITE_SYSTEM = (
    "You are an astrologer reading a COMPOSITE chart — the midpoint chart that represents "
    "the relationship itself as a single entity (not either person). Use ONLY the planets, "
    "aspects, and ascendant below. Describe the relationship's purpose, character, and growth "
    "edges, honestly and kindly. English first, then 中文. "
    "你在讀『組合中點盤』——代表這段關係本身的命盤，只依據以下資料，先英後中。"
)


def interpret_composite(composite: dict, *, focus: str | None = None) -> str:
    asc = composite.get("ascendant") or {}
    facts = {
        "composite_ascendant": f"{asc.get('sign', '?')} {asc.get('sign_zh', '')}".strip() or None,
        "planets": [f"{p['body']} {p['sign']} {p['sign_zh']}" for p in composite.get("planets", [])],
        "aspects": [f"{x['a']} {x['type']} {x['b']} ({x['orb']}°)" for x in composite.get("aspects", [])],
    }
    head = "Composite (midpoint) chart of the relationship.\n組合中點盤（關係本身的命盤）。\n"
    if focus:
        head += f"★ They ask about / 想問: {focus}\n"
    user = head + f"\nFacts (JSON):\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\nRead bilingually."
    return complete(_COMPOSITE_SYSTEM, user)


_DAVISON_SYSTEM = (
    "You are an astrologer reading a DAVISON relationship chart — a real ephemeris chart "
    "cast for the midpoint moment in time and the midpoint location of the two births "
    "(unlike the composite, this is an actual sky at an actual time/place). Use ONLY the "
    "data below; describe the relationship's lived character and timing. English then 中文. "
    "你在讀 Davison 時空中點盤（兩人生時與生地的真實中點所排的實際天象盤），只依資料、先英後中。"
)


def interpret_davison(davison: dict, *, focus: str | None = None) -> str:
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
    user = head + f"\nFacts (JSON):\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\nRead bilingually."
    return complete(_DAVISON_SYSTEM, user)


_GROUP_SYSTEM = (
    "You are an astrologer reading GROUP dynamics (團體合盤) from the pairwise cross-aspect "
    "scores below. Describe the group's overall cohesion, the bonds that flow easily, and the "
    "tensions to mind — honestly and kindly, never deterministically. English then 中文. "
    "你在讀團體合盤：依下列兩兩相位分數，論整體默契、順暢的連結與需留意的張力，先英後中。"
)


def interpret_group(grp: dict, *, focus: str | None = None) -> str:
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
    user = head + f"\nFacts (JSON):\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\nRead bilingually."
    return complete(_GROUP_SYSTEM, user)


def interpret_synastry(syn, *, focus: str | None = None) -> str:
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
            "Read the relationship bilingually (English then 中文).")
    return complete(_SYNASTRY_SYSTEM, user)
