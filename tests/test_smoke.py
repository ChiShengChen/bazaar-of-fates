"""Smoke: every available system casts a non-empty 命盤 from one 生辰."""

from datetime import date, time

import pytest

from fortune import casting
from fortune.birth import BirthInput
from fortune.interpret import interpret

BIRTH = BirthInput(
    name="測試", birth_date=date(1990, 6, 15), birth_time=time(14, 30),
    gender="女", place="台北", latitude=25.04, longitude=121.56,
)


@pytest.mark.parametrize("key", list(casting.REGISTRY))
def test_each_system_casts(key):
    avail = {s["key"]: s["available"] for s in casting.systems()}
    if not avail[key]:
        pytest.skip(f"{key} adapter not wired yet")
    chart = casting.cast(key, BIRTH)
    assert chart.system == key
    assert chart.system_en          # bilingual: English name populated
    assert chart.system_zh
    assert chart.summary
    assert chart.reasoning_chain


def test_reading_runs_on_mock():
    r = interpret(casting.cast("bazi", BIRTH))
    assert r.interpretation
    assert "八字" in r.system_zh


# --- place/time-aware upgrades -------------------------------------------------

NO_GEOMETRY = BirthInput(birth_date=date(1990, 6, 15))   # no time, no place


@pytest.mark.parametrize("key", ["astrology", "qizheng", "jyotish"])
def test_ascendant_present_with_time_and_place(key):
    c = casting.cast(key, BIRTH)
    assert c.ascendant is not None
    assert c.ascendant["sign"]
    assert len(c.ascendant["houses"]) == 12


@pytest.mark.parametrize("key", ["astrology", "qizheng", "jyotish"])
def test_ascendant_degrades_without_geometry(key):
    c = casting.cast(key, NO_GEOMETRY)      # must not crash
    assert c.ascendant is None
    assert c.summary


def test_ziwei_life_palace_varies_by_hour():
    from datetime import time
    base = dict(birth_date=date(1985, 3, 20))
    palaces = {
        casting.cast("ziwei", BirthInput(birth_time=time(h, 0), **base)).readings["life_palace_branch"]
        for h in (1, 7, 13, 19)
    }
    assert len(palaces) > 1     # 命宮 genuinely depends on 時辰


# --- ① Placidus ----------------------------------------------------------------

def test_placidus_cusp1_is_ascendant_and_cusp10_is_mc():
    from fortune import astro_ext as AX
    cusps = AX.placidus_houses(BIRTH)
    asc, mc = AX.ascendant_lon(BIRTH), AX.mc_lon(BIRTH)
    assert abs((cusps[0]["longitude"] - asc + 180) % 360 - 180) < 0.01    # cusp 1 == Asc
    assert abs((cusps[9]["longitude"] - mc + 180) % 360 - 180) < 0.01     # cusp 10 == MC
    gaps = [(cusps[(i + 1) % 12]["longitude"] - cusps[i]["longitude"]) % 360 for i in range(12)]
    assert all(g > 0 for g in gaps) and abs(sum(gaps) - 360) < 0.01       # monotonic, closes


def test_house_system_toggle_differs():
    ws = casting.cast("astrology", BIRTH, house_system="whole_sign")
    pl = casting.cast("astrology", BIRTH, house_system="placidus")
    assert ws.ascendant["house_system"] == "whole_sign"
    assert pl.ascendant["house_system"] == "placidus"
    assert ws.ascendant["houses"] != pl.ascendant["houses"]


# --- ③ timelines ---------------------------------------------------------------

def test_timelines_build_and_mark_current():
    from fortune import timeline as tl
    for key in ("jyotish", "bazi", "ziwei"):
        t = tl.timeline(key, BIRTH)
        assert t.kind != "none" and t.periods
        assert sum(1 for p in t.periods if p.current) <= 1     # at most one "now"


def test_timeline_none_for_pointwise_systems():
    from fortune import timeline as tl
    assert tl.timeline("qimen", BIRTH).kind == "none"


# --- ② Equal + Koch ------------------------------------------------------------

def test_equal_houses_are_30_apart_from_ascendant():
    from fortune import astro_ext as AX
    asc = AX.ascendant_lon(BIRTH)
    eq = AX.equal_houses(asc)
    assert abs((eq[0]["longitude"] - asc + 180) % 360 - 180) < 0.01
    gaps = [(eq[(i + 1) % 12]["longitude"] - eq[i]["longitude"]) % 360 for i in range(12)]
    assert all(abs(g - 30) < 0.01 for g in gaps)


def test_koch_cusp1_is_ascendant_and_cusp10_is_mc():
    from fortune import astro_ext as AX
    cusps = AX.koch_houses(BIRTH)
    asc, mc = AX.ascendant_lon(BIRTH), AX.mc_lon(BIRTH)
    assert abs((cusps[0]["longitude"] - asc + 180) % 360 - 180) < 0.01
    assert abs((cusps[9]["longitude"] - mc + 180) % 360 - 180) < 0.01
    gaps = [(cusps[(i + 1) % 12]["longitude"] - cusps[i]["longitude"]) % 360 for i in range(12)]
    assert all(g > 0 for g in gaps) and abs(sum(gaps) - 360) < 0.01


@pytest.mark.parametrize("hs", ["whole_sign", "equal", "placidus", "koch", "regiomontanus", "campanus"])
def test_all_house_systems_castable(hs):
    c = casting.cast("astrology", BIRTH, house_system=hs)
    assert c.ascendant["house_system"] == hs


@pytest.mark.parametrize("fn", ["regiomontanus_houses", "campanus_houses"])
def test_quadrant_cusp1_asc_cusp10_mc(fn):
    from fortune import astro_ext as AX
    cusps = getattr(AX, fn)(BIRTH)
    asc, mc = AX.ascendant_lon(BIRTH), AX.mc_lon(BIRTH)
    assert abs((cusps[0]["longitude"] - asc + 180) % 360 - 180) < 0.01
    assert abs((cusps[9]["longitude"] - mc + 180) % 360 - 180) < 0.01
    gaps = [(cusps[(i + 1) % 12]["longitude"] - cusps[i]["longitude"]) % 360 for i in range(12)]
    assert all(g > 0 for g in gaps) and abs(sum(gaps) - 360) < 0.01


def test_chart_ruler_and_angular_in_readings():
    c = casting.cast("astrology", BIRTH)   # has time + place
    assert "chart_ruler" in c.readings and "命主星" in c.readings["chart_ruler"]
    assert "angular_planets" in c.readings
    assert "aspects" in c.readings


def test_all_house_systems_have_cusp_longitudes():
    for hs in ("whole_sign", "equal", "placidus", "koch", "regiomontanus", "campanus"):
        houses = casting.cast("astrology", BIRTH, house_system=hs).ascendant["houses"]
        assert all("longitude" in h for h in houses) and len(houses) == 12


# --- transits + synastry -------------------------------------------------------

def test_transits_overlay_present():
    c = casting.cast("astrology", BIRTH, transits=True)
    assert c.chart["transits"] and len(c.chart["transits"]) == 7
    assert "transit_aspects" in c.chart
    assert "transit_date" in c.readings


def test_transits_off_by_default():
    assert "transits" not in casting.cast("astrology", BIRTH).chart


def _partner():
    from datetime import time
    return BirthInput(name="K", gender="male", birth_date=date(1988, 11, 2), birth_time=time(9, 15),
                      latitude=25.04, longitude=121.56)


def test_synastry_cross_aspects():
    from fortune import synastry
    s = synastry.compute(BIRTH, _partner())
    assert s.a.system == "astrology" and s.b.system == "astrology"
    assert all({"a", "b", "type"} <= set(x) for x in s.cross_aspects)
    assert "✕" in s.summary


def test_aspects_detail_carries_orb():
    detail = casting.cast("astrology", BIRTH).chart["aspects_detail"]
    assert detail and all({"a", "b", "type", "orb"} <= set(x) for x in detail)


def test_transit_date_changes_overlay():
    c1 = casting.cast("astrology", BIRTH, transits=True, transit_date="2020-01-01")
    c2 = casting.cast("astrology", BIRTH, transits=True, transit_date="2024-01-01")
    assert c1.readings["transit_date"] == "2020-01-01"
    s1 = {p["body"]: p["ecliptic_lon"] for p in c1.chart["transits"]}
    s2 = {p["body"]: p["ecliptic_lon"] for p in c2.chart["transits"]}
    assert s1 != s2     # the sky genuinely differs across the chosen dates


def test_composite_midpoints():
    from fortune import synastry
    s = synastry.compute(BIRTH, _partner())
    assert s.composite and len(s.composite["planets"]) == 7
    assert "ascendant" in s.composite       # both have birth time + place
    # composite Sun is the shorter-arc midpoint of the two natal Suns
    a_sun = next(p["ecliptic_lon"] for p in s.a.chart["planets"] if p["body"] == "Sun")
    b_sun = next(p["ecliptic_lon"] for p in s.b.chart["planets"] if p["body"] == "Sun")
    c_sun = next(p["ecliptic_lon"] for p in s.composite["planets"] if p["body"] == "Sun")
    mid = (a_sun + (((b_sun - a_sun + 540) % 360) - 180) / 2) % 360
    assert abs((c_sun - mid + 180) % 360 - 180) < 0.1


# --- ③ streaming ---------------------------------------------------------------

def test_interpret_stream_matches_sync_on_mock():
    from fortune.interpret import interpret, interpret_stream
    chart = casting.cast("bazi", BIRTH)
    streamed = "".join(interpret_stream(chart, focus="career"))
    assert streamed and streamed == interpret(chart, focus="career").interpretation


def test_focus_reaches_the_prompt():
    from fortune.interpret import _prompts
    _sys, user = _prompts(casting.cast("bazi", BIRTH), "marriage 婚姻")
    assert "marriage 婚姻" in user
