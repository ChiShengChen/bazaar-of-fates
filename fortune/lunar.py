"""農曆 conversion with the most reliable backend available.

lunardate (our original dependency) has three wrong month lengths — 1933 閏五月, 1954 and 1978 — that
shift every 紫微/梅花/六爻/稱骨 cast in those 30-day windows by one day. 壽星萬年曆 (sxtwl, C++, optional)
and lunar-python (pure Python, a core dependency) agree with each other and with the published
almanacs, so: sxtwl → lunar-python → lunardate.
"""

from __future__ import annotations

from datetime import date

try:
    import sxtwl as _sx
except Exception:  # noqa: BLE001
    _sx = None
try:
    from lunar_python import Lunar as _LPLunar, Solar as _LPSolar
except Exception:  # noqa: BLE001
    _LPSolar = _LPLunar = None
from lunardate import LunarDate as _LD

BACKEND = "sxtwl" if _sx else "lunar-python" if _LPSolar else "lunardate"


def to_lunar(d: date) -> tuple[int, int, int, bool]:
    """Solar date → (lunar year, month, day, is_leap_month)."""
    if _sx:
        x = _sx.fromSolar(d.year, d.month, d.day)
        return x.getLunarYear(), x.getLunarMonth(), x.getLunarDay(), bool(x.isLunarLeap())
    if _LPSolar:
        l = _LPSolar.fromYmd(d.year, d.month, d.day).getLunar()
        return l.getYear(), abs(l.getMonth()), l.getDay(), l.getMonth() < 0
    l = _LD.from_solar_date(d.year, d.month, d.day)
    return l.year, l.month, l.day, bool(l.is_leap_month)


def to_solar(year: int, month: int, day: int, leap: bool = False) -> date:
    """Lunar (year, month, day, leap) → solar date. Raises ValueError when the day does not exist."""
    if _sx:
        x = _sx.fromLunar(year, month, day, leap)
        out = date(x.getSolarYear(), x.getSolarMonth(), x.getSolarDay())
    elif _LPLunar:
        s = _LPLunar.fromYmd(year, -month if leap else month, day).getSolar()
        out = date(s.getYear(), s.getMonth(), s.getDay())
    else:
        out = _LD(year, month, day, leap).to_solar_date()
    if to_lunar(out) != (year, month, day, leap):          # sxtwl rolls a non-existent 三十 into the next month
        raise ValueError(f"lunar date does not exist: {year}-{month}-{day}{' leap' if leap else ''}")
    return out
