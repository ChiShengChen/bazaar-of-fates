"""鐵板神數 stand-in: 太玄數 of each 干支, 命數 = Σ over the four pillars, verse number and 吉/平/凶 verdict.
The real 條文 system has no public algorithm; this is an honest deterministic substitute.
"""

from __future__ import annotations

from datetime import date

from fortune.engines.bazi import bazi as B   # reuse the 干支 calendar

# 太玄數 — 天干: 甲己9 乙庚8 丙辛7 丁壬6 戊癸5 ; 地支: 子午9 丑未8 寅申7 卯酉6 辰戌5 巳亥4
_STEM_TAIXUAN = [9, 8, 7, 6, 5, 9, 8, 7, 6, 5]
_BRANCH_TAIXUAN = [9, 8, 7, 6, 5, 4, 9, 8, 7, 6, 5, 4]
_VERDICT = ["吉", "平", "凶"]   # verse number mod 3


def _gz_number(stem: int, branch: int) -> int:
    return _STEM_TAIXUAN[stem] + _BRANCH_TAIXUAN[branch]


def ming_number(birth: date) -> int:
    """命數 (太極數) = Σ 太玄數 over the four natal 干支 pillars."""
    p = B.four_pillars(birth)
    return sum(_gz_number(p[k]["stem_idx"], p[k]["branch_idx"]) for k in ("year", "month", "day", "hour"))


def liunian_number(ming: int, d: date) -> int:
    s, b = B.year_pillar(d)
    return ming + _gz_number(s, b)


def liuyue_number(ming: int, d: date) -> int:
    s, b = B.month_pillar(d)
    return ming + _gz_number(s, b)


def verdict(verse_no: int) -> str:
    return _VERDICT[verse_no % 3]


def tieban_readings(birth: date, ming: int, as_of: date) -> dict[str, float | str]:
    vn = liunian_number(ming, as_of)
    v = verdict(vn)
    return {
        "tieban_regime": {"吉": "auspicious", "平": "neutral", "凶": "inauspicious"}[v],
        "ming_number": float(ming),
        "liunian_verse_no": float(vn),
        "liunian_verdict": v,
        "liunian_gua": "乾兌離震巽坎艮坤"[vn % 8],   # flavour: 流年's 八卦 by verse-no mod 8
    }


def readings_block(r: dict[str, float | str]) -> str:
    order = ["tieban_regime", "ming_number", "liunian_verse_no", "liunian_verdict", "liunian_gua"]
    return "\n".join(f"- {k}: {r[k]}" for k in order if k in r)


def reasoning_chain(birth: date, ming: int, as_of: date) -> list[str]:
    p = B.four_pillars(birth)
    gz = "、".join(f"{p[k]['gz']}({_gz_number(p[k]['stem_idx'], p[k]['branch_idx'])})" for k in ("year", "month", "day", "hour"))
    vn = liunian_number(ming, as_of)
    return [
        f"起數（上市日，時柱以開盤 09:30＝巳時）：四柱 {gz}，各取太玄數。",
        f"命數（太極數）＝四柱太玄數之和＝{ming}。",
        f"流年起例：命數 + 流年干支太玄數 ＝ 條文 #{vn}。",
        f"斷例：條文 #{vn} → 「{verdict(vn)}」（編號 mod 3）；流年卦象 {'乾兌離震巽坎艮坤'[vn % 8]}。",
    ]
