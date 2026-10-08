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
    assert all(-2 <= y["score"] <= 2 and "turning" in y for y in ov["years"])
    # light mode omits the heavy chart payload
    assert "chart" not in annual.compute(BIRTH, 2026, light=True)["sections"]["solar_return"]


def test_overview_turning_points_detected():
    from fortune import annual
    ov = annual.overview(BIRTH, 2018, 12)   # spans a 八字 flip, a 大運 change, and a Saturn return
    assert ov["turning_points"]
    events = " ".join(e for t in ov["turning_points"] for e in t["events"])
    assert "大運" in events or "八字" in events or "daśā" in events
    assert "Saturn return" in events        # the ~age-29.5 milestone is flagged
    # the year of a turning point carries its events on the row too
    tp = ov["turning_points"][0]
    row = next(y for y in ov["years"] if y["year"] == tp["year"])
    assert row["turning"] == tp["events"]


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


# --- 八字 full 排盤 (fortune/bazi_ext) — checked against a 周易大學堂-style sheet -----------

def test_bazi_ext_matches_reference_sheet():
    """Reference sheet: 丙午 丁酉 乙卯 甲申, male — 十神/藏干/納音/空亡/胎元/命宮/稱骨/relations."""
    from fortune import bazi_ext as X
    S, B = X.STEMS, X.BRANCHES
    dm = S.index("乙")
    assert [X.ten_god(dm, S.index(c)) for c in "丙丁甲"] == ["傷官", "食神", "劫財"]
    assert [h["god"] for h in X.hidden_gods(dm, B.index("申"))] == ["正官", "正印", "正財"]
    assert [X.nayin(S.index(g[0]), B.index(g[1])) for g in ("丙午", "丁酉", "乙卯", "甲申")] == ["天河水", "山下火", "大溪水", "泉中水"]
    assert [X.kong_wang(S.index(g[0]), B.index(g[1])) for g in ("丙午", "丁酉", "乙卯", "甲申")] == ["寅卯", "辰巳", "子丑", "午未"]
    assert X.tai_yuan(S.index("丁"), B.index("酉")) == "戊子"
    assert X.ming_gong(S.index("丁"), B.index("酉"), B.index("申")) == "庚子"
    assert [X.changsheng(dm, B.index(b)) for b in "戌亥子丑寅卯辰巳午"] == ["墓", "死", "病", "衰", "帝旺", "臨官", "冠帶", "沐浴", "長生"]
    cg = X.cheng_gu({"year": 2026, "month": 8, "day": 28}, B.index("申"))
    assert cg["label"] == "四兩四錢" and cg["verdict"].startswith("來事由天莫苦求")
    assert X.branch_relations([B.index(b) for b in "午酉卯申"]) == ["卯午相破", "卯酉相沖", "卯申暗合金"]
    assert X.stem_relations([S.index(s) for s in "丙丁乙甲"]) == []
    plus = X.branch_relations([B.index(b) for b in "午酉卯申戌午"])     # + 大運 戌 + 流年 午
    assert {"卯戌合化火", "申酉戌會西方金", "午午自刑"} <= set(plus)
    ss = X.shensha_for(None, B.index("午"), ys=S.index("丙"), ds=dm, yb=B.index("午"), db=B.index("卯"), mb=B.index("酉"))
    assert {"將星", "文昌貴人", "天廚貴人", "太極貴人"} <= set(ss)


def test_bazi_ext_exact_solar_terms_and_qiyun():
    """寒露 2026 = 10-08 14:29 (UTC+8, 台北市政府曆象表); birth 11 min before it → 起運 22 h."""
    from fortune import bazi_ext as X
    terms = {name: at for at, name, _ in X.jie_terms(2026, 8)}
    assert terms["寒露"].strftime("%m-%d %H:%M") == "10-08 14:29"
    assert terms["立春"].strftime("%m-%d %H:%M") in ("02-04 04:01", "02-04 04:02")
    b = BirthInput(birth_date=date(2026, 10, 8), birth_time=time(14, 18), gender="male", tz_offset_hours=8)
    c = X.full_chart(b, today=date(2026, 10, 8))
    assert [p["gz"] for p in c["pillars"]] == ["丙午", "丁酉", "乙卯", "癸未"]
    qy = c["qi_yun"]
    assert qy["forward"] and (qy["years"], qy["months"], qy["days"], qy["hours"]) == (0, 0, 0, 22)
    assert qy["jiao_yun"] == "2026-10-09T12:18" and qy["huan_yun_digit"] == 6
    assert [d["gz"] for d in c["dayun"]][:3] == ["戊戌", "己亥", "庚子"]
    assert c["dayun"][0]["start_year"] == 2026 and c["dayun"][0]["changsheng"] == "墓" and "華蓋" in c["dayun"][0]["shensha"]
    ln = c["dayun"][0]["liunian"]
    assert [l["gz"] for l in ln] == ["丙午", "丁未", "戊申", "己酉", "庚戌", "辛亥", "壬子", "癸丑", "甲寅", "乙卯"]
    assert [m["gz"] for m in ln[0]["liuyue"]][:3] == ["庚寅", "辛卯", "壬辰"]
    assert c["lunar"]["text"] == "2026年（馬）八月廿八未時" and c["ming_gong"] == "辛丑"
    # 11 minutes later the 節 has passed: month pillar rolls to 戊戌, 起運 ≈ 10 yr (next 節 = 立冬)
    c2 = X.full_chart(BirthInput(birth_date=date(2026, 10, 8), birth_time=time(15, 57), gender="male"), today=date(2026, 10, 8))
    assert c2["pillars"][1]["gz"] == "戊戌" and c2["qi_yun"]["years"] == 10


def test_bazi_cast_carries_full_sheet_and_timeline_agrees():
    chart = casting.cast("bazi", BIRTH)
    c = chart.chart
    assert len(c["dayun"]) == 9 and all(len(d["liunian"]) == 10 for d in c["dayun"])
    assert all(len(l["liuyue"]) == 12 for d in c["dayun"] for l in d["liunian"])
    assert c["pillars"][2]["stem_god"] in ("元男", "元女")
    for k in ("ten_gods", "hidden_stems", "nayin", "kong_wang", "shensha", "tai_yuan", "ming_gong", "qi_yun", "cheng_gu", "relations"):
        assert chart.readings[k]
    assert any(s.startswith("稱骨") for s in chart.reasoning_chain)
    from fortune import timeline as tl
    t = tl.timeline("bazi", BIRTH)
    assert [p.label for p in t.periods] == [d["gz"] for d in c["dayun"]]
    assert t.periods[0].start_age == c["dayun"][0]["start_age"]


# --- algorithm-correctness fixes (time-aware/of-date positions, 月將, hour pillars, 起卦…) -------

def test_natal_planets_use_birth_instant_and_equinox_of_date():
    """Mei 1990-06-15 14:30 Taipei: Moon 342.3° (midnight-UT J2000 gave 338.9°); the frame must
    match the ascendant's. Sun 83.9° of date (J2000 would be 83.79°)."""
    import math, ephem
    from fortune import astro_ext as AX
    c = casting.cast("astrology", BIRTH)
    by = {p["body"]: p["ecliptic_lon"] for p in c.chart["planets"]}
    assert abs(by["Moon"] - 342.31) < 0.05 and abs(by["Sun"] - 83.91) < 0.05
    ut = AX.birth_utc(BIRTH)
    s = ephem.Sun(ephem.Date(ut)); eq = ephem.Equatorial(s.ra, s.dec, epoch=ephem.Date(ut))
    assert abs(by["Sun"] - math.degrees(ephem.Ecliptic(eq).lon) % 360) < 0.01
    # a late-evening birth moves the Moon by hours' worth of motion, not zero
    late = casting.cast("astrology", BirthInput(birth_date=date(1990, 6, 15), birth_time=time(23, 30), tz_offset_hours=8))
    assert abs({p["body"]: p["ecliptic_lon"] for p in late.chart["planets"]}["Moon"] - by["Moon"]) > 4.0
    # transits / returns / Davison share the frame: the Solar Return Sun equals the natal Sun
    sr = casting.cast("astrology", BIRTH, solar_return=True, transit_date="2026-06-15")
    assert abs({p["body"]: p["ecliptic_lon"] for p in sr.chart["solar_return"]}["Sun"] - by["Sun"]) < 0.02


def test_jyotish_nakshatra_from_birth_instant():
    from fortune import astro_ext as AX, jyotish_ext as JX
    c = casting.cast("jyotish", BIRTH)
    moon = next(g for g in c.chart["grahas"] if g["graha"] == "Moon")
    assert c.readings["moon_nakshatra"] == "Shatabhisha" and moon["rashi"] == "Kumbha"
    n, frac = JX.natal_nakshatra(AX.birth_utc(BIRTH))
    assert 0.85 < frac < 0.93                      # date-only engine said 0.63
    from fortune import timeline as tl
    t = tl.timeline("jyotish", BIRTH)
    assert t.periods[0].label == "Rahu" and 1.5 < float(t.periods[0].detail.split()[0]) < 2.2


def test_liuren_yuejiang_and_courses():
    """Sun in Gemini (June) → 申將 (傳送); 日干 辛 寄戌; 四課 and 賊克 三傳 for Mei."""
    c = casting.cast("liuren", BIRTH)
    assert c.chart["yue_jiang"] == "申" and c.chart["occupy"] == "未"
    assert [k["upper"] for k in c.chart["courses"]] == ["亥", "子", "子", "丑"]
    assert c.chart["transmissions"] == ["丑", "寅", "卯"] and "上克下" in c.readings["course_type"]
    march = casting.cast("liuren", BirthInput(birth_date=date(2026, 4, 1), birth_time=time(9, 0)))
    assert march.chart["yue_jiang"] == "戌"       # Sun in Aries → 戌將（河魁）


def test_suimei_tieban_use_real_hour_and_exact_terms():
    s = casting.cast("suimei", BIRTH)
    assert [p["gz"] for p in s.chart["pillars"]] == ["庚午", "壬午", "辛亥", "乙未"]   # 時柱 乙未, not the engine's 巳時
    assert s.readings["tenchusatsu"] == "寅卯"
    t = casting.cast("tieban", BIRTH)
    assert t.chart["ming_number"] == 17 + 15 + 11 + 16
    # 2026-10-08 15:57 is past 寒露 14:29 → 戌月 for both
    late = BirthInput(birth_date=date(2026, 10, 8), birth_time=time(15, 57))
    assert casting.cast("suimei", late).chart["pillars"][1]["gz"] == "戊戌"


def test_iching_traditional_time_casting():
    """農曆 庚午年五月廿三未時: 年支午=7, 月5, 日23 → 35 → 離; +時8 → 43 → 離, 動爻 43%6=1."""
    c = casting.cast("iching", BIRTH)
    h = c.chart["hexagram"]
    assert (h["upper"], h["lower"], h["moving"]) == ("離", "離", 1)
    assert h["ben_name"] == "離為火" and h["bian_name"] == "火山旅" and h["hu_name"] == "澤風大過"
    assert h["numbers"]["upper_sum"] == 35 and h["numbers"]["lower_sum"] == 43


def test_ziwei_conventions_and_extra_stars():
    from fortune import ziwei_ext as ZX
    c = casting.cast("ziwei", BIRTH)
    stars = {s.split("(")[0] for p in c.chart["palaces"] for s in p["stars"]}
    assert {"祿存", "擎羊", "陀羅", "天魁", "天鉞", "火星", "鈴星", "地空", "地劫", "天馬", "紅鸞", "天喜"} <= stars
    sp = c.chart["star_palace"]
    pal = {p["name"]: p["branch"] for p in c.chart["palaces"]}
    assert pal[sp["祿存"]] == "申" and pal[sp["擎羊"]] == "酉" and pal[sp["陀羅"]] == "未"   # 庚年 祿存在申
    assert pal[sp["天魁"]] == "丑" and pal[sp["天鉞"]] == "未"                            # 庚 → 魁丑 鉞未
    assert pal[sp["天馬"]] == "申"                                                       # 午年 → 申
    assert c.readings["liunian_stem"] == "丙"                                            # 2026 農曆 丙午
    # 晚子時 → next day's lunar date, 子時; 閏月下半月 → next month
    assert ZX.lunar_for_ziwei(date(1990, 6, 15), 23) == (1990, 5, 24, False)
    assert ZX.lunar_for_ziwei(date(2023, 4, 10), 10) == (2023, 3, 20, True)    # 2023 閏二月二十
    assert ZX.lunar_for_ziwei(date(2023, 3, 25), 10) == (2023, 2, 4, False)    # 閏二月初四 stays 二月


def test_qimen_chaibu_chart():
    from datetime import datetime
    from fortune import qimen_ext as Q
    g = Q.cast_hour(datetime(1990, 6, 15, 14, 30), 8)
    assert (g["term"], g["dun"], g["yuan"], g["ju"]) == ("芒種", "陽遁", "上元", 6)     # 辛亥日 符頭 己酉 → 上元
    earth = {p["palace"]: p["earth_stem"] for p in g["palaces"]}
    assert earth == {6: "戊", 7: "己", 8: "庚", 9: "辛", 1: "壬", 2: "癸", 3: "丁", 4: "丙", 5: "乙"}
    assert g["hour_gz"] == "乙未" and g["xun_head"] == "甲午" and g["zhifu"] == "天英" and g["zhishi"] == "景門"
    by = {p["palace"]: p for p in g["palaces"]}
    assert by[2]["star"] == "天英" and by[2]["god"] == "值符" and by[2]["sky_stem"] == "辛"   # 時干乙在中宮 → 寄坤二
    assert by[1]["gate"] == "景門"                                                       # 值使 from 離九 +1 (未−午) → 坎一
    assert [by[p]["god"] for p in Q.RING] == ["六合", "白虎", "玄武", "九地", "九天", "值符", "騰蛇", "太陰"]
    late = Q.cast_hour(datetime(2024, 2, 9, 23, 30), 8)
    assert late["day_gz"] == "甲辰" and late["late_zi"]                                  # 晚子時 → next day
    c = casting.cast("qimen", BIRTH)
    assert c.summary.startswith("陽遁6局")


# --- second audit batch: 旺衰, 真太陽時, geo/DST, 紫微 大限, 六壬 九宗門, 奇門 置閏, reference 節氣 ----

def test_bazi_strength_analysis_is_auditable():
    from fortune import bazi_ext as X
    p = X.exact_pillars(BIRTH.dt, BIRTH.tz_offset_hours)
    s = X.strength_analysis(p)
    assert s["day_master"] == "辛" and s["pattern"] == "七殺格"           # 午月 本氣 丁 = 辛之七殺
    assert s["label"].startswith("身弱") and s["ratio"] < 0.42
    assert s["yongshen"] == "土" and set(s["favourable"]) == {"土", "金"} and set(s["avoid"]) == {"木", "水", "火"}
    assert s["tiaohou"] == "水" and any("月令 午" in ln for ln in s["lines"]) and any("透" in ln for ln in s["lines"])
    # a 比劫-heavy chart reads strong and wants 官殺: 甲 day in 寅月 with 甲/乙 stems
    from datetime import datetime
    strong = X.strength_analysis(X.exact_pillars(datetime(1984, 2, 20, 4, 0), 8))   # 甲子年 丙寅月
    assert strong["ratio"] > 0.5
    c = casting.cast("bazi", BIRTH)
    assert c.readings["pattern"] == "七殺格" and c.readings["yongshen"].startswith("土")


def test_true_solar_time_shifts_cast_time_only_for_ganzhi_systems():
    from fortune import bazi_ext as X
    b = BirthInput(birth_date=date(1990, 6, 15), birth_time=time(14, 30), latitude=25.04, longitude=121.56, true_solar_time=True)
    tst = X.cast_dt(b)
    delta_min = (tst - b.dt).total_seconds() / 60
    assert 5.0 < delta_min < 7.5                       # +6.2 min longitude (121.56−120) + EoT ≈ −0.3
    assert X.cast_dt(BIRTH) == BIRTH.dt                # off by default
    # an hour-branch boundary: 00:55 clock at 121.56°E → ≈01:01 TST → 丑時, not 子時
    edge = BirthInput(birth_date=date(1990, 6, 15), birth_time=time(0, 55), latitude=25.04, longitude=121.56, true_solar_time=True)
    assert X.exact_pillars(X.cast_dt(edge), 8)["hour"]["branch"] == "丑"
    assert X.exact_pillars(edge.dt, 8)["hour"]["branch"] == "子"
    # astrology ignores the flag (it works in UT)
    a1 = casting.cast("astrology", b); a2 = casting.cast("astrology", b.model_copy(update={"true_solar_time": False}))
    assert a1.chart["planets"] == a2.chart["planets"]


def test_geo_lookup_and_taiwan_dst():
    from fortune import geo
    assert geo.lookup("Tokyo")["tz_offset_hours"] == 9 and geo.lookup("紐約")["longitude"] == -74.01
    assert geo.lookup("台北", date(1975, 6, 1))["tz_offset_hours"] == 9 and geo.lookup("台北", date(1975, 6, 1))["dst"]
    assert geo.lookup("台北", date(1975, 10, 1))["tz_offset_hours"] == 8
    assert geo.lookup("Taipei, Taiwan", date(1990, 6, 15))["name"] == "Taipei"
    assert geo.lookup("Atlantis") is None
    with pytest.raises(ValueError):
        BirthInput(birth_date=date(1850, 1, 1))


def test_ziwei_luck_periods():
    c = casting.cast("ziwei", BIRTH)
    L = c.chart["luck"]
    assert L["start_age"] == 5 and L["forward"] is False                 # 土五局, 庚(陽)年 女 → 逆行
    assert [d["palace"] for d in L["daxian"][:4]] == ["命宮", "兄弟", "夫妻", "子女"]
    assert L["daxian"][0]["ages"] == [5, 14] and L["daxian"][3]["years"][0] == 1990 + 35 - 1
    ln = next(l for d in L["daxian"] for l in d["liunian"] if l["year"] == 2026)
    assert ln["gz"] == "丙午" and ln["age"] == 37 and ln["flow_stars"]["流祿"] == "巳" and ln["suiqian"]["午"] == "太歲"
    pal = {p["name"]: p for p in c.chart["palaces"]}
    assert all("changsheng" in p and "boshi" in p for p in pal.values())
    assert sum(1 for p in pal.values() if p["boshi"] == "博士") == 1


def test_liuren_nine_course_types():
    from fortune import liuren_ext as LX
    B = LX.BRANCHES
    # 伏吟 (月將 = 占時) and 返吟 (opposite) are recognised
    assert LX.cast(0, 0, 5, 5)["kind"].startswith("伏吟")
    assert LX.cast(0, 0, 5, 11)["kind"].startswith("返吟")
    # 八專: 甲寅日 (干支同位) with no 賊克
    k = LX.cast(0, 2, 2, 2)
    assert k["kind"].startswith(("八專", "伏吟"))
    # Mei: 元首課 上克下, 三傳 丑寅卯 (regression from the first audit)
    c = casting.cast("liuren", BIRTH)
    assert c.chart["kind"].startswith("元首課") and c.chart["transmissions"] == ["丑", "寅", "卯"]
    # every date casts without error and only known course types appear
    kinds = set()
    for i in range(0, 400, 13):
        d = date(2000, 1, 1) + __import__("datetime").timedelta(days=i)
        kinds.add(casting.cast("liuren", BirthInput(birth_date=d, birth_time=time(7, 0))).chart["kind"].split("（")[0])
    assert kinds <= {"重審課", "元首課", "知一課", "涉害課", "遙克課", "昴星課", "別責課", "八專課", "伏吟課", "返吟課"}


def test_qimen_zhirun_method():
    from datetime import datetime
    from fortune import qimen_ext as Q
    g = Q.cast_hour(datetime(1990, 6, 15, 14, 30), 8, method="zhirun")
    assert g["method"] == "置閏法" and g["term"] == "夏至" and g["yuan"] == "上元" and g["ju"] == 9   # 己酉 head 06-13 超神 → 夏至上元
    assert Q.cast_hour(datetime(1990, 6, 15, 14, 30), 8)["term"] == "芒種"                          # 拆補 keeps the term in force
    c = casting.cast("qimen", BIRTH, qimen_method="zhirun")
    assert "置閏法" in c.summary


def test_solar_terms_match_published_values():
    """Reference instants: USNO equinox/solstice tables (UT) and the 台北市政府 2026 曆象表 (UTC+8)."""
    from fortune import bazi_ext as X
    ref = {(2024, 270): "2024-12-21 09:20", (2025, 0): "2025-03-20 09:01", (2025, 90): "2025-06-21 02:42", (2026, 0): "2026-03-20 14:46"}
    from datetime import datetime
    for (y, lon), want in ref.items():
        assert abs((X._term_utc(y, lon) - datetime.strptime(want, "%Y-%m-%d %H:%M")).total_seconds()) <= 60
    local = {n: t for t, n, _l in X.all_terms(2026, 8)}
    assert local["寒露"].strftime("%m-%d %H:%M") == "10-08 14:29" and local["冬至"].strftime("%m-%d %H:%M") == "12-22 04:49"


# --- cross-validation against sibling open-source engines (optional deps; skipped if absent) ---------

def _births(n: int, seed: int = 7):
    from random import Random
    from datetime import timedelta
    r = Random(seed)
    out = []
    for _ in range(n):
        d = date(1950, 1, 1) + timedelta(days=r.randrange(365 * 70))
        out.append(BirthInput(birth_date=d, birth_time=time(r.randrange(24), r.randrange(60)), gender=r.choice(["male", "female"]),
                              latitude=25.04, longitude=121.56, tz_offset_hours=8))
    return out


def test_oracle_lunar_python_pillars_terms_taiyuan_dayun():
    lp = pytest.importorskip("lunar_python")
    from fortune import bazi_ext as X
    from fortune import timeline as tl
    for b in _births(150):
        if b.dt.hour >= 23:
            continue                                   # 晚子時: lunar-python starts the hour stem from the NEXT day's stem; we keep the day's (school choice)
        p = X.exact_pillars(b.dt, 8)
        ec = lp.Solar.fromYmdHms(b.dt.year, b.dt.month, b.dt.day, b.dt.hour, b.dt.minute, 0).getLunar().getEightChar()
        assert [p[k]["gz"] for k in ("year", "month", "day", "hour")] == [ec.getYear(), ec.getMonth(), ec.getDay(), ec.getTime()], b.dt
        assert X.tai_yuan(p["month"]["stem_idx"], p["month"]["branch_idx"]) == ec.getTaiYuan()
        assert X.ming_gong(p["month"]["stem_idx"], p["month"]["branch_idx"], p["hour"]["branch_idx"]) == ec.getMingGong()
    # 節氣 instants agree to the minute
    for b in _births(40, seed=3):
        prev, _n = X.surrounding_jie(b.dt, 8)
        jq = lp.Solar.fromYmdHms(b.dt.year, b.dt.month, b.dt.day, b.dt.hour, b.dt.minute, 0).getLunar().getPrevJie()
        assert abs((prev[0] - __import__("datetime").datetime.strptime(jq.getSolar().toYmdHms(), "%Y-%m-%d %H:%M:%S")).total_seconds()) <= 120
    # 大運 sequence and start years (lunar-python sect 2 = 三日折一年 rounded to the hour)
    for b in _births(30, seed=11):
        ours = tl.bazi_dayun(b)
        ec = lp.Solar.fromYmdHms(b.dt.year, b.dt.month, b.dt.day, b.dt.hour, b.dt.minute, 0).getLunar().getEightChar()
        yun = ec.getYun(1 if b.gender == "male" else 0, 2)
        theirs = [(d.getGanZhi(), d.getStartYear()) for d in yun.getDaYun()[1:]]
        k = min(len(theirs), len(ours.periods))
        assert [p.label for p in ours.periods][:k] == [g for g, _y in theirs][:k], b.dt
        assert all(abs(int(p.start[:4]) - y) <= 1 for p, (_g, y) in zip(ours.periods[:k], theirs[:k]))


def test_oracle_x_iztro_star_placement():
    xi = pytest.importorskip("x_iztro")
    from fortune import bazi_ext as X, ziwei_ext as ZX
    ours_names = {"紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府", "太陰", "貪狼", "巨門", "天相", "天梁", "七殺", "破軍",
                  "文昌", "文曲", "左輔", "右弼", "祿存", "擎羊", "陀羅", "天魁", "天鉞", "火星", "鈴星", "地空", "地劫", "天馬",
                  "紅鸞", "天喜", "龍池", "鳳閣", "天哭", "天虛", "天刑", "天姚", "天才", "天壽", "孤辰", "寡宿"}
    for b in _births(40, seed=5):
        if b.dt.hour >= 23:
            continue
        hb = ZX.hour_branch_of(b.dt.hour)
        natal = ZX.build_chart(b.as_date, hb, clock_hour=b.dt.hour)
        chart = xi.Astro().by_solar(f"{b.dt.year}-{b.dt.month}-{b.dt.day}", hb, b.gender, language="zh-TW")
        theirs = {}
        for pal in chart.palaces:
            for st in list(pal.major_stars) + list(pal.minor_stars) + list(pal.adjective_stars):
                theirs[st.name] = pal.earthly_branch
        for star, br in natal["star_palace"].items():
            pass
        by_branch = {p["branch"]: p for p in natal["palaces"]}
        for p in natal["palaces"]:
            for s in p["stars"]:
                if s in ours_names:
                    assert theirs.get(s) == p["branch"], (b.dt, s, p["branch"], theirs.get(s))
        assert natal["five_elements_class"] == chart.five_elements_class and natal["soul"] == chart.soul and natal["body"] == chart.body
        luck = ZX.luck(natal, b.gender == "male", date(2026, 1, 1))
        for pal in chart.palaces:
            ours_p = by_branch[pal.earthly_branch]
            assert ours_p["changsheng"] == pal.changsheng12 and ours_p["boshi"] == pal.boshi12, (b.dt, pal.name)
            dx = next(d for d in luck["daxian"] if d["branch"] == pal.earthly_branch)
            assert tuple(dx["ages"]) == tuple(pal.decadal.range), (b.dt, pal.name)


def test_oracle_kinliuren_courses_and_generals():
    """kinliuren (MIT) as oracle. 四課, 十二天將 and the 賊克/遙克 course families must agree exactly;
    涉害 / 伏吟 / 返吟 / 別責 / 八專 follow school conventions that differ between implementations,
    so for those only an overall agreement floor is asserted."""
    kl = pytest.importorskip("kinliuren")
    from kinliuren import kinliuren as KL
    from fortune import bazi_ext as X, liuren_ext as LX
    import ephem
    from fortune import astro_ext as AX
    _ = kl
    strict = {"元首課", "重審課", "遙克課"}
    n = agree = agree1 = 0
    for b in _births(300, seed=9):
        p = X.exact_pillars(b.dt, 8)
        ds, db, hb = p["day"]["stem_idx"], p["day"]["branch_idx"], p["hour"]["branch_idx"]
        yj = (10 - int(AX.lon_of_date(ephem.Sun, AX.birth_utc(b)) // 30) % 12) % 12
        term = X.current_term(b.dt, 8)[1]
        lunar_m = "正二三四五六七八九十冬臘"[X.lunar_info(b.as_date, hb)["month"] - 1]
        try:
            theirs = KL.Liuren(term, lunar_m, p["day"]["gz"], p["hour"]["gz"]).result(0)
        except Exception:  # noqa: BLE001 — kinliuren raises on some 月將 lookups; skip those
            continue
        ours = LX.cast(ds, db, hb, yj)
        t_courses = [theirs["四課"][k][0] for k in ("一課", "二課", "三課", "四課")]
        o_courses = [c["upper"] + (c["lower"] if i else X.STEMS[ds]) for i, c in enumerate(ours["courses"])]
        if t_courses != o_courses:
            continue                                   # different 月將 convention for that date → not comparable
        n += 1
        t_gen = dict(zip(theirs["天地盤"]["天盤"], theirs["天地盤"]["天將"]))
        for br, g in ours["generals"].items():
            assert t_gen[br] == LX.GENERAL_SHORT[LX.GENERALS.index(g)], (b.dt, br)
        t3 = [theirs["三傳"][k][0] for k in ("初傳", "中傳", "末傳")]
        kind = ours["kind"].split("（")[0]
        their_kind = {"元首": "元首課", "重審": "重審課", "遙尅": "遙克課"}.get(theirs["格局"][0], "")
        if kind in strict and their_kind == kind:          # same course family on both sides → the 三傳 must agree exactly
            assert t3 == ours["transmissions"], (b.dt, theirs["格局"], ours["kind"])
        agree += t3 == ours["transmissions"]
        agree1 += t3[0] == ours["transmissions"][0]
    assert n >= 150 and agree / n >= 0.75 and agree1 / n >= 0.78, (n, agree, agree1)


def test_oracle_kinqimen_hour_chart():
    pytest.importorskip("kinqimen")
    import os, sys, kinqimen as _kq
    sys.modules.pop("config", None)                                  # kintaiyi (another oracle) ships a top-level `config` too
    sys.path.insert(0, os.path.dirname(_kq.__file__))
    from kinqimen import kinqimen as KQ
    from fortune import qimen_ext as Q
    import inspect
    if "minute" not in inspect.signature(KQ.Qimen.__init__).parameters:
        pytest.skip("kinqimen < 0.0.6 (no minute argument) — pip downgraded it; the oracle needs 0.0.6.6")
    pal = {"坎": 1, "坤": 2, "震": 3, "巽": 4, "中": 5, "乾": 6, "兌": 7, "艮": 8, "離": 9}
    n = 0
    for b in _births(40, seed=13):
        for method, code in (("chaibu", 1), ("zhirun", 2)):
            ours = Q.cast_hour(b.dt, 8, method=method)
            theirs = KQ.Qimen(b.dt.year, b.dt.month, b.dt.day, b.dt.hour, b.dt.minute).pan(code)
            if theirs["排局"] != f"{ours['dun']}{'一二三四五六七八九'[ours['ju'] - 1]}局{ours['yuan']}":
                continue                               # 置閏 boundary conventions differ around 閏 blocks; compare matching 局 only
            n += 1
            by = {p["palace"]: p for p in ours["palaces"]}
            for name, gate in theirs["門"].items():
                assert by[pal[name]]["gate"] == gate + "門", (b.dt, method, name)
            for name, star in theirs["星"].items():
                assert by[pal[name]]["star"].startswith("天" + star[0]) or star == "禽", (b.dt, method, name)
            hour_in_centre = ours["hour_gz"][0] == by[5]["earth_stem"] or (ours["hour_gz"][0] == "甲" and ours["xun_yi"] == by[5]["earth_stem"])
            for name, stem in theirs["天盤"].items():
                if "禽" in by[pal[name]]["star"] or hour_in_centre:
                    continue                           # 天禽/天芮 palace carries two stems; 時干在中宮 is handled differently by kinqimen
                assert by[pal[name]]["sky_stem"] == stem, (b.dt, method, name)
            assert ours["zhifu"][1] == theirs["值符值使"]["值符星宮"][0][0] and ours["zhishi"][0] == theirs["值符值使"]["值使門宮"][0][0]
    assert n >= 40


def test_oracle_swisseph_planets_and_houses():
    swe = pytest.importorskip("swisseph")
    from fortune import astro_ext as AX
    ids = {"Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN}
    for b in _births(30, seed=21):
        ut = AX.birth_utc(b)
        jd = swe.julday(ut.year, ut.month, ut.day, ut.hour + ut.minute / 60)
        rows = {p["body"]: p["ecliptic_lon"] for p in AX.planets_at(ut)}
        for name, i in ids.items():
            lon = swe.calc_ut(jd, i, swe.FLG_MOSEPH)[0][0]
            assert abs(((rows[name] - lon + 180) % 360) - 180) < 0.02, (b.dt, name)
        asc = swe.houses(jd, b.latitude, b.longitude, b"W")[1][0]
        assert abs(((AX.ascendant_lon(b) - asc + 180) % 360) - 180) < 0.02, b.dt


# --- question-oriented readings, synthesis and language option ---------------------------------

def test_focus_classify_and_extract_all_systems():
    from fortune import focus as F
    assert F.classify("明年事業會不會升遷") == "career" and F.classify("money and investments") == "wealth"
    assert F.classify("感情什麼時候穩定") == "love" and F.classify("身體狀況") == "health" and F.classify(None) == "general"
    charts = {k: casting.cast(k, BIRTH, transits=(k == "astrology")) for k in casting.REGISTRY}
    for topic in ("career", "love", "wealth", "health", "study", "family", "general"):
        for k, ch in charts.items():
            e = F.extract(ch, topic, male=False)
            assert e["verdict"] in ("favourable", "neutral", "unfavourable") and isinstance(e["facts"], dict) and e["reason"], (k, topic)
    bz = F.extract(charts["bazi"], "career", male=False)
    assert bz["facts"]["本題相關十神"] == ["正官", "七殺", "正印", "偏印"] and any("七殺" in w for w in bz["facts"]["出現位置"])
    zw = F.extract(charts["ziwei"], "love")
    assert zw["facts"]["本題宮位"].startswith("夫妻")
    ly = F.extract(charts["liuyao"], "career")
    assert ly["facts"]["用神"] == ["官鬼"]
    syn = F.synthesize(charts, "career", False)
    assert len(syn["systems"]) == 13 and sum(syn["tally"].values()) == 13 and syn["lean"] in ("favourable", "neutral", "unfavourable")
    assert set(syn["consensus"]).isdisjoint(syn["conflicts"])


def test_prompts_carry_focus_facts_and_language():
    from fortune.interpret import _prompts, lang_instruction
    chart = casting.cast("bazi", BIRTH)
    sysm, user = _prompts(chart, "事業升遷", "zh")
    assert "與本題直接相關的事實" in user and "本題相關十神" in user and "正官" in user
    assert "只用繁體中文" in sysm and chart.readings["focus_topic"].startswith("事業")
    _s, user_en = _prompts(casting.cast("bazi", BIRTH), None, "en")
    assert "English only" in user_en and "與本題直接相關" not in user_en
    assert "BILINGUALLY" in lang_instruction("both") and lang_instruction(None) == lang_instruction("both")


def test_synthesis_endpoint():
    from fastapi.testclient import TestClient
    from fortune.api.main import app
    c = TestClient(app)
    body = {"birth": BIRTH.model_dump(mode="json"), "focus": "事業", "lang": "zh"}
    r = c.post("/synthesis", json=body)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["topic"] == "career" and len(j["systems"]) == 13 and j["interpretation"] and not j["errors"]
    r2 = c.post("/synthesis", json={**body, "systems": ["bazi", "ziwei", "liuyao"]})
    assert [s["system"] for s in r2.json()["systems"]] == ["bazi", "ziwei", "liuyao"]
    r3 = c.post("/reading/bazi", json={"birth": BIRTH.model_dump(mode="json"), "focus": "財運", "lang": "en"})
    assert r3.status_code == 200 and r3.json()["readings"]["focus_topic"].startswith("財運")


# --- 擇日 / 流日 ---------------------------------------------------------------------------------

def test_liuri_and_liushi():
    from fortune import bazi_ext as X
    full = X.full_chart(BIRTH)
    lr = X.liuri(full, date(2026, 11, 3), 8)
    assert lr["gz"] == "辛巳" and lr["clash_natal_day"]                 # 巳 沖 natal 日支 亥
    assert lr["year_gz"] == "丙午" and lr["month_gz"] == "戊戌" and lr["stem_god"] == "比肩"
    hs = X.liushi(full, date(2026, 11, 12), 8)
    assert len(hs) == 12 and hs[0]["gz"] == "丙子" and hs[5]["clash_natal_day"]   # 庚寅日 → 丙子時; 巳時 沖 亥
    assert any(h["he_natal_day"] for h in hs)                            # 寅 合 亥


def test_zeri_select_and_rules():
    from fortune import zeri
    out = zeri.select(BIRTH, date(2026, 11, 1), date(2026, 11, 30), "wedding", top=5)
    assert len(out["days"]) == 30 and len(out["best"]) == 5 and out["purpose_label"].startswith("結婚")
    by = {d["date"]: d for d in out["days"]}
    assert by["2026-11-03"]["grade"] == 1 and by["2026-11-03"]["hard_avoid"]           # 日沖 → 忌
    assert all(by[d]["grade"] >= 3 and not by[d]["hard_avoid"] for d in out["best"])
    assert all(by[d]["grade"] == 1 for d in out["avoid"])
    best = by[out["best"][0]]
    assert best.get("hours") and len(best["hours"]) == 12 and sum(1 for h in best["hours"] if h["best"]) <= 3
    assert best["qimen"]["zhishi"] and isinstance(best["qimen"]["lucky_dirs"], list)
    assert any(r["src"] == "八字" for r in best["reasons"]) and all("delta" in r for r in best["reasons"])
    # every day's score is the sum of its listed reasons
    for d in out["days"]:
        assert abs(sum(r["delta"] for r in d["reasons"]) - d["score"]) < 0.15, d["date"]
    today = zeri.day_outlook(BIRTH, date(2026, 10, 8))
    assert today["context"]["liuyue"] == "丁酉" and len(today["hours"]) == 12 and today["gz"]["day"] == "乙卯"


def test_zeri_and_day_endpoints():
    from fastapi.testclient import TestClient
    from fortune.api.main import app
    c = TestClient(app)
    b = BIRTH.model_dump(mode="json")
    r = c.post("/zeri", json={"birth": b, "start": "2026-11-01", "end": "2026-11-15", "purpose": "opening", "top": 3, "lang": "zh"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert len(j["days"]) == 15 and len(j["best"]) == 3 and j["interpretation"] and j["rules"]
    assert c.post("/zeri", json={"birth": b, "start": "2026-01-01", "end": "2026-12-31", "purpose": "opening"}).status_code == 400
    assert c.post("/zeri", json={"birth": b, "start": "2026-01-01", "end": "2026-01-02", "purpose": "nope"}).status_code == 400
    d = c.post("/day", json={"birth": b, "date": "2026-10-08"})
    assert d.status_code == 200 and d.json()["gz"]["day"] == "乙卯" and len(d.json()["hours"]) == 12


# --- calendar backend, CLI, MCP ------------------------------------------------------------------

def test_lunar_backend_fixes_lunardate_month_errors():
    from fortune import lunar
    assert lunar.to_lunar(date(1933, 7, 22)) == (1933, 5, 30, True)       # lunardate says 六月初一
    assert lunar.to_lunar(date(1933, 8, 20)) == (1933, 6, 29, False)
    assert lunar.to_solar(1990, 5, 23) == date(1990, 6, 15) and lunar.to_lunar(date(1990, 6, 15)) == (1990, 5, 23, False)
    from fortune import ziwei_ext as ZX
    assert ZX.lunar_for_ziwei(date(1933, 7, 22), 10)[:3] == (1933, 6, 30)   # 閏五月三十 → 下半月歸次月


def test_cli_runs():
    import io, contextlib
    from fortune.cli import main
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert main(["bazi", "1990-06-15", "14:30", "--place", "台北", "--gender", "female"]) == 0
        assert main(["ziwei", "1990-06-15", "14:30", "--gender", "female"]) == 0
        assert main(["synthesis", "1990-06-15", "14:30", "--gender", "female", "--ask", "money"]) == 0
        assert main(["zeri", "1990-06-15", "14:30", "--purpose", "moving", "--from", "2026-11-01", "--to", "2026-11-10"]) == 0
        assert main(["systems"]) == 0
    out = buf.getvalue()
    assert "辛" in out and "命宮" in out and "財運" in out and "擇日" in out and "xiaoliuren" in out


def test_mcp_server_tools():
    pytest.importorskip("mcp")
    import asyncio, json
    from fortune import mcp_server as M
    async def go():
        names = [t.name for t in await M.server.list_tools()]
        assert {"cast", "reading", "synthesis", "zeri", "day", "synastry", "list_systems", "geo_lookup"} <= set(names)
        r = await M.server.call_tool("cast", {"system": "liuyao", "birth_date": "1990-06-15", "birth_time": "14:30"})
        payload = json.loads(r.content[0].text) if hasattr(r, "content") else json.loads(r[0].text)
        assert payload["system"] == "liuyao" and payload["chart"]["hexagram"]["name"]
    asyncio.run(go())
