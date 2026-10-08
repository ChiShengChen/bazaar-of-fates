"""`bazaar-mcp` — Bazaar of Fates as a Model Context Protocol server (stdio by default).

Tools: list_systems · cast · reading · synthesis · zeri · day · synastry · love · consult · ask · geo
Every tool is deterministic except `reading` / `synthesis` prose (mock digest unless LLM_BACKEND is set).

Claude Desktop / Claude Code:  {"mcpServers": {"bazaar-of-fates": {"command": "bazaar-mcp"}}}
Cursor / any MCP client:       command `bazaar-mcp` (install: pip install "bazaar-of-fates[mcp]")
HTTP:                          bazaar-mcp --http --port 8020
"""

from __future__ import annotations

import sys
from datetime import date as _date
from typing import Any

from fortune import casting, geo
from fortune.birth import BirthInput

try:                                                   # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:                                    # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server  # type: ignore

INSTRUCTIONS = (
    "Bazaar of Fates casts 13 traditional divination charts (西洋占星, 八字, 紫微斗數, 梅花易數, 六爻, 小六壬, 四柱推命, "
    "七政四餘, 鐵板神數, 奇門遁甲, 大六壬, 太乙神數, Jyotiṣa) from one birth moment with real astronomy. Start with "
    "`cast` for the deterministic chart facts (reasoning_chain + readings are the audit trail), use `synthesis` to put "
    "all systems on one question, `zeri` to pick dates, `day` for today's outlook, and `love` for any romance / marriage "
    "question (natal love disposition, 桃花年／婚緣年 timeline, 合婚 with a partner), and `consult` for the other 專科 — career 事業, "
    "wealth 財運, health 健康, study 學業, family 家庭 (natal disposition, yearly scan, the topic's own sheet). `ask` is 問事: no birth needed — "
    "奇門／六壬／梅花／六爻／小六壬 cast for the moment of the question (or from numbers / a phrase / coin throws). Never present a chart as a basis "
    "for medical, financial or legal decisions."
)
server = _Server(name="bazaar-of-fates", instructions=INSTRUCTIONS)


def _birth(birth_date: str, birth_time: str | None, gender: str | None, place: str | None, latitude: float | None,
           longitude: float | None, tz_offset_hours: float | None, true_solar_time: bool, name: str | None = None) -> BirthInput:
    lat, lon, tz = latitude, longitude, tz_offset_hours
    if place and (lat is None or lon is None):
        hit = geo.lookup(place, _date.fromisoformat(birth_date))
        if hit:
            lat, lon = hit["latitude"], hit["longitude"]
            tz = hit["tz_offset_hours"] if tz is None else tz
    return BirthInput(name=name, birth_date=_date.fromisoformat(birth_date), birth_time=birth_time, gender=gender, place=place,
                      latitude=lat, longitude=lon, tz_offset_hours=8.0 if tz is None else tz, true_solar_time=true_solar_time)


@server.tool()
def list_systems() -> list[dict[str, Any]]:
    """The 13 divination systems: key, English and 中文 names."""
    return casting.systems()


@server.tool()
def geo_lookup(place: str, on: str | None = None) -> dict[str, Any] | None:
    """Birthplace → latitude / longitude / UTC offset (offline city table; Taiwan historical DST applied when `on` = birth date)."""
    return geo.lookup(place, _date.fromisoformat(on) if on else None)


@server.tool()
def cast(system: str, birth_date: str, birth_time: str | None = None, gender: str | None = None, place: str | None = None,
         latitude: float | None = None, longitude: float | None = None, tz_offset_hours: float | None = None,
         true_solar_time: bool = False, house_system: str = "whole_sign", transits: bool = False,
         qimen_method: str = "chaibu", name: str | None = None) -> dict[str, Any]:
    """Cast one system's deterministic chart (no LLM). `system`: bazi | ziwei | astrology | jyotish | iching | liuyao |
    xiaoliuren | suimei | qizheng | tieban | qimen | liuren | taiyi. Dates ISO (YYYY-MM-DD, HH:MM local). Returns summary,
    reasoning_chain (the audit trail), readings (named facts) and the system-native chart payload."""
    b = _birth(birth_date, birth_time, gender, place, latitude, longitude, tz_offset_hours, true_solar_time, name)
    return casting.cast(system, b, house_system=house_system, transits=transits, qimen_method=qimen_method).model_dump(mode="json")


@server.tool()
def reading(system: str, birth_date: str, birth_time: str | None = None, gender: str | None = None, place: str | None = None,
            focus: str | None = None, lang: str = "zh", latitude: float | None = None, longitude: float | None = None,
            tz_offset_hours: float | None = None, true_solar_time: bool = False, house_system: str = "whole_sign") -> dict[str, Any]:
    """Chart + interpretation for one system. `focus` = the question (the prompt then leads with the facts that bear on it and
    the tradition's own rule-based verdict); `lang` zh | en | both. The prose is a deterministic facts digest unless the server
    has LLM_BACKEND=anthropic + ANTHROPIC_API_KEY."""
    from fortune.interpret import interpret
    b = _birth(birth_date, birth_time, gender, place, latitude, longitude, tz_offset_hours, true_solar_time)
    chart = casting.cast(system, b, house_system=house_system, transits=(system == "astrology"))
    return interpret(chart, focus=focus, lang=lang).model_dump(mode="json")


@server.tool()
def synthesis(birth_date: str, question: str | None = None, birth_time: str | None = None, gender: str | None = None,
              place: str | None = None, systems: list[str] | None = None, lang: str = "zh", latitude: float | None = None,
              longitude: float | None = None, tz_offset_hours: float | None = None, with_reading: bool = False) -> dict[str, Any]:
    """All (or chosen) systems on ONE question: per-system rule-based verdict (favourable / neutral / unfavourable) with reason
    and the facts behind it, tally, consensus and conflicts. `with_reading` adds one panel reading."""
    from fortune import focus as F
    b = _birth(birth_date, birth_time, gender, place, latitude, longitude, tz_offset_hours, False)
    keys = systems or list(casting.REGISTRY)
    charts = {k: casting.cast(k, b, transits=(k == "astrology")) for k in keys}
    male = {"male": True, "female": False}.get((gender or "").lower())
    syn = F.synthesize(charts, F.classify(question), male)
    syn["focus"] = question
    if with_reading:
        from fortune.interpret import interpret_synthesis
        syn["interpretation"] = interpret_synthesis(syn, focus=question, lang=lang)
    return syn


@server.tool()
def zeri(birth_date: str, start: str, end: str, purpose: str = "general", birth_time: str | None = None, gender: str | None = None,
         place: str | None = None, top: int = 5, latitude: float | None = None, longitude: float | None = None,
         tz_offset_hours: float | None = None) -> dict[str, Any]:
    """擇日 — score every day in [start, end] (≤ 121 days) for a purpose: wedding | opening | moving | contract | surgery |
    travel | wealth | general. Returns ranked days with +/− reasons (黃曆, 八字 流日, 紫微 流日四化, 奇門, 小六壬), the best 時辰
    and 吉方 of the top days, and the days to avoid."""
    from fortune import zeri as Z
    b = _birth(birth_date, birth_time, gender, place, latitude, longitude, tz_offset_hours, False)
    s, e = _date.fromisoformat(start), _date.fromisoformat(end)
    if e < s or (e - s).days > 120:
        raise ValueError("range must be 1–121 days")
    out = Z.select(b, s, e, purpose, top=max(1, min(top, 30)))
    best = {d["date"] for d in out["days"] if d["date"] in out["best"]}
    out["days"] = [d for d in out["days"] if d["date"] in best or d["grade"] == 1]   # keep the payload small
    return out


@server.tool()
def day(birth_date: str, on: str | None = None, birth_time: str | None = None, gender: str | None = None, place: str | None = None,
        latitude: float | None = None, longitude: float | None = None, tz_offset_hours: float | None = None) -> dict[str, Any]:
    """今日運勢 — one day's score with reasons, 黃曆, 流日, 紫微 流日四化, 奇門 吉方, 小六壬 and the 12 時辰."""
    from fortune import zeri as Z
    b = _birth(birth_date, birth_time, gender, place, latitude, longitude, tz_offset_hours, False)
    return Z.day_outlook(b, _date.fromisoformat(on) if on else _date.today())


@server.tool()
def synastry(a_birth_date: str, b_birth_date: str, a_birth_time: str | None = None, b_birth_time: str | None = None,
             a_place: str | None = None, b_place: str | None = None, a_gender: str | None = None, b_gender: str | None = None,
             house_system: str = "whole_sign") -> dict[str, Any]:
    """合盤 — two Western natal charts, cross-aspects, composite and Davison charts (no LLM)."""
    from fortune import synastry as S
    a = _birth(a_birth_date, a_birth_time, a_gender, a_place, None, None, None, False)
    b = _birth(b_birth_date, b_birth_time, b_gender, b_place, None, None, None, False)
    return S.compute(a, b, house_system=house_system).model_dump(mode="json")


@server.tool()
def love(birth_date: str, question: str | None = None, birth_time: str | None = None, gender: str | None = None, place: str | None = None,
         partner_birth_date: str | None = None, partner_birth_time: str | None = None, partner_gender: str | None = None,
         partner_place: str | None = None, partner_name: str | None = None, start_year: int | None = None, years: int = 8,
         with_reading: bool = False, lang: str = "zh", name: str | None = None) -> dict[str, Any]:
    """感情專科 — the love-specialist sitting. Classifies the question (何時有緣 / 合不合 / 復合 / 該不該分開 / 婚姻 / 第三者 / 現況),
    then returns: `natal` (命 — 八字 配偶星・夫妻宮・桃花神煞, 紫微 夫妻宮三方四正・桃花曜, 西洋 金星・火星・七宮, Jyotiṣa 七宮, each
    scored with listed reasons), `this_year` (all 13 systems' rule verdicts on love), `timing` (every year from `start_year`
    scored as 桃花年／婚緣年 from 八字 流年 配偶星・紅鸞天喜・合沖夫妻宮, 紫微 流年四化入夫妻宮, 西洋 木土行運對金星／七宮, Jyotiṣa daśā;
    `best` and `caution` years), and `match` (合婚: 八字 日柱干合支合／沖刑害・生肖・喜用互補・夫妻星 + 西洋 synastry) when a partner
    is given. Present the years as a ranked list with reasons; present 合婚 as the biggest + and − terms. Gender matters
    (男命財星為妻、女命官殺為夫) — pass it when known."""
    from fortune import love as L
    b = _birth(birth_date, birth_time, gender, place, None, None, None, False, name)
    p = _birth(partner_birth_date, partner_birth_time, partner_gender, partner_place, None, None, None, False, partner_name) if partner_birth_date else None
    out = L.consult(b, question, partner=p, start_year=start_year, years=max(1, min(years, 20)), read=with_reading, lang=lang)
    for y in out["timing"]["years"]:                     # keep the payload small: the context dicts are in the reasons already
        y.pop("context", None)
    return out


@server.tool()
def consult(topic: str, birth_date: str, question: str | None = None, birth_time: str | None = None, gender: str | None = None,
            place: str | None = None, start_year: int | None = None, years: int = 8, with_reading: bool = False, lang: str = "zh",
            name: str | None = None) -> dict[str, Any]:
    """專科 — one specialist sitting. `topic` is career 事業 / wealth 財運 / health 健康 / study 學業 / family 家庭 (or `auto` to pick from
    the question; love questions → the `love` tool). Classifies the sub-question (e.g. career: 轉職／升遷／創業／方向／考試；wealth: 投資／收入／
    破財／買房／合夥；health: 某病／慢性／壓力／哪年注意；study: 考試／升學／選系／專注；family: 父母／子女／搬家／手足／和睦), then returns `natal`
    (命 — 八字 本題十神與宮位、紫微 本題宮三方四正、西洋 本題宮位主星、Jyotiṣa bhāva, each scored with listed reasons), `this_year` (all 13 systems),
    `timing` (every year from `start_year` scored with every +/− term; `best` / `caution`; `sign` marks 升遷轉換年／進財年／注意年／考運年／家運年),
    and `extra` (the topic sheet: 事業方向 / 財性與財庫 / 體質與臟腑 / 學習傾向與科系 / 六親宮位). Present years as a ranked list with reasons.
    Health output is never medical advice; wealth output never names assets."""
    from fortune import specialist as SP
    b = _birth(birth_date, birth_time, gender, place, None, None, None, False, name)
    if topic == "auto":
        topic = SP.route(question)
    if topic == "love":
        return love(birth_date, question, birth_time, gender, place, start_year=start_year, years=years, with_reading=with_reading, lang=lang, name=name)
    out = SP.consult(topic, b, question, start_year=start_year, years=max(1, min(years, 20)), read=with_reading, lang=lang)
    for y in out["timing"]["years"]:
        y.pop("context", None)
    return out


@server.tool()
def ask(system: str, question: str | None = None, at: str | None = None, tz_offset_hours: float = 8.0, place: str | None = None,
        numbers: list[int] | None = None, text: str | None = None, coins: list[int] | None = None, with_reading: bool = False, lang: str = "zh") -> dict[str, Any]:
    """問事 — divination on demand, no birth data. `system`: qimen 奇門 (時盤: 日干宮＝求測人, 時干宮＝所問之事, 用神宮 by topic, 門迫／空亡／三奇／八神,
    吉方), liuren 六壬 (時課: 類神入傳, 末傳 vs 日干, 課體, 旬空), iching 梅花 (時間起卦; or `numbers` = 1–3 numbers 數字起卦; or `text` = a phrase 字占),
    liuyao 六爻 (時間起卦; or `coins` = six of 6/7/8/9 bottom→top 金錢卦), xiaoliuren 小六壬. `at` is the ISO moment of asking (default now,
    local to `tz_offset_hours` / `place`). Returns the chart (reasoning_chain is the audit trail) and `verdict` {verdict_zh 吉/平/凶, score,
    reasons, facts, timing_hint 應期, lucky_directions}. The topic (事業/財運/感情/健康/學業/家庭) is classified from the question."""
    from datetime import datetime as _dt
    from fortune import ask as AK
    return AK.ask(system, question, at=_dt.fromisoformat(at) if at else None, tz=tz_offset_hours, place=place, numbers=numbers, text=text,
                  coins=coins, read=with_reading, lang=lang)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--http" in argv:
        port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8020
        try:
            server.settings.port = port                # mcp 1.x
        except Exception:  # noqa: BLE001
            pass
        server.run("streamable-http")
    else:
        server.run("stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
