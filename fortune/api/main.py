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

from fortune import annual as annual_mod, casting, group as grp_mod, synastry as syn_mod, timeline as tl
from fortune.birth import BirthInput
from fortune.interpret import (
    interpret, interpret_annual, interpret_composite, interpret_davison, interpret_group,
    interpret_overview, interpret_stream, interpret_synastry,
)
from fortune.schemas import Chart, Group, Reading, Synastry, Timeline
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
    transit_date: str | None = None    # ISO date for the transit/progression overlay (default today)
    progress: bool = False             # overlay the progressed chart 二次推運 / 太陽弧
    progress_method: str = "secondary"  # "secondary" | "solar_arc"
    solar_return: bool = False         # overlay the Solar Return chart 太陽回歸
    lunar_return: bool = False         # overlay the Lunar Return chart 月亮回歸


class SynastryRequest(BaseModel):
    a: BirthInput
    b: BirthInput
    focus: str | None = None
    house_system: str = "whole_sign"


class GroupRequest(BaseModel):
    births: list[BirthInput]
    focus: str | None = None
    house_system: str = "whole_sign"


class AnnualRequest(BaseModel):
    birth: BirthInput
    year: int
    focus: str | None = None


class OverviewRequest(BaseModel):
    birth: BirthInput
    start_year: int
    count: int = 6
    focus: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/systems")
def list_systems() -> list[dict[str, object]]:
    return casting.systems()


@app.post("/cast/{system}", response_model=Chart)
def cast(system: str, birth: BirthInput, house_system: str = "whole_sign",
         transits: bool = False, transit_date: str | None = None,
         progress: bool = False, progress_method: str = "secondary",
         solar_return: bool = False, lunar_return: bool = False) -> Chart:
    try:
        return casting.cast(system, birth, house_system=house_system,
                            transits=transits, transit_date=transit_date, progress=progress, progress_method=progress_method, solar_return=solar_return, lunar_return=lunar_return)
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
        chart = casting.cast(system, req.birth, house_system=req.house_system, transits=req.transits, transit_date=req.transit_date, progress=req.progress, progress_method=req.progress_method, solar_return=req.solar_return, lunar_return=req.lunar_return)
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
    if s.composite:
        s.composite["interpretation"] = interpret_composite(s.composite, focus=req.focus)
    if s.davison:
        s.davison["interpretation"] = interpret_davison(s.davison, focus=req.focus)
    return s


@app.post("/group", response_model=Group)
def group(req: GroupRequest) -> Group:
    """團體合盤: pairwise cross-aspect matrix + standout pairs + a group-dynamics reading."""
    if len(req.births) < 2:
        raise HTTPException(400, "need at least 2 people / 至少兩人")
    if len(req.births) > 8:
        raise HTTPException(400, "max 8 people / 最多八人")
    try:
        g = grp_mod.compute(req.births, house_system=req.house_system)
    except Exception as e:  # noqa: BLE001
        log.exception("group_failed")
        raise HTTPException(500, f"group failed / 團體合盤失敗：{e}") from e
    g["interpretation"] = interpret_group(g, focus=req.focus)
    if g.get("composite"):
        g["composite"]["interpretation"] = interpret_composite(g["composite"], focus=req.focus)
    return Group(**g)


@app.post("/annual-report")
def annual_report(req: AnnualRequest) -> dict:
    """年度報告: one year across Solar Return + 八字流年/大運 + 紫微四化 + Jyotiṣa daśā + a synthesis."""
    try:
        rep = annual_mod.compute(req.birth, req.year)
    except Exception as e:  # noqa: BLE001
        log.exception("annual_failed")
        raise HTTPException(500, f"annual report failed / 年度報告失敗：{e}") from e
    rep["interpretation"] = interpret_annual(rep, focus=req.focus)
    return rep


@app.post("/annual-overview")
def annual_overview(req: OverviewRequest) -> dict:
    """多年運勢概覽: a compact per-year arc across several years + a synthesis."""
    if not 1 <= req.count <= 20:
        raise HTTPException(400, "count must be 1–20 / 年數需 1–20")
    try:
        ov = annual_mod.overview(req.birth, req.start_year, req.count)
    except Exception as e:  # noqa: BLE001
        log.exception("overview_failed")
        raise HTTPException(500, f"overview failed / 多年概覽失敗：{e}") from e
    ov["interpretation"] = interpret_overview(ov, focus=req.focus)
    return ov


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


@app.post("/reading/{system}/stream")
def reading_stream(system: str, req: ReadingRequest) -> StreamingResponse:
    """Server-Sent Events: a `chart` event (the deterministic 命盤) followed by `delta`
    text events (the streamed 解讀), then `done`. Casts once up front."""
    try:
        chart = casting.cast(system, req.birth, house_system=req.house_system, transits=req.transits, transit_date=req.transit_date, progress=req.progress, progress_method=req.progress_method, solar_return=req.solar_return, lunar_return=req.lunar_return)
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
