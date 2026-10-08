"""奇門遁甲 basic tables (八門, 九宮 names) and a simplified day-of-year 局. The real 時家奇門 轉盤 起局 lives in fortune/qimen_ext.py.
"""

from __future__ import annotations

from datetime import date

from fortune.engines.bazi import bazi as B

MEN = ["休", "生", "傷", "杜", "景", "死", "驚", "開"]   # 八門 (洛書順)
AUSPICIOUS = {0, 1, 7}    # 休 生 開
ILL = {2, 5, 6}           # 傷 死 驚
# 九宮 (洛書) palace order for display
PALACES = ["坎一", "坤二", "震三", "巽四", "中五", "乾六", "兌七", "艮八", "離九"]


def _doy(d: date) -> int:
    return d.timetuple().tm_yday


def is_yang_dun(d: date) -> bool:
    """陽遁: 冬至→夏至 (順布); 陰遁: 夏至→冬至 (逆布). Approx by day-of-year."""
    doy = _doy(d)
    return doy >= 356 or doy < 172


def ju_number(d: date) -> int:
    """局數 1–9 — SIMPLIFIED (real uses 節氣三元). Deterministic from day-of-year."""
    return (_doy(d) % 9) + 1


def active_gate(d: date) -> int:
    """The 值使門 of the day — index into MEN. 陽遁 順行 / 陰遁 逆行 from the 局."""
    ju = ju_number(d)
    step = B._jdn(d.year, d.month, d.day) + (ju if is_yang_dun(d) else -ju)
    return step % 8


def qimen_readings(d: date) -> dict[str, float | str]:
    g = active_gate(d)
    regime = "auspicious_gate" if g in AUSPICIOUS else "ill_gate" if g in ILL else "neutral_gate"
    return {
        "qimen_regime": regime,
        "dun": "陽遁" if is_yang_dun(d) else "陰遁",
        "ju": f"{ju_number(d)}局",
        "active_gate": MEN[g] + "門",
        "gate_class": "三吉門" if g in AUSPICIOUS else "凶門" if g in ILL else "平門",
    }


def readings_block(r: dict[str, float | str]) -> str:
    order = ["qimen_regime", "dun", "ju", "active_gate", "gate_class"]
    return "\n".join(f"- {k}: {r[k]}" for k in order if k in r)


def gate_layout(d: date) -> list[dict]:
    """八門 distributed over the 8 outer 九宮 palaces (for display)."""
    ju = ju_number(d)
    forward = is_yang_dun(d)
    outer = [0, 1, 2, 3, 5, 6, 7, 8]   # 九宮 indices minus 中五
    out = []
    for i, pi in enumerate(outer):
        gi = ((i + ju) if forward else (i - ju)) % 8
        out.append({"palace": PALACES[pi], "gate": MEN[gi] + "門",
                    "cls": "吉" if gi in AUSPICIOUS else "凶" if gi in ILL else "平"})
    return out


def reasoning_chain(d_natal: date, as_of: date) -> list[str]:
    r = qimen_readings(as_of)
    return [
        f"起局（上市 {d_natal.isoformat()} 為命局；流日 {as_of.isoformat()} 起盤，簡化節氣三元）。",
        f"遁：{r['dun']}；局：{r['ju']}（{'順布' if is_yang_dun(as_of) else '逆布'}八門九宮）。",
        f"值使門：{r['active_gate']}（{r['gate_class']}）。三吉門＝開/休/生，凶門＝傷/死/驚。",
    ]
