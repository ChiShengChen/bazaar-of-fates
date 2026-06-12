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
    "術語保留原形，結尾各以一段白話總結。"
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
