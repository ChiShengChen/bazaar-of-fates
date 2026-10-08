"""專科 (career / wealth / health / study / family): classification, natal, timing, topic sheets, and the surfaces."""

from datetime import date, time

import pytest

from fortune import casting, specialist as S
from fortune.birth import BirthInput

MEI = BirthInput(name="Mei", birth_date=date(1990, 6, 15), birth_time=time(14, 30), gender="female", place="台北", latitude=25.04, longitude=121.56)
NO_GEOMETRY = BirthInput(birth_date=date(1985, 2, 2))


@pytest.fixture(scope="module")
def charts():
    return {k: casting.cast(k, MEI, transits=(k == "astrology")) for k in ("bazi", "ziwei", "astrology", "jyotish")}


@pytest.mark.parametrize("topic,q,want", [
    ("career", "該不該轉職", "change"), ("career", "明年會升遷嗎", "promotion"), ("career", "想創業開店", "startup"), ("career", "我適合什麼行業", "direction"),
    ("career", "國考考得上嗎", "exam"), ("career", None, "current"),
    ("wealth", "適合投資股票嗎", "invest"), ("wealth", "今年會破財嗎", "loss"), ("wealth", "想買房", "property"), ("wealth", "跟朋友合夥", "partner"),
    ("health", "要開刀", "illness"), ("health", "最近失眠壓力大", "mental"), ("health", "哪一年要注意", "timing"),
    ("study", "學測考運", "exam"), ("study", "想申請留學", "admission"), ("study", "選什麼科系", "major"), ("study", "讀不下去", "focus"),
    ("family", "媽媽的健康", "parents"), ("family", "想生小孩", "children"), ("family", "要不要搬家", "home"), ("family", "跟哥哥不合", "siblings"),
])
def test_classify_sub_intent(topic, q, want):
    assert S.classify(topic, q) == want


def test_route_picks_the_specialist():
    assert S.route("該不該轉職") == "career" and S.route("想投資") == "wealth" and S.route("失眠") == "health"
    assert S.route("考研究所") == "study" and S.route("父母") == "family" and S.route("何時結婚") == "love" and S.route(None) == "career"


def test_unknown_topic_raises():
    with pytest.raises(ValueError):
        S.spec("love")


@pytest.mark.parametrize("topic", S.TOPICS)
def test_natal_scores_four_systems(charts, topic):
    n = S.natal(topic, charts, male=False)
    assert {r["system"] for r in n["systems"]} == {"bazi", "ziwei", "astrology", "jyotish"}
    for r in n["systems"]:
        assert r["verdict"] in ("favourable", "neutral", "unfavourable")
        assert isinstance(r["reasons"], list) and isinstance(r["facts"], dict)
        assert not any("本題" in x for x in r["reasons"])          # the topic is named, never the placeholder
    assert n["label"] in ("上吉", "吉", "可", "平", "宜守")
    zh = S.spec(topic)["zh"]
    assert n["summary"].startswith(f"命中{zh}")


def test_bazi_natal_reads_the_topic_palace(charts):
    bz = charts["bazi"].chart
    c = S._bazi_natal("career", bz, False)
    assert "月支（提綱・事業宮）" in c["facts"] and c["facts"]["月支（提綱・事業宮）"] == bz["pillars"][1]["branch"]
    w = S._bazi_natal("wealth", bz, False)
    assert w["facts"]["財庫"] == S._TOMB[S._god_elems(bz["strength"]["dm_elem"])["財"]]
    h = S._bazi_natal("health", bz, False)
    assert set(h["facts"]["五行"]) == set("木火土金水") and any("日主" in r for r in h["reasons"])
    f = S._bazi_natal("family", bz, False)
    assert "年支（父母宮・祖業）" in f["facts"]


def test_ziwei_natal_uses_the_topic_palace(charts):
    for topic, pal in (("career", "官祿"), ("wealth", "財帛"), ("health", "疾厄"), ("study", "父母"), ("family", "田宅")):
        r = S._ziwei_natal(topic, charts["ziwei"].chart)
        key = next(k for k in r["facts"] if k.startswith(pal))
        assert r["facts"][key][0] in "甲乙丙丁戊己庚辛壬癸"
        assert "三方" in r["facts"] and len(r["facts"]["三方"]) == 2


def test_astro_natal_degrades_without_houses():
    ch = casting.cast("astrology", NO_GEOMETRY)
    r = S._astro_natal("career", ch)
    assert "註" in r["facts"] and r["verdict"] in ("favourable", "neutral", "unfavourable")


@pytest.mark.parametrize("topic", S.TOPICS)
def test_timing_scores_every_year_with_listed_terms(charts, topic):
    t = S.timing(topic, MEI, charts, 2026, 5)
    assert [y["year"] for y in t["years"]] == list(range(2026, 2031))
    for y in t["years"]:
        assert y["score"] == pytest.approx(round(sum(r["delta"] for r in y["reasons"]), 1))
        assert y["grade"] in (1, 2, 3, 4, 5)
        assert {r["src"] for r in y["reasons"]} <= {"八字", "紫微", "西洋", "Jyotiṣa"}
        assert y["age"] == y["context"]["bazi"]["age"]
        if y["sign"]:
            kws = S._SIGN_KW[topic]
            assert any(any(k in r["text"] for k in kws) for r in y["reasons"])
    if topic == "health":
        assert all(next(x for x in t["years"] if x["year"] == c)["score"] <= -1.5 for c in t["caution"])
    else:
        assert all(next(x for x in t["years"] if x["year"] == b)["score"] >= 3 for b in t["best"])
    assert t["sign_label"]


def test_ziwei_year_lands_sihua_in_the_topic_palace(charts):
    rs, ctx = S._ziwei_year("wealth", charts["ziwei"].chart, 2028)
    assert len(ctx["流年四化"]) == 4 and ctx["流年財帛宮"] in S._B
    assert any("化忌入財帛宮" in r["text"] for r in rs)          # 戊年 天機化忌; 天機 sits in 財帛 for this chart


def test_wealth_year_uses_the_treasury(charts):
    full = charts["bazi"].chart
    tomb = S._TOMB[S._god_elems(full["strength"]["dm_elem"])["財"]]
    hit = [yr for yr in range(2026, 2040) if any("沖財庫" in r["text"] for r in S._bazi_year("wealth", full, yr, False)[0])]
    assert hit and all((S._B.index(S.X.BRANCHES[(y - 4) % 12]) - S._B.index(tomb)) % 12 == 6 for y in hit)


def test_family_year_child_star_is_gender_aware(charts):
    full = charts["bazi"].chart
    f = {r["text"] for yr in range(2026, 2036) for r in S._bazi_year("family", full, yr, False)[0] if "子女星" in r["text"]}
    m = {r["text"] for yr in range(2026, 2036) for r in S._bazi_year("family", full, yr, True)[0] if "子女星" in r["text"]}
    assert all("食神" in t or "傷官" in t for t in f) and all("正官" in t or "七殺" in t for t in m)


def test_extra_sheets(charts):
    c = S.extra("career", charts, False)
    assert c["industries"] and c["styles"] and "紫微 官祿宮主星 → 職業象" in c["facts"]
    w = S.extra("wealth", charts, False)
    assert w["facts"]["財性"] and "財庫" in w["facts"]["財星五行"]
    h = S.extra("health", charts, False)
    assert set(h["facts"]["五行分布"]) == set("木火土金水") and h["facts"]["偏弱"]
    st = S.extra("study", charts, False)
    assert st["facts"]["學習型態"] and "喜用五行 → 科系方向" in st["facts"]
    f = S.extra("family", charts, False)
    assert "父母宮（年柱）" in f["facts"] and "子女宮（時柱）" in f["facts"] and "紫微 田宅宮" in f["facts"]


@pytest.mark.parametrize("topic,q,intent", [("career", "該不該轉職", "change"), ("health", "哪年要注意", "timing")])
def test_consult_assembles_everything(topic, q, intent):
    out = S.consult(topic, MEI, q, start_year=2026, years=3)
    assert out["topic"] == topic and out["intent"] == intent and out["errors"] == {}
    assert len(out["this_year"]["systems"]) == len(casting.REGISTRY) and len(out["timing"]["years"]) == 3
    assert out["extra"]["facts"] and "interpretation" not in out
    system, user = S.prompts(out)
    assert S.spec(topic)["master"] in system and q in user
    first = S.spec(topic)["order"][intent][0]
    assert user.index(f'"{first}"') < user.index('"natal"') or first == "natal"


def test_consult_without_geometry_and_with_reading():
    out = S.consult("study", NO_GEOMETRY, None, years=2, read=True)
    assert out["intent"] == "current" and out["interpretation"]
    assert "註" in next(r for r in out["natal"]["systems"] if r["system"] == "astrology")["facts"]


def test_cli_specialists_run(capsys):
    from fortune.cli import main
    for topic in ("career", "family"):
        assert main([topic, "1990-06-15", "14:30", "--gender", "female", "--ask", "明年", "--years", "2", "--from-year", "2026"]) == 0
        out = capsys.readouterr().out
        assert "【命】" in out and "【運】" in out and "2026" in out


def test_api_consult_endpoints():
    from fastapi.testclient import TestClient
    from fortune.api.main import app
    c = TestClient(app)
    topics = c.get("/consult").json()
    assert [t["topic"] for t in topics] == ["love", *S.TOPICS]
    r = c.post("/consult/wealth", json={"birth": {"birth_date": "1990-06-15", "birth_time": "14:30", "gender": "female"}, "question": "想買房", "start_year": 2026, "years": 2, "read": False})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["intent"] == "property" and len(j["timing"]["years"]) == 2 and j["extra"]["facts"]["財性"]
    r = c.post("/consult/auto", json={"birth": {"birth_date": "1990-06-15"}, "question": "何時結婚", "years": 1, "read": False})
    assert r.status_code == 200 and "match" in r.json()            # routed to the love specialist
    assert c.post("/consult/nope", json={"birth": {"birth_date": "1990-06-15"}, "years": 1}).status_code == 404
    assert c.post("/consult/career", json={"birth": {"birth_date": "1990-06-15"}, "years": 99}).status_code == 400


def test_mcp_consult_tool():
    from fortune import mcp_server as M
    out = M.consult("auto", "1990-06-15", "考研究所", "14:30", "female", years=2, start_year=2026)
    assert out["topic"] == "study" and "context" not in out["timing"]["years"][0]
