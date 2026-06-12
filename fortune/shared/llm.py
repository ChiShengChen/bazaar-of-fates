"""Minimal LLM gateway for 命盤 interpretation.

One job: turn a deterministic 命盤 (facts the engine computed) into readable prose.
Backend is pluggable; "mock" needs no API key so the whole service runs offline —
every chart still casts deterministically, only the narration is stubbed.
"""

from __future__ import annotations

from fortune.shared.config import get_settings
from fortune.shared.logging import get_logger

log = get_logger("llm")


class LLMError(RuntimeError):
    pass


def complete(system_prompt: str, user_prompt: str, *, max_tokens: int | None = None) -> str:
    """Return the model's text. Falls back to a deterministic stub on the mock backend
    or whenever the real backend is unconfigured/unavailable."""
    s = get_settings()
    max_tokens = max_tokens or s.interpretation_max_tokens

    if s.llm_backend == "anthropic" and s.anthropic_api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=s.anthropic_api_key)
            msg = client.messages.create(
                model=s.anthropic_model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return "".join(b.text for b in msg.content if b.type == "text").strip()
        except Exception as e:  # noqa: BLE001 — degrade to stub, never 500 the reading
            log.warning("llm_fallback_to_stub", error=str(e))

    return _stub(user_prompt)


def _stub(user_prompt: str) -> str:
    """Deterministic placeholder so the product is fully runnable with no key.
    無金鑰時的確定性佔位，讓整個產品仍可運行。"""
    return (
        "[Demo reading · LLM not connected / 示範解讀 · 未接 LLM]\n"
        "Below is the deterministic factual summary of the chart. Set ANTHROPIC_API_KEY "
        "and LLM_BACKEND=anthropic for a real AI reading.\n"
        "以下為命盤的確定性事實摘要（設定金鑰並切換後端即得真正的 AI 解讀）：\n\n"
        + user_prompt.strip()
    )
