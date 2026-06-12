"""Bazaar of Fates — FastAPI 算命 service. One input (birth / 生辰), eleven divination
systems, a deterministic chart (命盤) plus an optional bilingual LLM reading (解讀).

    GET  /systems                  → the 11 systems + which cast cleanly
    POST /cast/{system}            → deterministic chart, no LLM            → Chart
    POST /reading/{system}         → chart + reading (LLM, mock by default) → Reading
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fortune import casting, timeline as tl
from fortune.birth import BirthInput
from fortune.interpret import interpret
from fortune.schemas import Chart, Reading, Timeline
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
    house_system: str = "whole_sign"   # "whole_sign" | "placidus" (astrology only)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/systems")
def list_systems() -> list[dict[str, object]]:
    return casting.systems()


@app.post("/cast/{system}", response_model=Chart)
def cast(system: str, birth: BirthInput, house_system: str = "whole_sign") -> Chart:
    try:
        return casting.cast(system, birth, house_system=house_system)
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
        chart = casting.cast(system, req.birth, house_system=req.house_system)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        log.exception("cast_failed", system=system)
        raise HTTPException(500, f"{system} cast failed / 排盤失敗：{e}") from e
    return interpret(chart, focus=req.focus)
