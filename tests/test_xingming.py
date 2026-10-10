"""姓名學（熊崎式五格）：康熙筆畫、分姓名、流派開關、五格三才、八字連動、API / CLI / MCP."""

from datetime import date, time

import pytest

from fortune import casting
from fortune.birth import BirthInput
from fortune.casting import xingming as XM
from fortune.xingming.engine import NameInputError, Rules, analyze, char_strokes, element_of, split_name

# 康熙筆畫（部首還原原形）：常見姓氏與名字用字，逐字手算對照（來自課程版的驗證表）
KANGXI = dict(陳=16, 林=8, 黃=12, 張=11, 李=7, 王=4, 吳=7, 劉=15, 蔡=17, 楊=13, 許=11, 鄭=19, 謝=17, 洪=10, 郭=15, 邱=12, 曾=12, 廖=14, 賴=16,
              徐=10, 周=8, 葉=15, 蘇=22, 莊=13, 呂=7, 江=7, 何=7, 蕭=18, 羅=20, 高=10, 潘=16, 簡=18, 朱=6, 鍾=17, 彭=12, 游=13, 詹=13, 胡=11,
              施=9, 沈=8, 余=7, 盧=16, 梁=11, 趙=14, 顏=18, 柯=9, 翁=10, 魏=18, 孫=10, 范=11, 方=4, 宋=7, 鄧=19, 杜=7, 傅=12, 侯=9, 曹=11,
              薛=19, 丁=2, 卓=8, 馬=10, 阮=12, 董=15, 唐=10, 藍=20, 蔣=17, 石=5, 古=5, 紀=9, 姚=9, 連=14, 馮=12, 歐=15, 程=12, 湯=13, 田=5,
              康=11, 姜=9, 白=5, 汪=8, 鄒=17, 尤=4, 巫=7, 鐘=20, 黎=15, 龔=22, 嚴=20, 韓=17, 袁=10, 金=8, 童=12, 陸=16, 夏=10, 柳=9, 邵=12,
              錢=16, 伍=6, 倪=10, 溫=14, 于=3, 譚=19, 駱=16, 熊=14, 任=6, 甘=5, 秦=10, 顧=21, 毛=4,
              美=9, 華=14, 文=4, 明=8, 志=7, 偉=11, 怡=9, 婷=12, 雅=12, 俊=9, 宏=7, 家=10, 豪=14, 傑=12, 欣=8, 宇=6, 翔=12, 淑=12, 芬=10,
              玲=10, 珍=10, 建=9, 國=11, 榮=14, 嘉=14, 慧=15, 惠=12, 秀=7, 英=11, 麗=19, 玉=5, 蘭=23, 春=9, 雲=12, 鳳=14, 蓮=17, 德=15,
              龍=16, 博=12, 浩=11, 清=12, 海=11, 思=9, 琪=13, 瑜=14, 涵=12, 安=6, 心=4, 恩=10, 承=8, 祐=10, 福=14, 禎=14, 振=11, 哲=10)


@pytest.mark.parametrize("ch,want", sorted(KANGXI.items()))
def test_kangxi_strokes(ch, want):
    assert char_strokes(ch, "名", Rules())[0].strokes == want


def test_radical_restoration_and_switches():
    info, _ = char_strokes("陳", "姓", Rules())
    assert "阜" in info.how and "170.8" in info.how and info.modern == 10
    assert char_strokes("陳", "姓", Rules(stroke_basis="modern"))[0].strokes == 10
    assert char_strokes("四", "名", Rules())[0].strokes == 4 and char_strokes("四", "名", Rules(numeral_strokes="shape"))[0].strokes == 5
    info, warnings = char_strokes("张", "姓", Rules())
    assert info.strokes == 11 and info.traditional == "張" and warnings


def test_split_name_and_errors():
    assert split_name("陳美玲")[:2] == ("陳", "美玲") and split_name("歐陽娜娜")[:2] == ("歐陽", "娜娜")
    assert split_name("陳林 美玲")[:2] == ("陳林", "美玲") and split_name("張簡")[:2] == ("張", "簡")
    for bad in ("", "陳", "Amy Chen"):
        with pytest.raises(NameInputError):
            analyze(bad)
    assert [element_of(n) for n in range(1, 11)] == ["木", "木", "火", "火", "土", "土", "金", "金", "水", "水"]


def test_standard_case_chen_meiling():
    nc = analyze("陳美玲")
    g = nc.grids
    assert (g["天格"].number, g["人格"].number, g["地格"].number, g["外格"].number, g["總格"].number) == (17, 25, 19, 11, 35)
    assert g["人格"].element == "土" and g["人格"].luck == "吉" and nc.sancai == "金土水"
    off = analyze("陳美玲", Rules(jiashu="off"))
    assert off.grids["天格"].number == 16


def test_chart_with_bazi_link():
    b = BirthInput(full_name="陳美玲", birth_date=date(1990, 6, 15), birth_time=time(14, 30), gender="female")
    c = casting.cast("xingming", b)
    assert c.system == "xingming" and c.readings["人格"].startswith("25・土・吉") and c.readings["三才"].startswith("金土水")
    assert c.chart["bazi"]["favourable"] == ["土", "金"] and c.readings["人格對八字"] == "人格土：喜用"
    assert any("配八字" in line for line in c.reasoning_chain) and c.chart["grids"][1]["bazi"] == "喜用"
    assert "xingming" in {s["key"] for s in casting.systems()} and next(s for s in casting.systems() if s["key"] == "xingming")["needs_name"]
    assert "xingming" not in casting.REGISTRY                          # the 13-system loops are untouched


def test_name_from_birth_name_or_error():
    c = casting.cast("xingming", BirthInput(name="歐陽娜娜", birth_date=date(1990, 6, 15)))
    assert c.chart["surname"] == "歐陽"
    with pytest.raises(NameInputError):
        casting.cast("xingming", BirthInput(name="Mei", birth_date=date(1990, 6, 15)))
    alone = XM.build("林書豪")
    assert alone.chart["bazi"] is None and "未提供生辰" in alone.reasoning_chain[-1] and alone.subject == "林書豪"


def test_focus_and_reading():
    from fortune import focus as F
    from fortune.interpret import interpret
    c = casting.cast("xingming", BirthInput(full_name="陳美玲", birth_date=date(1990, 6, 15), birth_time=time(14, 30), gender="female"))
    fx = F.extract(c, "career")
    assert fx["verdict"] in ("favourable", "neutral", "unfavourable") and "成功運" in fx["facts"]["本題"]
    r = interpret(c, focus="這個名字適合創業嗎")
    assert r.interpretation and "人格" in r.interpretation


def test_api_name_and_cast():
    from fastapi.testclient import TestClient
    from fortune.api.main import app
    c = TestClient(app)
    r = c.post("/name", json={"full_name": "陳美玲", "birth": {"birth_date": "1990-06-15", "birth_time": "14:30", "gender": "female"}})
    assert r.status_code == 200 and r.json()["chart"]["sancai"] == "金土水" and r.json()["chart"]["bazi"]["favourable"] == ["土", "金"]
    r = c.post("/name", json={"full_name": "陳美玲", "jiashu": "off"})
    assert r.status_code == 200 and r.json()["chart"]["grids"][0]["number"] == 16 and r.json()["chart"]["bazi"] is None
    assert c.post("/name", json={"full_name": "Amy"}).status_code == 400
    r = c.post("/cast/xingming", json={"full_name": "陳美玲", "birth_date": "1990-06-15"})
    assert r.status_code == 200 and r.json()["system"] == "xingming"
    assert c.post("/cast/xingming", json={"birth_date": "1990-06-15"}).status_code == 422
    assert any(s["key"] == "xingming" for s in c.get("/systems").json())


def test_cli_and_mcp(capsys):
    from fortune.cli import main
    assert main(["xingming", "1990-06-15", "14:30", "--full-name", "陳美玲", "--gender", "female"]) == 0
    out = capsys.readouterr().out
    assert "人格" in out and "金土水" in out
    from fortune import mcp_server as M
    j = M.name("陳美玲", "1990-06-15", "14:30", "female")
    assert j["chart"]["grids"][1]["number"] == 25 and j["chart"]["bazi"]["favourable"] == ["土", "金"]
