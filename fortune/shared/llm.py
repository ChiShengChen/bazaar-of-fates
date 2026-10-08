"""Minimal LLM gateway for 命盤 interpretation.

One job: turn a deterministic 命盤 (facts the engine computed) into readable prose.
Backend is pluggable; "mock" needs no API key so the whole service runs offline —
every chart still casts deterministically, only the narration is stubbed.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Iterator

from fortune.shared.config import get_settings
from fortune.shared.logging import get_logger

log = get_logger("llm")


class LLMError(RuntimeError):
    pass


_sem: threading.BoundedSemaphore | None = None
_sem_n = 0
_stats = {"in_flight": 0, "queued": 0, "completed": 0, "max_concurrency": 0}
_stats_lock = threading.Lock()


def _gate() -> threading.BoundedSemaphore:
    """Server-wide cap on concurrent LLM calls (LLM_MAX_CONCURRENCY); extra callers queue instead of fanning out."""
    global _sem, _sem_n
    n = max(1, get_settings().llm_max_concurrency)
    if _sem is None or n != _sem_n:
        _sem, _sem_n = threading.BoundedSemaphore(n), n
        _stats["max_concurrency"] = n
    return _sem


class _Slot:
    def __enter__(self):
        with _stats_lock:
            _stats["queued"] += 1
        _gate().acquire()
        with _stats_lock:
            _stats["queued"] -= 1
            _stats["in_flight"] += 1
        return self

    def __exit__(self, *exc):
        _gate().release()
        with _stats_lock:
            _stats["in_flight"] -= 1
            _stats["completed"] += 1


def llm_stats() -> dict:
    with _stats_lock:
        return dict(_stats)


def complete(system_prompt: str, user_prompt: str, *, max_tokens: int | None = None) -> str:
    """Return the model's text. Falls back to a deterministic stub on the mock backend
    or whenever the real backend is unconfigured/unavailable."""
    s = get_settings()
    max_tokens = max_tokens or s.interpretation_max_tokens

    if s.llm_backend == "anthropic" and s.anthropic_api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=s.anthropic_api_key)
            with _Slot():
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


def stream(system_prompt: str, user_prompt: str, *, max_tokens: int | None = None) -> Iterator[str]:
    """Yield the reading incrementally. Real token stream on Anthropic; on the mock
    backend (or any failure) the deterministic stub is chunked so the UI still streams."""
    s = get_settings()
    max_tokens = max_tokens or s.interpretation_max_tokens

    if s.llm_backend == "anthropic" and s.anthropic_api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=s.anthropic_api_key)
            with _Slot(), client.messages.stream(
                model=s.anthropic_model, max_tokens=max_tokens,
                system=system_prompt, messages=[{"role": "user", "content": user_prompt}],
            ) as st:
                for text in st.text_stream:
                    yield text
            return
        except Exception as e:  # noqa: BLE001
            log.warning("llm_stream_fallback_to_stub", error=str(e))

    for chunk in re.findall(r".{1,36}", _stub(user_prompt), flags=re.S):
        yield chunk


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
