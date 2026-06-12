"""命盤 → 解讀. Turns a cast Chart's deterministic facts into readable 命理 prose.

The synced author prompts (prompts/<system>/*.md) supply each tradition's voice; the
deterministic facts are handed over verbatim so the model narrates the real 命盤
rather than inventing one. On the mock backend this returns a faithful facts digest.
"""

from __future__ import annotations

import json
from pathlib import Path

from fortune.schemas import Chart, Reading
from fortune.shared.llm import complete

_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

_SYSTEM = (
    "你是一位嚴謹而溫暖的命理師。以下提供的是程式以確定性規則排出的命盤事實"
    "（行星經度／四柱／卦象／九宮…，皆為真實計算，未經杜撰）。請只根據這些事實，"
    "用該門派的術語與口吻，給出條理清楚、誠懇、不販賣恐懼的解讀。"
    "結尾以一段白話總結。切勿捏造事實中沒有的盤面。"
)


def _voice(system: str) -> str:
    d = _PROMPTS / system
    if not d.is_dir():
        return ""
    text = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(d.glob("*.md")))
    return f"\n\n【{system} 門派風格參考】\n{text[:4000]}" if text else ""


def interpret(chart: Chart, *, focus: str | None = None) -> Reading:
    facts = {
        "命理系統": chart.system_zh,
        "命主": chart.subject,
        "盤面摘要": chart.summary,
        "排盤步驟": chart.reasoning_chain,
        "命盤要素": chart.readings,
    }
    user = (
        f"命盤事實（JSON）：\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\n"
        + (f"命主想問：{focus}\n\n" if focus else "")
        + "請依上述事實解讀。"
    )
    text = complete(_SYSTEM + _voice(chart.system), user)
    return Reading(**chart.model_dump(), interpretation=text)
