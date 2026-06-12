"""Uniform 命盤 result across all 11 systems.

Every engine produces its own native chart shape (planet rows / 四柱 / 卦象 / 九宮…),
kept verbatim in `chart` for that system's renderer. The fields above it are the
common envelope the API and the 解讀 layer rely on.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Chart(BaseModel):
    system: str                              # engine key, e.g. "astrology"
    system_en: str = ""                      # English name, e.g. "Western Astrology"
    system_zh: str                           # 中文名, e.g. "西洋占星"
    subject: str                             # birth label (who · when · where)
    cast_at: datetime

    chart: dict[str, Any] = Field(default_factory=dict)        # system-native chart payload
    reasoning_chain: list[str] = Field(default_factory=list)   # deterministic read, step by step
    readings: dict[str, Any] = Field(default_factory=dict)     # named facts (regime, 喜用神, 卦名…)
    summary: str = ""                                          # one-line deterministic headline
    ascendant: dict[str, Any] | None = None                    # rising sign + houses (None if 時辰/出生地 missing)


class Reading(Chart):
    interpretation: str = ""                 # LLM 解讀 — the product layer on top of the facts
    cost_usd: float = 0.0
