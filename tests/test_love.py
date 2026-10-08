"""感情專科 / love-specialist: natal disposition, 桃花年 timing, 合婚, classification, and the surfaces."""

from datetime import date, time

import pytest

from fortune import casting, love
from fortune.birth import BirthInput

MEI = BirthInput(name="Mei", birth_date=date(1990, 6, 15), birth_time=time(14, 30), gender="female", place="台北", latitude=25.04, longitude=121.56)
JUN = BirthInput(name="Jun", birth_date=date(1988, 11, 3), birth_time=time(8, 15), gender="male", place="台北", latitude=25.04, longitude=121.56)
NO_GEOMETRY = BirthInput(birth_date=date(1985, 2, 2))


@pytest.fixture(scope="module")
def charts():
    return {k: casting.cast(k, MEI, transits=(k == "astrology")) for k in ("bazi", "ziwei", "astrology", "jyotish")}


@pytest.mark.parametrize("q,partner,want", [
    ("我什麼時候會遇到正緣？", False, "timing"), ("我跟他合不合", False, "match"), (None, True, "match"), (None, False, "current"),
    ("該不該分手", False, "breakup"), ("想跟前任復合", False, "reconcile"), ("他有第三者嗎", False, "affair"),
    ("婚姻會幸福嗎", False, "marriage"), ("when will I get married", False, "timing"),
])
def test_classify_sub_intent(q, partner, want):
    assert love.classify(q, has_partner=partner) == want


def test_natal_uses_gendered_spouse_star(charts):
    n = love.natal(charts, male=False)
    bz = next(r for r in n["systems"] if r["system"] == "bazi")
    assert "正官" in bz["facts"]["配偶星"] and "夫星" in bz["facts"]["配偶星"]
    n_m = love.natal(charts, male=True)
    assert "正財" in next(r for r in n_m["systems"] if r["system"] == "bazi")["facts"]["配偶星"]
    assert {r["system"] for r in n["systems"]} == {"bazi", "ziwei", "astrology", "jyotish"}
    for r in n["systems"]:
        assert r["verdict"] in ("favourable", "neutral", "unfavourable")
        assert isinstance(r["reasons"], list)
    assert n["label"] in ("上吉", "吉", "可", "平", "宜守")


def test_ziwei_natal_reads_the_spouse_palace(charts):
    zw = next(r for r in love.natal(charts, False)["systems"] if r["system"] == "ziwei")
    assert zw["facts"]["夫妻宮"].startswith(("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"))
    assert "三方" in zw["facts"] and len(zw["facts"]["三方"]) == 2
    # no duplicated star names when natal stars and iztro 雜曜 overlap
    for line in zw["reasons"]:
        if "桃花曜" in line:
            inside = line.split("夫妻宮 ")[1].split("；")[0]
            parts = [p for p in inside.split("、") if p and p != "—"]
            assert len(parts) == len(set(parts))


def test_timing_scores_every_year_with_listed_terms(charts):
    t = love.timing(MEI, charts, 2026, 6)
    assert [y["year"] for y in t["years"]] == list(range(2026, 2032))
    for y in t["years"]:
        assert y["score"] == pytest.approx(round(sum(r["delta"] for r in y["reasons"]), 1))
        assert y["grade"] in (1, 2, 3, 4, 5)
        assert {r["src"] for r in y["reasons"]} <= {"八字", "紫微", "西洋", "Jyotiṣa"}
        assert y["age"] == y["context"]["bazi"]["age"]
    assert all(next(x for x in t["years"] if x["year"] == b)["score"] >= 3 for b in t["best"])
    # a marriage sign needs a marriage-type term, not just a good year
    for y in t["years"]:
        if y["marriage_sign"]:
            assert any(k in r["text"] for r in y["reasons"] for k in ("紅鸞", "天喜", "配偶星", "化祿入夫妻", "過七宮"))


def test_timing_bazi_terms_are_gender_aware(charts):
    full = charts["bazi"].chart
    f_terms = {r["text"] for yr in range(2026, 2036) for r in love._bazi_year(full, yr, False)[0]}
    m_terms = {r["text"] for yr in range(2026, 2036) for r in love._bazi_year(full, yr, True)[0]}
    assert any("正官" in t or "七殺" in t for t in f_terms if "配偶星" in t)
    assert not any("正官" in t or "七殺" in t for t in m_terms if "配偶星" in t)


def test_ziwei_year_lands_sihua_and_flow_spouse_palace(charts):
    rs, ctx = love._ziwei_year(charts["ziwei"].chart, 2027)
    assert len(ctx["流年四化"]) == 4 and all("化" in s and "→" in s for s in ctx["流年四化"])
    assert ctx["流年夫妻宮"] in "子丑寅卯辰巳午未申酉戌亥"
    assert all(r["src"] == "紫微" for r in rs)


def test_match_bazi_and_synastry_terms():
    m = love.match(MEI, JUN)
    srcs = {r["src"] for r in m["reasons"]}
    assert "八字" in srcs and "西洋" in srcs
    assert m["score"] == pytest.approx(round(sum(r["delta"] for r in m["reasons"]), 1))
    assert "Mei" in m["facts"] and "Jun" in m["facts"] and "日柱" in m["facts"]["Mei"]
    assert "composite" in " ".join(m["facts"])
    # symmetric in the 八字 pair terms (same two people either way round)
    m2 = love.match(JUN, MEI)
    assert sum(r["delta"] for r in m["reasons"] if r["src"] == "八字") == pytest.approx(sum(r["delta"] for r in m2["reasons"] if r["src"] == "八字"))


def test_match_detects_a_branch_clash():
    a = BirthInput(name="A", birth_date=date(1990, 1, 10))        # 日支 and 年支 chosen only through the engine
    b = BirthInput(name="B", birth_date=date(1990, 1, 16))        # six days apart → 日支 six apart → 相沖
    m = love.match(a, b)
    assert any("日支（夫妻宮）相沖" in r["text"] for r in m["reasons"])


def test_consult_assembles_everything_and_degrades_without_geometry():
    out = love.consult(MEI, "何時有正緣", partner=JUN, start_year=2026, years=3)
    assert out["intent"] == "timing" and out["match"] and out["errors"] == {}
    assert len(out["this_year"]["systems"]) == len(casting.REGISTRY)
    assert len(out["timing"]["years"]) == 3
    assert "interpretation" not in out
    out2 = love.consult(NO_GEOMETRY, None, years=2, read=True)
    assert out2["match"] is None and out2["intent"] == "current"
    astro = next(r for r in out2["natal"]["systems"] if r["system"] == "astrology")
    assert "註" in astro["facts"]            # no houses → says so instead of inventing a 7th house
    assert out2["interpretation"]            # mock backend: facts digest


def test_prompt_leads_with_the_sub_question_facts():
    out = love.consult(MEI, "我跟他合不合", partner=JUN, start_year=2026, years=2)
    system, user = love.prompts(out, lang="zh")
    assert "專看感情" in system or "love" in system.lower()
    assert user.index('"match"') < user.index('"natal"') < user.index('"timing"')
    assert "合不合" in user and "繁體中文" in system


def test_cli_love_runs(capsys):
    from fortune.cli import main
    assert main(["love", "1990-06-15", "14:30", "--gender", "female", "--ask", "何時有正緣", "--years", "3", "--from-year", "2026",
                 "--partner-date", "1988-11-03", "--partner-time", "08:15", "--partner-gender", "male"]) == 0
    out = capsys.readouterr().out
    assert "【命】" in out and "【運】" in out and "【合婚】" in out and "2026" in out


def test_api_love_endpoint():
    from fastapi.testclient import TestClient
    from fortune.api.main import app
    c = TestClient(app)
    r = c.post("/love", json={"birth": {"name": "Mei", "birth_date": "1990-06-15", "birth_time": "14:30", "gender": "female"},
                              "partner": {"name": "Jun", "birth_date": "1988-11-03", "birth_time": "08:15", "gender": "male"},
                              "question": "合不合", "start_year": 2026, "years": 2, "read": False})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["intent"] == "match" and j["match"]["label"] and len(j["timing"]["years"]) == 2
    assert c.post("/love", json={"birth": {"birth_date": "1990-06-15"}, "years": 99}).status_code == 400
