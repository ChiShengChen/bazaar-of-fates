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


def test_astrology_planet_returns_timeline():
    from fortune import timeline as tl
    t = tl.timeline("astrology", BIRTH)
    assert t.kind == "planet_returns" and t.periods
    labels = [p.label for p in t.periods]
    assert any("Saturn return" in s for s in labels) and any("Jupiter return" in s for s in labels)
    # Saturn return #1 lands near age 29.5
    sr1 = next(p for p in t.periods if p.label == "Saturn return #1")
    assert 28 < sr1.start_age < 31


def test_annual_report_assembles_all_systems():
    from fortune import annual
    r = annual.compute(BIRTH, 2026)
    s = r["sections"]
    assert s["solar_return"]["ascendant"] and s["solar_return"]["highlights"]
    assert s["bazi"]["liunian_element"] and s["bazi"]["verdict"]
    assert len(s["ziwei"]["sihua"]) == 4
    assert s["jyotish"]["mahadasha_lord"]
    assert "2026" in r["summary"]
    # the report carries the SR chart payload for the wheel
    ch = s["solar_return"]["chart"]
    assert len(ch["natal"]) == 7 and len(ch["sr_planets"]) == 7 and len(ch["sr_houses"]) == 12


def test_annual_overview_arc():
    from fortune import annual
    ov = annual.overview(BIRTH, 2024, 5)
    assert len(ov["years"]) == 5
    assert [y["year"] for y in ov["years"]] == [2024, 2025, 2026, 2027, 2028]
    assert all(y["sr_ascendant"] and y["bazi_element"] and y["jyotish_lord"] for y in ov["years"])
    # light mode omits the heavy chart payload
    assert "chart" not in annual.compute(BIRTH, 2026, light=True)["sections"]["solar_return"]


def test_solar_return_year_timeline():
    c = casting.cast("astrology", BIRTH, solar_return=True, transit_date="2020-03-01")
    tln = c.chart["solar_return_timeline"]
    assert tln and all(set(("label", "start", "nature")) <= set(p) for p in tln)
    assert all(p["start"][:4] in ("2020", "2021") for p in tln)   # within the SR year


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


def test_major_transits_field_present():
    c = casting.cast("astrology", BIRTH, transits=True)
    assert "major_transits" in c.chart and isinstance(c.chart["major_transits"], list)
    assert "major_transits" in c.readings


def test_major_transit_fires_when_saturn_hits_an_angle():
    # 2005-07: transit Saturn (~Leo 0°) conjoins this chart's MC at ~120°
    c = casting.cast("astrology", BIRTH, transits=True, transit_date="2005-07-01")
    hits = c.chart["major_transits"]
    assert any(h["transit"] == "Saturn" and h["angle"] == "MC" for h in hits)


def test_major_transit_weight_grades_by_aspect():
    c = casting.cast("astrology", BIRTH, transits=True, transit_date="2005-07-01")
    conj = next(h for h in c.chart["major_transits"] if h["type"] == "conjunction")
    sq = next((h for h in c.chart["major_transits"] if h["type"] == "square"), None)
    assert 0 < (sq["weight"] if sq else 0) < conj["weight"]   # conjunction outweighs square


def test_davison_timeline_returns():
    from fortune import synastry
    tl = synastry.compute(BIRTH, _partner()).davison["timeline"]
    labels = [p["label"] for p in tl["periods"]]
    assert any("Saturn return" in s for s in labels) and any("Jupiter return" in s for s in labels)


def _trio():
    c = BirthInput(name="L", gender="female", birth_date=date(1992, 3, 8), birth_time=time(20, 40),
                   latitude=22.3, longitude=114.2)
    return [BIRTH, _partner(), c]


def test_group_matrix_is_symmetric_and_scored():
    from fortune import group
    g = group.compute(_trio())
    m = g["matrix"]
    assert len(m) == 3 and all(m[i][i] == 0 for i in range(3))
    assert all(m[i][j] == m[j][i] for i in range(3) for j in range(3))   # symmetric
    assert len(g["pairs"]) == 3 and g["best_pair"] and g["tense_pair"]


def test_group_composite_is_circular_mean():
    import math
    from fortune import group
    members = _trio()
    g = group.compute(members)
    comp = g["composite"]
    assert comp and len(comp["planets"]) == 7 and "ascendant" in comp
    suns = [next(p["ecliptic_lon"] for p in casting.cast("astrology", b).chart["planets"] if p["body"] == "Sun") for b in members]
    s = sum(math.sin(math.radians(x)) for x in suns); c = sum(math.cos(math.radians(x)) for x in suns)
    expect = math.degrees(math.atan2(s, c)) % 360
    csun = next(p["ecliptic_lon"] for p in comp["planets"] if p["body"] == "Sun")
    assert abs((csun - expect + 180) % 360 - 180) < 0.1


def test_transit_phase_applying_or_separating():
    c = casting.cast("astrology", BIRTH, transits=True, transit_date="2005-07-01")
    hits = c.chart["major_transits"]
    assert hits and all(h["phase"] in ("applying", "separating") for h in hits)


def test_exact_trigger_date_lands_on_the_angle():
    from fortune.engines.astrology import astro
    import ephem
    c = casting.cast("astrology", BIRTH, transits=True, transit_date="2005-07-01")
    m = next(h for h in c.chart["major_transits"] if h["type"] == "conjunction" and h["angle"] == "MC")
    y, mo, d = map(int, m["exact_date"].split("-"))
    sat = astro._lon(ephem.Saturn, date(y, mo, d))
    assert abs((sat - m["angle_lon"] + 180) % 360 - 180) < 0.3   # Saturn really is on the MC then


def test_secondary_progressions_overlay():
    c = casting.cast("astrology", BIRTH, progress=True, transit_date="2030-06-15")  # ~age 40
    assert c.chart["progressions"] and len(c.chart["progressions"]) == 7
    assert "progression_aspects" in c.chart
    assert c.readings["progressed_age"] == 40.0
    # progressed Sun advances ~1°/year from natal Sun
    nat = next(p["ecliptic_lon"] for p in c.chart["planets"] if p["body"] == "Sun")
    prog = next(p["ecliptic_lon"] for p in c.chart["progressions"] if p["body"] == "Sun")
    adv = (prog - nat) % 360
    assert 35 < adv < 45   # ~40° for ~40 years
    assert c.chart["progression_houses"] and len(c.chart["progression_houses"]) == 12


def test_solar_arc_is_a_rigid_rotation():
    c = casting.cast("astrology", BIRTH, progress=True, transit_date="2025-06-15", progress_method="solar_arc")
    arc = c.readings["solar_arc_deg"]
    assert 33 < arc < 36   # ~age 35 → ~34° arc
    natal = {p["body"]: p["ecliptic_lon"] for p in c.chart["planets"]}
    for p in c.chart["progressions"]:               # every planet advanced by the same arc
        assert abs((p["ecliptic_lon"] - natal[p["body"]] - arc + 180) % 360 - 180) < 0.05


def test_major_progressions_flagged():
    c = casting.cast("astrology", BIRTH, progress=True, transit_date="2025-06-15")
    mp = c.chart["major_progressions"]
    events = " ".join(m["event"] for m in mp)
    assert "progressed Moon in sign" in events
    assert any("changed sign" in m["event"] for m in mp)   # prog Sun Gemini → Cancer by age 35


def test_cross_aspects_carry_phase_and_exact():
    for kwargs in ({"transits": True, "transit_date": "2024-06-01"},
                   {"progress": True, "transit_date": "2025-06-15"}):
        c = casting.cast("astrology", BIRTH, **kwargs)
        asp = c.chart.get("transit_aspects") or c.chart.get("progression_aspects")
        assert asp and all(a["phase"] in ("applying", "separating") for a in asp)
        assert all(("exact_date" in a) for a in asp)


def test_aspects_ranked_by_importance():
    c = casting.cast("astrology", BIRTH, transits=True, transit_date="2024-06-01")
    imps = [a["importance"] for a in c.chart["transit_aspects"]]
    assert imps == sorted(imps, reverse=True)            # most important first
    assert all(0 < i <= 1 for i in imps)


def test_solar_return_chart():
    c = casting.cast("astrology", BIRTH, solar_return=True, transit_date="2025-03-01")
    assert c.readings["solar_return_year"] == 2025
    assert len(c.chart["solar_return"]) == 7 and len(c.chart["solar_return_houses"]) == 12
    # at the Solar Return moment, the Sun is back on its natal longitude
    nat = next(p["ecliptic_lon"] for p in c.chart["planets"] if p["body"] == "Sun")
    sr = next(p["ecliptic_lon"] for p in c.chart["solar_return"] if p["body"] == "Sun")
    assert abs((sr - nat + 180) % 360 - 180) < 0.05
    hl = " ".join(c.readings["solar_return_highlights"])
    assert "SR ascendant" in hl and "SR Sun in house" in hl


def test_lunar_return_chart():
    c = casting.cast("astrology", BIRTH, lunar_return=True, transit_date="2025-03-10")
    assert len(c.chart["lunar_return"]) == 7 and len(c.chart["lunar_return_houses"]) == 12
    # at the Lunar Return moment, the Moon is back on its natal longitude (NOT the opposition)
    nat = next(p["ecliptic_lon"] for p in c.chart["planets"] if p["body"] == "Moon")
    lr = next(p["ecliptic_lon"] for p in c.chart["lunar_return"] if p["body"] == "Moon")
    assert abs((lr - nat + 180) % 360 - 180) < 0.05
    assert any("LR ascendant" in h for h in c.readings["lunar_return_highlights"])


def test_solar_arc_directions_to_angles():
    c = casting.cast("astrology", BIRTH, progress=True, progress_method="solar_arc", transit_date="2025-06-15")
    dirs = c.chart["solar_arc_directions"]
    assert dirs and all(0 <= x["age"] <= 100 and x["angle"] in ("ASC", "MC", "DSC", "IC") for x in dirs)
    assert dirs == sorted(dirs, key=lambda x: x["age"])     # sorted by age
    # arc needed ≈ age (solar arc ~1°/yr)
    assert all(abs(x["arc"] - x["age"]) < 8 for x in dirs)


def test_davison_is_a_real_distinct_chart():
    from fortune import synastry
    s = synastry.compute(BIRTH, _partner())
    assert s.davison and len(s.davison["planets"]) == 7
    assert s.davison["datetime"] and s.davison["ascendant"]
    # Davison ≠ composite: the time-accurate Moon differs from the longitude-midpoint Moon
    dav_moon = next(p["ecliptic_lon"] for p in s.davison["planets"] if p["body"] == "Moon")
    comp_moon = next(p["ecliptic_lon"] for p in s.composite["planets"] if p["body"] == "Moon")
    assert abs((dav_moon - comp_moon + 180) % 360 - 180) > 0.5


def test_davison_none_without_geometry():
    from fortune import synastry
    bare = BirthInput(birth_date=date(1990, 6, 15))
    assert synastry.compute(bare, bare).davison is None


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
