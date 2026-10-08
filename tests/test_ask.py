"""問事 (ask): 奇門 / 六壬 time charts for the moment of a question, 梅花 numbers / text, 六爻 coins, 小六壬, and the surfaces."""

from datetime import datetime

import pytest

from fortune import ask as A
from fortune.engines.iching import iching as IC

AT = datetime(2026, 10, 10, 14, 30)


@pytest.mark.parametrize("system", list(A.SYSTEMS))
def test_every_system_answers_a_question(system):
    out = A.ask(system, "明天面試會順利嗎", at=AT, place="台北")
    assert out["system"] == system and out["topic"] == "career" and out["at"] == "2026-10-10T14:30"
    v = out["verdict"]
    assert v["verdict"] in ("favourable", "neutral", "unfavourable") and v["verdict_zh"] in "吉平凶"
    assert v["reasons"] and isinstance(v["facts"], dict) and out["chart"]["reasoning_chain"]
    assert out["chart"]["subject"].startswith("問事：明天面試會順利嗎")
    assert "interpretation" not in out


def test_qimen_identifies_person_matter_and_yong():
    out = A.ask("qimen", "這筆投資能不能做", at=AT)
    f = out["verdict"]["facts"]
    assert out["topic"] == "wealth" and f["用神"].startswith("生門")
    assert "落" in f["日干（求測人）"] and "落" in f["時干（所問之事）"]
    assert isinstance(f["吉方（三吉門）"], list) and len(f["吉方（三吉門）"]) == 3
    assert out["verdict"]["timing_hint"].startswith("應期參考")


def test_qimen_health_uses_tianrui_not_as_a_bad_star():
    out = A.ask("qimen", "身體檢查結果會好嗎", at=AT)
    assert out["topic"] == "health" and out["verdict"]["facts"]["用神"].startswith("天芮")
    assert not any("臨天芮（凶星）" in r for r in out["verdict"]["reasons"])


def test_liuren_topic_class_god():
    out = A.ask("liuren", "何時有正緣", at=AT)
    f = out["verdict"]["facts"]
    assert out["topic"] == "love" and "六合" in f["類神"]
    assert f["三傳"].count("（") == 3 and f["日旬空亡"] and len(f["日旬空亡"]) == 2


@pytest.mark.parametrize("numbers,upper,lower,moving", [
    ([3, 7, 9], "離", "艮", 3),          # 三數：上 3→離, 下 7→艮, 動 9 mod 6 = 3
    ([8, 16], "坤", "坤", 6),            # 雙數：8→坤, 16→坤, 動 24 mod 6 → 6
    ([1234], "震", "兌", 4),             # 單數：12→震(4), 34→兌(2), 動 46 mod 6 = 4
    ([5], "巽", "巽", 4),                  # 個位數：上下同卦, 動 (5+5) mod 6 = 4
])
def test_meihua_numbers(numbers, upper, lower, moving):
    d = A.meihua_numbers(numbers)
    assert (d["upper"], d["lower"], d["moving"]) == (upper, lower, moving)
    assert d["ben_name"] == IC.kingwen(upper, lower)[1]


def test_meihua_text_splits_fewer_first_and_adds_hour():
    d = A.meihua_numbers(text="明天面試順不順利", hour_branch=7)      # 8 chars → 4/4, 時 未=8 → 動 (4+4+8) mod 6 = 4
    assert d["numbers"]["input"] == [4, 4] and d["moving"] == 4
    d2 = A.meihua_numbers(text="他會回我嗎", hour_branch=0)            # 5 chars → 2 上 / 3 下, 時 子=1 → 動 6
    assert d2["numbers"]["input"] == [2, 3] and d2["upper"] == "兌" and d2["lower"] == "離" and d2["moving"] == 6
    with pytest.raises(ValueError):
        A.meihua_numbers(text="   ")
    with pytest.raises(ValueError):
        A.meihua_numbers([1, 2, 3, 4])


def test_ask_iching_numbers_vs_time():
    t = A.ask("iching", "他會回我嗎", at=AT)
    n = A.ask("iching", "他會回我嗎", at=AT, numbers=[3, 7, 9])
    x = A.ask("iching", "他會回我嗎", at=AT, text="他會回我嗎")
    assert t["method"] == "時間起卦" and n["method"] == "數字起卦" and x["method"] == "字占"
    assert n["chart"]["chart"]["hexagram"]["ben_name"] == "火山旅"
    assert "變卦" in " ".join(n["verdict"]["reasons"])


def test_liuyao_coins():
    g, moving_all, lines = A.liuyao_coins([7, 8, 9, 8, 6, 7], AT, 8.0)
    assert lines == [1, 0, 1, 0, 0, 1] and moving_all == [3, 5] and g["moving"] == 5
    assert any("亦動" in r["notes"] for r in g["lines"] if r["pos"] == 3)
    out = A.ask("liuyao", "合約能簽嗎", at=AT, coins=[7, 8, 9, 8, 6, 7])
    assert out["method"] == "金錢卦" and out["chart"]["chart"]["coins"] == [7, 8, 9, 8, 6, 7] and out["chart"]["chart"]["hexagram"]["changed"]
    still = A.ask("liuyao", "合約能簽嗎", at=AT, coins=[7, 8, 8, 8, 8, 7])
    assert still["chart"]["chart"]["hexagram"]["moving"] == 0 and "無動爻" in still["chart"]["summary"]
    with pytest.raises(ValueError):
        A.liuyao_coins([1, 2, 3, 4, 5, 6], AT, 8.0)


def test_liuyao_topic_yong_and_reading():
    out = A.ask("liuyao", "今年財運如何", at=AT, read=True)
    assert out["topic"] == "wealth" and out["verdict"]["facts"]["用神"] == ["妻財"]
    assert out["interpretation"] and "問事判斷" not in out["interpretation"][:40] or out["interpretation"]


def test_unknown_system():
    with pytest.raises(ValueError):
        A.ask("bazi", "x", at=AT)


def test_cli_ask(capsys):
    from fortune.cli import main
    assert main(["ask", "qimen", "明天面試會順利嗎", "--at", "2026-10-10T14:30", "--place", "台北"]) == 0
    out = capsys.readouterr().out
    assert "奇門遁甲問事" in out and "【斷】" in out and "吉方" in out
    assert main(["ask", "iching", "他會回我嗎", "--numbers", "3,7,9", "--at", "2026-10-10T14:30"]) == 0
    assert "火山旅" in capsys.readouterr().out
    assert main(["ask", "liuyao", "合約", "--coins", "7,8,9,8,6,7", "--at", "2026-10-10T14:30", "--json"]) == 0
    assert '"金錢卦"' in capsys.readouterr().out


def test_api_ask():
    from fastapi.testclient import TestClient
    from fortune.api.main import app
    c = TestClient(app)
    r = c.post("/ask/liuren", json={"question": "這筆投資能做嗎", "at": "2026-10-10T14:30", "place": "台北", "read": False})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["topic"] == "wealth" and j["verdict"]["verdict_zh"] in "吉平凶" and j["chart"]["system"] == "liuren"
    r = c.post("/ask/iching", json={"question": "他會回我嗎", "numbers": [3, 7, 9], "at": "2026-10-10T14:30", "read": False})
    assert r.status_code == 200 and r.json()["method"] == "數字起卦"
    assert c.post("/ask/liuyao", json={"question": "x", "coins": [1, 2, 3, 4, 5, 6], "read": False}).status_code == 400
    assert c.post("/ask/bazi", json={"question": "x"}).status_code == 404


def test_mcp_ask_tool():
    from fortune import mcp_server as M
    out = M.ask("xiaoliuren", "今天出門順嗎", at="2026-10-10T14:30")
    assert out["system"] == "xiaoliuren" and out["verdict"]["facts"]["課"]
