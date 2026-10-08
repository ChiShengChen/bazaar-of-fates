"""太乙神數 simplified model: 積年 from a nominal 上元, 太乙 palace (24 years per palace, 八宮), 主算/客算.
"""

from __future__ import annotations

from datetime import date

from fortune.engines.bazi import bazi as B

# 太乙上元積年 base (traditional order of magnitude; exact 上元 varies by school — simplified).
_SHANGYUAN = 1936557
PALACES = ["乾", "離", "艮", "震", "巽", "坤", "兌", "坎"]   # 八宮 (太乙不入中宮)


def accumulated_years(d: date) -> int:
    return _SHANGYUAN + B._solar_year(d)


def taiyi_palace(d: date) -> str:
    """太乙每 24 年遷一宮，循八宮 (不入中五)."""
    return PALACES[(accumulated_years(d) // 24) % 8]


def host_guest(d: date) -> tuple[int, int]:
    """主算 (host) / 客算 (guest) — simplified deterministic counts from 積年 + 流年."""
    acc = accumulated_years(d)
    ly = B._solar_year(d)
    host = (acc + ly) % 360
    guest = (acc * 3 + ly * 2 + 30) % 360
    return host, guest


def host_wins(d: date) -> bool:
    h, g = host_guest(d)
    return h >= g


def taiyi_readings(d: date) -> dict[str, float | str]:
    h, g = host_guest(d)
    return {
        "taiyi_regime": "host_prevails" if h >= g else "guest_prevails",
        "accumulated_years": float(accumulated_years(d)),
        "taiyi_palace": taiyi_palace(d) + "宮",
        "host_count": float(h),
        "guest_count": float(g),
        "verdict": "主勝" if h >= g else "客勝",
    }


def readings_block(r: dict[str, float | str]) -> str:
    order = ["taiyi_regime", "accumulated_years", "taiyi_palace", "host_count", "guest_count", "verdict"]
    return "\n".join(f"- {k}: {r[k]}" for k in order if k in r)


def reasoning_chain(d_natal: date, as_of: date) -> list[str]:
    r = taiyi_readings(as_of)
    return [
        f"積年（上市 {d_natal.isoformat()} 命盤；流年 {B._solar_year(as_of)} 推算，簡化上元）。",
        f"太乙積年 ＝ {int(r['accumulated_years'])}，太乙臨 {r['taiyi_palace']}（24 年遷一宮）。",
        f"主算 ＝ {int(r['host_count'])}、客算 ＝ {int(r['guest_count'])} → 斷「{r['verdict']}」。",
    ]
