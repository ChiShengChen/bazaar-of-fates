"""Bazaar of Fates — FastAPI 算命 service. One input (birth / 生辰), eleven divination
systems, a deterministic chart (命盤) plus an optional bilingual LLM reading (解讀).

    GET  /systems                  → the 11 systems + which cast cleanly
    POST /cast/{system}            → deterministic chart, no LLM            → Chart
    POST /reading/{system}         → chart + reading (LLM, mock by default) → Reading
"""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from fortune import casting, synastry as syn_mod, timeline as tl
from fortune.birth import BirthInput
from fortune.interpret import interpret, interpret_stream, interpret_synastry
from fortune.schemas import Chart, Reading, Synastry, Timeline
from fortune.shared.config import get_settings
from fortune.shared.logging import configure_logging, get_logger

configure_logging()
log = get_logger("api")
settings = get_settings()

app = FastAPI(title="Bazaar of Fates · 算命 Divination Suite", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReadingRequest(BaseModel):
    birth: BirthInput
    focus: str | None = None      # optional topic / 命主想問的方向（career, love, health…）
    house_system: str = "whole_sign"   # whole_sign | equal | placidus | koch | regiomontanus | campanus
    transits: bool = False             # overlay the sky 行運 (astrology only)
    transit_date: str | None = None    # ISO date for the transit overlay (default today)


class SynastryRequest(BaseModel):
    a: BirthInput
    b: BirthInput
    focus: str | None = None
    house_system: str = "whole_sign"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/systems")
def list_systems() -> list[dict[str, object]]:
    return casting.systems()


@app.post("/cast/{system}", response_model=Chart)
def cast(system: str, birth: BirthInput, house_system: str = "whole_sign",
         transits: bool = False, transit_date: str | None = None) -> Chart:
    try:
        return casting.cast(system, birth, house_system=house_system,
                            transits=transits, transit_date=transit_date)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        log.exception("cast_failed", system=system)
        raise HTTPException(500, f"{system} cast failed / 排盤失敗：{e}") from e


@app.post("/timeline/{system}", response_model=Timeline)
def life_timeline(system: str, birth: BirthInput) -> Timeline:
    """大運 / Mahādaśā / 流年 sequence for the system (empty kind='none' if it has none)."""
    try:
        return tl.timeline(system, birth)
    except Exception as e:  # noqa: BLE001
        log.exception("timeline_failed", system=system)
        raise HTTPException(500, f"{system} timeline failed / 時間軸失敗：{e}") from e


@app.post("/reading/{system}", response_model=Reading)
def reading(system: str, req: ReadingRequest) -> Reading:
    try:
        chart = casting.cast(system, req.birth, house_system=req.house_system, transits=req.transits, transit_date=req.transit_date)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        log.exception("cast_failed", system=system)
        raise HTTPException(500, f"{system} cast failed / 排盤失敗：{e}") from e
    return interpret(chart, focus=req.focus)


@app.post("/synastry", response_model=Synastry)
def synastry(req: SynastryRequest) -> Synastry:
    """合盤: two natal charts + their cross-aspects + a bilingual relationship reading."""
    try:
        s = syn_mod.compute(req.a, req.b, house_system=req.house_system)
    except Exception as e:  # noqa: BLE001
        log.exception("synastry_failed")
        raise HTTPException(500, f"synastry failed / 合盤失敗：{e}") from e
    s.interpretation = interpret_synastry(s, focus=req.focus)
    return s


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


@app.post("/reading/{system}/stream")
def reading_stream(system: str, req: ReadingRequest) -> StreamingResponse:
    """Server-Sent Events: a `chart` event (the deterministic 命盤) followed by `delta`
    text events (the streamed 解讀), then `done`. Casts once up front."""
    try:
        chart = casting.cast(system, req.birth, house_system=req.house_system, transits=req.transits, transit_date=req.transit_date)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        log.exception("cast_failed", system=system)
        raise HTTPException(500, f"{system} cast failed / 排盤失敗：{e}") from e

    def gen():
        yield _sse("chart", chart.model_dump_json())
        for delta in interpret_stream(chart, focus=req.focus):
            yield _sse("delta", json.dumps({"t": delta}, ensure_ascii=False))
        yield _sse("done", "{}")

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
