"""算命 service — FastAPI. One input (生辰), eleven 命理 systems, deterministic 命盤
plus optional LLM 解讀.

    GET  /systems                  → the 11 systems + which cast cleanly
    POST /cast/{system}            → deterministic 命盤 (no LLM)        → Chart
    POST /reading/{system}         → 命盤 + 解讀 (LLM, mock by default) → Reading
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fortune import casting
from fortune.birth import BirthInput
from fortune.interpret import interpret
from fortune.schemas import Chart, Reading
from fortune.shared.config import get_settings
from fortune.shared.logging import configure_logging, get_logger

configure_logging()
log = get_logger("api")
settings = get_settings()

app = FastAPI(title="算命 · Divination Suite", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReadingRequest(BaseModel):
    birth: BirthInput
    focus: str | None = None      # 命主想問的方向（事業/感情/健康…），可選


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/systems")
def list_systems() -> list[dict[str, object]]:
    return casting.systems()


@app.post("/cast/{system}", response_model=Chart)
def cast(system: str, birth: BirthInput) -> Chart:
    try:
        return casting.cast(system, birth)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        log.exception("cast_failed", system=system)
        raise HTTPException(500, f"{system} 排盤失敗：{e}") from e


@app.post("/reading/{system}", response_model=Reading)
def reading(system: str, req: ReadingRequest) -> Reading:
    try:
        chart = casting.cast(system, req.birth)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        log.exception("cast_failed", system=system)
        raise HTTPException(500, f"{system} 排盤失敗：{e}") from e
    return interpret(chart, focus=req.focus)
