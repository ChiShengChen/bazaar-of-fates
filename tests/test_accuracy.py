"""準確度 round: 六壬 九宗門 rule fixes, 八字 神煞 full table, 紫微 brightness schools, native 太乙 年計 (vs kintaiyi oracle)."""

from datetime import date, time

import pytest

from fortune import bazi_ext as X
from fortune import casting
from fortune import liuren_ext as LX
from fortune import taiyi_ext as T
from fortune.birth import BirthInput

S, B = X.STEMS, X.BRANCHES


def _lr(day_gz: str, hb: str, yj: str) -> dict:
    return LX.cast(S.index(day_gz[0]), B.index(day_gz[1]), B.index(hb), B.index(yj))


# --- 六壬 -------------------------------------------------------------------------------------

def test_duplicate_courses_do_not_fake_a_sheihai():
    # 甲子日 子時 寅將: 一課 寅上辰 and 四課 寅上辰 are the same 賊 → one candidate → 重審, 初傳 辰
    k = _lr("甲子", "子", "寅")
    assert k["kind"].startswith("重審") and k["transmissions"] == ["辰", "午", "申"]


def test_fuyin_mutual_xing_returns_to_the_first():
    # 丁卯日 伏吟 無剋 陰日 → 自信：初傳 支上神 卯，中傳 卯刑子，末傳 子刑卯 (回初傳)
    k = _lr("丁卯", "子", "子")
    assert k["kind"].startswith("伏吟") and k["transmissions"] == ["卯", "子", "卯"]


def test_fuyin_self_xing_middle_takes_the_clash():
    # 壬子日 伏吟 陽日：干上神 亥 自刑 → 中傳 支上神 子，末傳 子之刑 卯
    k = _lr("壬子", "午", "午")
    assert k["transmissions"][0] == "亥" and k["transmissions"][1] == "子" and k["transmissions"][2] == "卯"


def test_yaoke_precedes_biezé():
    # 丙寅日 子時 酉將: 三課不備, 無賊克, but 亥 (上神) 剋 丙 → 遙克 (蒿矢), not 別責
    k = _lr("丙寅", "子", "酉")
    assert k["kind"].startswith("遙克") and k["transmissions"][0] == "亥"


def test_sheihai_ties_resolve_by_meng_then_zhong():
    """Across the whole 8,640-course space the 涉害 ties always split by 孟 (見機) or 仲 (察微); 綴瑕 is never needed."""
    from collections import Counter
    c = Counter()
    for g in range(60):
        for hb in range(12):
            for yj in range(12):
                k = LX.cast(g % 10, g % 12, hb, yj)
                for n in k["notes"]:
                    if "涉害深淺相等" in n:
                        c[n] += 1
                        assert k["kind"].startswith("涉害")
    assert c["涉害深淺相等，取孟上神"] == 96 and c["涉害深淺相等，取仲上神"] == 12 and not any("綴瑕" in n for n in c)


def test_fullspace_script_runs(capsys):
    pytest.importorskip("kinliuren")
    import runpy
    import sys
    sys.argv = ["x", "--show", "0"]
    try:
        runpy.run_path("scripts/liuren_fullspace_check.py", run_name="__main__")
    except SystemExit:
        pass
    out = capsys.readouterr().out
    assert "元首課" in out and "100.0%" in out


# --- 八字 神煞 ----------------------------------------------------------------------------------

def test_new_shensha_by_day_stem():
    ss = lambda br, **kw: X.shensha_for(None, B.index(br), ys=S.index("庚"), ds=S.index("甲"), yb=B.index("午"), db=B.index("子"), mb=B.index("午"), **kw)  # noqa: E731
    assert "流霞" in ss("酉") and "金輿" in ss("辰") and "血刃" in ss("申") and "天官貴人" in ss("未") and "天福貴人" in ss("酉")
    assert "福星貴人" in ss("寅") and "災煞" in ss("午")                 # 甲→寅子; 申子辰→午
    assert "流霞" not in ss("酉", full=False)                         # the core set is unchanged


def test_day_pillar_shensha_and_gendered_yuanchen():
    c = casting.cast("bazi", BirthInput(birth_date=date(1990, 6, 15), birth_time=time(14, 30), gender="female")).chart
    day = c["pillars"][2]
    assert day["gz"] == "辛亥" and "孤鸞" in day["shensha"] and "死符" in day["shensha"]      # 午年 亥 = 太歲後五位 死符
    f = c["pillars"][2]["shensha"]
    m = casting.cast("bazi", BirthInput(birth_date=date(1990, 6, 15), birth_time=time(14, 30), gender="male")).chart["pillars"][2]["shensha"]
    assert ("元辰" in f) != ("元辰" in m)                                # 陽年: 女 backward, 男 forward → lands on different branches
    assert "shensha_chart" in c
    x = X.shensha_for(S.index("甲"), B.index("辰"), ys=S.index("甲"), ds=S.index("甲"), yb=B.index("子"), db=B.index("辰"), mb=B.index("寅"), is_pillar=True, gz="甲辰", role="day")
    assert "十惡大敗" in x and "魁罡" not in x


def test_sanqi_and_gonglu():
    p = {"year": {"stem": "乙", "gz": "乙丑", "nayin": "海中金", "branch": "丑"}, "month": {"stem": "丙", "gz": "丙戌"}, "day": {"stem": "丁", "gz": "丁巳", "branch": "巳"}, "hour": {"stem": "丁", "gz": "丁未"}}
    out = X.pillar_shensha(p)["chart"]
    assert any(o.startswith("三奇貴人（乙丙丁）") for o in out) and "拱祿" in out


# --- 紫微 亮度流派 --------------------------------------------------------------------------------

def test_brightness_schools():
    pytest.importorskip("x_iztro")
    b = BirthInput(birth_date=date(1990, 6, 15), birth_time=time(14, 30), gender="female")
    q = casting.cast("ziwei", b, brightness_school="quanshu")
    z = casting.cast("ziwei", b, brightness_school="zhongzhou")
    s3 = casting.cast("ziwei", b, brightness_school="simple")
    levels = lambda c: {v for p in c.chart["palaces"] for v in p["brightness"].values() if v}  # noqa: E731
    assert levels(z) <= {"廟", "旺", "利", "陷"} and levels(s3) <= {"廟", "平", "陷"}
    assert levels(q) - {"廟", "旺", "得", "利", "平", "不", "陷"} == set()
    assert all(p["brightness"].get("祿存") == "廟" for p in q.chart["palaces"] if "祿存" in p["brightness"])   # 全書：祿存所到皆廟
    assert "中州派" in z.readings["brightness_school"]


# --- 太乙 ---------------------------------------------------------------------------------------

def test_taiyi_accumulated_years_and_ju():
    assert T.jinian(1984) == 10155901 and T.year_board(date(1984, 6, 15))["ju"] == 10155901 % 72 == 13
    b = T.year_board(date(1990, 6, 15))
    assert b["accumulated"] == 10155907 and b["ju"] == 19 and b["taiyi"] == "坎" and b["taisui"] == "午"
    assert b["jigod"] == "申" and b["hegod"] == "未"                   # 午年：寅逆行六位 → 申；丑逆行六位 → 未
    assert b["wenchang"] == "申" and b["shiji"] == "艮" and b["home_cal"] == 8 and b["away_cal"] == 32
    assert b["home_general"] == 8 and b["away_general"] == 2 and b["away_vgen"] == 6
    assert b["verdict"] in ("主勝", "客勝", "和") and len(b["doors"]) == 8 and set(b["doors"].values()) == set("開休生傷杜景死驚")


def test_taiyi_three_years_per_palace_never_centre():
    seen = [T.year_board(date(y, 6, 15))["taiyi"] for y in range(2000, 2024)]
    assert "中" not in seen and all(seen[i] == seen[i + 1] or seen[i] != seen[i + 1] for i in range(len(seen) - 1))
    assert sorted(set(seen)) == sorted("乾離艮震兌坤坎巽") and all(seen.count(g) == 3 for g in set(seen))


def test_taiyi_chart_and_methods():
    b = BirthInput(birth_date=date(1990, 6, 15), birth_time=time(14, 30), gender="female")
    c = casting.cast("taiyi", b)
    assert c.readings["natal_ju"] == "陽遁19局" and "命局" in c.reasoning_chain[0] and c.chart["natal"]["sixteen"]
    j = casting.cast("taiyi", b, taiyi_method="jinjing")
    assert j.chart["natal"]["accumulated"] == 1936557 + 1990 and j.readings["method"] == "太乙金鏡式經"


def test_taiyi_matches_kintaiyi_oracle():
    kt = pytest.importorskip("kintaiyi")
    import os
    import sys
    import warnings
    warnings.filterwarnings("ignore")
    sys.modules.pop("config", None)                                  # kintaiyi and kinqimen both ship a top-level `config` helper
    sys.path.insert(0, os.path.dirname(kt.__file__))
    try:
        from kintaiyi import kintaiyi as KT
    finally:
        sys.path.remove(os.path.dirname(kt.__file__))
        sys.modules.pop("config", None)
    keys = {"局式": None, "太乙": "taiyi", "文昌": "wenchang", "始擊": "shiji", "計神": "jigod", "合神": "hegod", "定目": "dingmu", "主算": "home_cal", "客算": "away_cal",
            "主參": "home_vgen", "客參": "away_vgen", "四神": "four_god", "天乙": "sky_yi", "地乙": "earth_yi", "直符": "zhi_fu", "君基": "king_base", "臣基": "officer_base",
            "民基": "people_base", "帝符": "kingfu", "太尊": "taijun", "飛鳥": "flybird", "大游": "bigyo", "小游": "smallyo", "陽九": "yangjiu", "百六": "baliu", "八門值事": "door_on_duty"}
    n = 0
    for y in range(1950, 2051, 3):
        try:
            theirs = KT.Taiyi(y, 6, 15, 12, 0).pan(0, 0)
        except Exception:  # noqa: BLE001
            continue
        ours = T.year_board(date(y, 6, 15))
        n += 1
        assert theirs["局式"]["數"] == ours["ju"] and theirs["局式"]["積年數"] == ours["accumulated"], y
        for k, o in keys.items():
            if o is None:
                continue
            a = theirs[k][0] if isinstance(theirs[k], list) else theirs[k]
            assert str(a) == str(ours[o]), (y, k, a, ours[o])
        for k, o in (("主將", "home_general"), ("客將", "away_general")):
            if theirs[k] not in (0, None):                        # kintaiyi returns 0 for an empty 算; ours says 中宮 (5)
                assert theirs[k] == ours[o], (y, k)
    assert n >= 25
