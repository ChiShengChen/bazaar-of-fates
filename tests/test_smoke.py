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
