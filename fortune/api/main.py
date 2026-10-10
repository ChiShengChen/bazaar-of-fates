"""Bazaar of Fates — FastAPI 算命 service. One input (birth / 生辰), eleven divination
systems, a deterministic chart (命盤) plus an optional bilingual LLM reading (解讀).

    GET  /systems                  → the 11 systems + which cast cleanly
    POST /cast/{system}            → deterministic chart, no LLM            → Chart
    POST /reading/{system}         → chart + reading (LLM, mock by default) → Reading
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path as _Path
from pydantic import BaseModel

from fortune import annual as annual_mod, casting, geo, group as grp_mod, synastry as syn_mod, timeline as tl
from fortune.birth import BirthInput
from fortune import focus as focus_mod
from fortune import zeri as zeri_mod
from fortune.interpret import (
    interpret, interpret_annual, interpret_composite, interpret_davison, interpret_group,
    interpret_overview, interpret_stream, interpret_synastry, interpret_synthesis,
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
from fortune.shared.throttle import CacheMiddleware, RateLimiter, RateLimitMiddleware, TTLCache  # noqa: E402

app.state.cache = TTLCache(max_entries=settings.cache_max_entries, ttl=settings.cache_ttl_seconds)
app.state.limiter = RateLimiter(per_minute=settings.rate_limit_per_minute, llm_per_minute=settings.llm_rate_limit_per_minute)
if settings.cache_enabled:
    app.add_middleware(CacheMiddleware, cache=app.state.cache)          # inner: serves hits before the handler runs
if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware, limiter=app.state.limiter)  # outer: counts every request, hits included


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
    qimen_method: str = "chaibu"       # 奇門 起局: "chaibu" 拆補法 | "zhirun" 置閏法
    lang: str = "both"                 # reading language: "zh" | "en" | "both"


class SynastryRequest(BaseModel):
    a: BirthInput
    b: BirthInput
    focus: str | None = None
    house_system: str = "whole_sign"
    lang: str = "both"


class GroupRequest(BaseModel):
    births: list[BirthInput]
    focus: str | None = None
    house_system: str = "whole_sign"
    lang: str = "both"


class AnnualRequest(BaseModel):
    birth: BirthInput
    year: int
    focus: str | None = None
    lang: str = "both"


class SynthesisRequest(BaseModel):
    birth: BirthInput
    focus: str | None = None
    systems: list[str] | None = None   # default: all 13
    lang: str = "both"
    house_system: str = "whole_sign"


class ZeriRequest(BaseModel):
    birth: BirthInput
    start: str                          # ISO date
    end: str
    purpose: str = "general"            # wedding | opening | moving | contract | surgery | travel | wealth | general
    top: int = 10
    lang: str = "both"
    interpret: bool = True


class DayRequest(BaseModel):
    birth: BirthInput
    date: str | None = None             # ISO date, default today
    hour: int | None = None             # clock hour for the 奇門/紫微 流時 (default noon)


class OverviewRequest(BaseModel):
    birth: BirthInput
    start_year: int
    count: int = 6
    focus: str | None = None
    lang: str = "both"


class LoveRequest(BaseModel):
    birth: BirthInput
    question: str | None = None         # 何時有緣 / 合不合 / 復合 / 該不該分開 / 婚姻 / 第三者 / 現況
    partner: BirthInput | None = None   # 合婚 when given
    start_year: int | None = None       # first year of the 桃花年 scan (default this year)
    years: int = 8                      # 1–20
    read: bool = True                   # add the 感情命理師 reading
    lang: str = "zh"
    house_system: str = "whole_sign"


@app.get("/health")
def health() -> dict:
    from fortune.shared.llm import llm_stats
    return {"status": "ok", "llm_backend": settings.llm_backend, "systems": len(casting.REGISTRY),
            "cache": {"enabled": settings.cache_enabled, "entries": len(app.state.cache), "hits": app.state.cache.hits, "misses": app.state.cache.misses, "ttl_seconds": settings.cache_ttl_seconds},
            "rate_limit": {"enabled": settings.rate_limit_enabled, "per_minute": app.state.limiter.per_minute, "llm_per_minute": app.state.limiter.llm_per_minute, "rejected": app.state.limiter.rejected},
            "llm": llm_stats()}


@app.get("/systems")
def list_systems() -> list[dict[str, object]]:
    return casting.systems()


@app.get("/geo")
def geo_lookup(q: str, on: str | None = None) -> dict:
    """Birthplace → lat/lon/tz (offline city table; Taiwan historical DST applied when `on` = birth date)."""
    from datetime import datetime, date as _date
    hit = geo.lookup(q, _date.fromisoformat(on) if on else None)
    return hit or {"name": None, "note": "unknown place / 查無此地，請手動填經緯度"}


@app.get("/cities")
def list_cities() -> list[dict]:
    return geo.cities()


@app.post("/cast/{system}", response_model=Chart)
def cast(system: str, birth: BirthInput, house_system: str = "whole_sign",
         transits: bool = False, transit_date: str | None = None,
         progress: bool = False, progress_method: str = "secondary",
         solar_return: bool = False, lunar_return: bool = False, qimen_method: str = "chaibu",
         brightness_school: str = "quanshu", taiyi_method: str = "tongzong", stroke_basis: str = "kangxi", numeral_strokes: str = "value", jiashu: str = "on") -> Chart:
    """`brightness_school` (紫微 亮度流派): quanshu 全書七級 · zhongzhou 中州派四級 · simple 三級. `taiyi_method` (太乙 積年): tongzong · jinjing · taojinge."""
    try:
        return casting.cast(system, birth, house_system=house_system,
                            transits=transits, transit_date=transit_date, progress=progress, progress_method=progress_method, solar_return=solar_return, lunar_return=lunar_return, qimen_method=qimen_method,
                            brightness_school=brightness_school, taiyi_method=taiyi_method, stroke_basis=stroke_basis, numeral_strokes=numeral_strokes, jiashu=jiashu)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:                      # e.g. 姓名學 NameInputError: needs a Chinese full name
        raise HTTPException(422 if getattr(e, "code", "") == "needs_full_name" else 400, str(e)) from e
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
        chart = casting.cast(system, req.birth, house_system=req.house_system, transits=req.transits, transit_date=req.transit_date, progress=req.progress, progress_method=req.progress_method, solar_return=req.solar_return, lunar_return=req.lunar_return, qimen_method=req.qimen_method)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        log.exception("cast_failed", system=system)
        raise HTTPException(500, f"{system} cast failed / 排盤失敗：{e}") from e
    return interpret(chart, focus=req.focus, lang=req.lang)


@app.post("/synthesis")
def synthesis(req: SynthesisRequest) -> dict:
    """綜合 / Cross-tradition synthesis: cast every system, extract the facts that bear on the
    question, give each tradition its own rule-based verdict, tally agreement vs conflict, then one
    reading that weighs them. No LLM is needed for the table; the prose is one call."""
    keys = req.systems or list(casting.REGISTRY)
    charts: dict[str, Chart] = {}
    errors: dict[str, str] = {}
    for k in keys:
        if k not in casting.REGISTRY:
            raise HTTPException(404, f"unknown system: {k}")
        try:
            charts[k] = casting.cast(k, req.birth, house_system=req.house_system, transits=(k == "astrology"))
        except Exception as e:  # noqa: BLE001
            log.exception("synthesis_cast_failed", system=k)
            errors[k] = str(e)
    male = {"male": True, "female": False}.get((req.birth.gender or "").lower())
    syn = focus_mod.synthesize(charts, focus_mod.classify(req.focus), male)
    syn["subject"] = req.birth.label()
    syn["focus"] = req.focus
    syn["errors"] = errors
    syn["interpretation"] = interpret_synthesis(syn, focus=req.focus, lang=req.lang)
    return syn


class ConsultRequest(BaseModel):
    birth: BirthInput
    question: str | None = None
    start_year: int | None = None
    years: int = 8                      # 1–20
    read: bool = True
    lang: str = "zh"
    house_system: str = "whole_sign"


@app.get("/consult")
def consult_topics() -> list[dict]:
    """The 專科 readers: love + career / wealth / health / study / family, with their sub-intents."""
    from fortune import love as love_mod
    from fortune import specialist as sp
    rows = [{"topic": "love", "zh": "感情", "en": "love", "intents": {k: v["zh"] for k, v in love_mod.INTENTS.items()}}]
    rows += [{"topic": t, "zh": s["zh"], "en": s["en"], "intents": {k: v["zh"] for k, v in s["intents"].items()}} for t, s in sp.SPECS.items()]
    return rows


@app.post("/consult/{topic}")
def consult(topic: str, req: ConsultRequest) -> dict:
    """專科 sitting for one topic (career 事業 / wealth 財運 / health 健康 / study 學業 / family 家庭; `love` routes to /love without a partner;
    `auto` picks the 專科 from the question). Natal disposition, this year's 13-system lean, a yearly scan with every +/− listed,
    the topic's own sheet (事業方向 / 財性財庫 / 體質臟腑 / 學習傾向科系 / 六親宮位), and one reading that answers the sub-question first."""
    from fortune import specialist as sp
    if not 1 <= req.years <= 20:
        raise HTTPException(400, "years must be 1–20 / 年數需 1–20")
    if topic == "auto":
        topic = sp.route(req.question)
    try:
        if topic == "love":
            from fortune import love as love_mod
            return love_mod.consult(req.birth, req.question, start_year=req.start_year, years=req.years, read=req.read, lang=req.lang, house_system=req.house_system)
        if topic not in sp.SPECS:
            raise HTTPException(404, f"unknown topic {topic!r}; one of love, {', '.join(sp.TOPICS)}, auto")
        return sp.consult(topic, req.birth, req.question, start_year=req.start_year, years=req.years, read=req.read, lang=req.lang, house_system=req.house_system)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        log.exception("consult_failed")
        raise HTTPException(500, f"consult failed / 專科排盤失敗：{e}") from e


class AskRequest(BaseModel):
    question: str | None = None
    at: datetime | None = None          # moment of the question (local), default now
    tz_offset_hours: float = 8.0
    place: str | None = None
    numbers: list[int] | None = None    # iching 數字起卦 (1–3 numbers)
    text: str | None = None             # iching 字占
    coins: list[int] | None = None      # liuyao 金錢卦 (six of 6/7/8/9, bottom→top)
    qimen_method: str = "chaibu"
    read: bool = True
    lang: str = "zh"


@app.post("/ask/{system}")
def ask(system: str, req: AskRequest) -> dict:
    """問事 — cast 奇門 / 六壬 / 梅花 / 六爻 / 小六壬 for the moment of the question (or from numbers / text / coins),
    with a question-oriented verdict (用神・類神・體用・世應 scored, every term listed, 應期 hint) and the system's reading."""
    from fortune import ask as ask_mod
    if system not in ask_mod.SYSTEMS:
        raise HTTPException(404, f"ask: system must be one of {', '.join(ask_mod.SYSTEMS)}")
    try:
        return ask_mod.ask(system, req.question, at=req.at, tz=req.tz_offset_hours, place=req.place, numbers=req.numbers, text=req.text,
                           coins=req.coins, qimen_method=req.qimen_method, read=req.read, lang=req.lang)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:  # noqa: BLE001
        log.exception("ask_failed")
        raise HTTPException(500, f"ask failed / 問事失敗：{e}") from e


class NameRequest(BaseModel):
    full_name: str                      # 中文全名；複姓或冠夫姓以空白分隔（歐陽 娜娜）
    birth: BirthInput | None = None     # optional: adds the 八字 link (每格五行對喜用)
    stroke_basis: str = "kangxi"        # kangxi | modern
    numeral_strokes: str = "value"      # value | shape
    jiashu: str = "on"                  # on | off
    read: bool = False
    lang: str = "zh"
    focus: str | None = None


@app.post("/name")
def name_numerology(req: NameRequest) -> dict:
    """姓名學 (熊崎式五格): 康熙筆畫 (Unihan 部首原形), 天人地外總, 三才, 81 數理; with `birth` the sheet also maps every 格 to the 八字 喜用."""
    from fortune.casting import xingming as xm
    from fortune.xingming import NameInputError
    try:
        chart = xm.build(req.full_name, req.birth, stroke_basis=req.stroke_basis, numeral_strokes=req.numeral_strokes, jiashu=req.jiashu)
    except NameInputError as e:
        raise HTTPException(422 if e.code == "needs_full_name" else 400, f"{e.code}: {e}") from e
    except Exception as e:  # noqa: BLE001
        log.exception("name_failed")
        raise HTTPException(500, f"name numerology failed / 姓名學排盤失敗：{e}") from e
    out = chart.model_dump(mode="json")
    if req.read:
        out["interpretation"] = interpret(chart, focus=req.focus, lang=req.lang).interpretation
    return out


@app.post("/love")
def love_consult(req: LoveRequest) -> dict:
    """感情專科 / Love-specialist sitting: natal love disposition (八字 配偶星・夫妻宮, 紫微 夫妻宮, 西洋 金星・七宮, Jyotiṣa 七宮),
    this year's lean across all 13 systems, a 桃花年／婚緣年 scan with every +/− listed, 合婚 when a partner is given, and
    one reading that answers the sub-question first. The tables need no LLM."""
    from fortune import love as love_mod
    if not 1 <= req.years <= 20:
        raise HTTPException(400, "years must be 1–20 / 年數需 1–20")
    try:
        return love_mod.consult(req.birth, req.question, partner=req.partner, start_year=req.start_year, years=req.years,
                                read=req.read, lang=req.lang, house_system=req.house_system)
    except Exception as e:  # noqa: BLE001
        log.exception("love_failed")
        raise HTTPException(500, f"love consult failed / 感情排盤失敗：{e}") from e


@app.post("/zeri")
def zeri(req: ZeriRequest) -> dict:
    """擇日: score every day in [start, end] for a purpose (黃曆 + 八字流日 + 紫微流日四化 + 奇門 + 小六壬),
    rank them, add the 吉時 of the best days, and (optionally) one short reading of the picks."""
    from datetime import date as _date
    try:
        s, e = _date.fromisoformat(req.start), _date.fromisoformat(req.end)
    except ValueError as ex:
        raise HTTPException(400, f"bad date: {ex}") from ex
    if e < s or (e - s).days > 120:
        raise HTTPException(400, "range must be 1–121 days / 區間需在 121 天內")
    if req.purpose not in zeri_mod.PURPOSES:
        raise HTTPException(400, f"purpose must be one of {list(zeri_mod.PURPOSES)}")
    try:
        out = zeri_mod.select(req.birth, s, e, req.purpose, top=max(1, min(req.top, 30)))
    except Exception as ex:  # noqa: BLE001
        log.exception("zeri_failed")
        raise HTTPException(500, f"擇日失敗：{ex}") from ex
    if req.interpret:
        from fortune.interpret import interpret_zeri
        out["interpretation"] = interpret_zeri(out, lang=req.lang)
    return out


@app.post("/day")
def day(req: DayRequest) -> dict:
    """今日運勢: one day's score, reasons, 黃曆, 流日, 紫微流日四化, 奇門吉方, 小六壬 and the 12 時辰."""
    from datetime import date as _date
    d = _date.fromisoformat(req.date) if req.date else _date.today()
    try:
        return zeri_mod.day_outlook(req.birth, d, req.hour)
    except Exception as ex:  # noqa: BLE001
        log.exception("day_failed")
        raise HTTPException(500, f"流日失敗：{ex}") from ex


@app.post("/synastry", response_model=Synastry)
def synastry(req: SynastryRequest) -> Synastry:
    """合盤: two natal charts + their cross-aspects + a bilingual relationship reading."""
    try:
        s = syn_mod.compute(req.a, req.b, house_system=req.house_system)
    except Exception as e:  # noqa: BLE001
        log.exception("synastry_failed")
        raise HTTPException(500, f"synastry failed / 合盤失敗：{e}") from e
    s.interpretation = interpret_synastry(s, focus=req.focus, lang=req.lang)
    if s.composite:
        s.composite["interpretation"] = interpret_composite(s.composite, focus=req.focus, lang=req.lang)
    if s.davison:
        s.davison["interpretation"] = interpret_davison(s.davison, focus=req.focus, lang=req.lang)
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
    g["interpretation"] = interpret_group(g, focus=req.focus, lang=req.lang)
    if g.get("composite"):
        g["composite"]["interpretation"] = interpret_composite(g["composite"], focus=req.focus, lang=req.lang)
    return Group(**g)


@app.post("/annual-report")
def annual_report(req: AnnualRequest) -> dict:
    """年度報告: one year across Solar Return + 八字流年/大運 + 紫微四化 + Jyotiṣa daśā + a synthesis."""
    try:
        rep = annual_mod.compute(req.birth, req.year)
    except Exception as e:  # noqa: BLE001
        log.exception("annual_failed")
        raise HTTPException(500, f"annual report failed / 年度報告失敗：{e}") from e
    rep["interpretation"] = interpret_annual(rep, focus=req.focus, lang=req.lang)
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
    ov["interpretation"] = interpret_overview(ov, focus=req.focus, lang=req.lang)
    return ov


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


@app.post("/reading/{system}/stream")
def reading_stream(system: str, req: ReadingRequest) -> StreamingResponse:
    """Server-Sent Events: a `chart` event (the deterministic 命盤) followed by `delta`
    text events (the streamed 解讀), then `done`. Casts once up front."""
    try:
        chart = casting.cast(system, req.birth, house_system=req.house_system, transits=req.transits, transit_date=req.transit_date, progress=req.progress, progress_method=req.progress_method, solar_return=req.solar_return, lunar_return=req.lunar_return, qimen_method=req.qimen_method)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        log.exception("cast_failed", system=system)
        raise HTTPException(500, f"{system} cast failed / 排盤失敗：{e}") from e

    if req.focus:                                            # surface the topic + extracted facts on the chart itself
        topic = focus_mod.classify(req.focus)
        fx = focus_mod.extract(chart, topic, {"male": True, "female": False}.get((req.birth.gender or "").lower()))
        chart.readings["focus_topic"] = focus_mod.topic_label(topic)
        chart.readings["focus_verdict"] = f"{fx['verdict']}（{fx['reason']}）"
        chart.readings["focus_facts"] = json.dumps(fx["facts"], ensure_ascii=False)

    def gen():
        yield _sse("chart", chart.model_dump_json())
        for delta in interpret_stream(chart, focus=req.focus, lang=req.lang):
            yield _sse("delta", json.dumps({"t": delta}, ensure_ascii=False))
        yield _sse("done", "{}")

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# Serve the no-build static page when the web/ folder is present (Docker, `uvicorn` alone). Mounted at
# BAZAAR_STATIC_PATH (default "/"); a host that owns "/" itself (the Gradio Space) sets it to "/web".
import os as _os
_WEB = _Path(__file__).resolve().parent.parent.parent / "web"
if (_WEB / "index.html").exists():
    app.mount(_os.environ.get("BAZAAR_STATIC_PATH", "/"), StaticFiles(directory=str(_WEB), html=True), name="static")
