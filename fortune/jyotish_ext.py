"""Jyotiṣa at the exact birth instant / 吠陀占星・精確時刻版.

Native module (NOT synced). The synced engine computes the natal Moon from the calendar
date only (midnight UT, J2000 frame). The Moon moves ~13°/day — one full nakṣatra — so a
quarter of births land in the wrong nakṣatra and therefore start the Vimśottarī daśā
sequence from the wrong lord. This module recomputes the grahas, nakṣatra and daśā from
the birth instant in the true-equinox-of-date frame (fortune.astro_ext), minus the Lahiri
ayanāṃśa. The engine's tables (lords, years, benefics, names) are reused as-is.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import ephem

from fortune import astro_ext as AX
from fortune.engines.jyotish import jyotish as JY

_NAK = 360.0 / 27.0
_DAYS_PER_YEAR = 365.2425


def _jd(dt: datetime) -> float:
    return ephem.julian_date(ephem.Date(dt))


def ayanamsa_at(dt_utc: datetime) -> float:
    """Lahiri ayanāṃśa (≈ 23.853° at J2000, +50.27″/yr) at an instant."""
    return 23.853 + (_jd(dt_utc) - 2451545.0) / 365.25 * (50.2719 / 3600.0)


def rahu_at(dt_utc: datetime) -> float:
    """Mean ascending node (tropical, of date)."""
    t = (_jd(dt_utc) - 2451545.0) / 36525.0
    return (125.0445 - 1934.1363 * t) % 360.0


def sidereal_positions(dt_utc: datetime) -> list[dict]:
    """[{graha, sidereal_lon, rashi, retrograde}] for the 9 grahas at an instant."""
    ayan = ayanamsa_at(dt_utc)
    rows = []
    for name, cls in JY.GRAHAS.items():
        lon = (AX.lon_of_date(cls, dt_utc) - ayan) % 360.0
        retro = name not in ("Sun", "Moon") and AX.is_retrograde_at(cls, dt_utc)
        rows.append({"graha": name, "sidereal_lon": round(lon, 2), "rashi": JY.RASHI[int(lon // 30) % 12], "retrograde": retro})
    node = rahu_at(dt_utc)
    for name, lon in (("Rahu", (node - ayan) % 360.0), ("Ketu", (node + 180.0 - ayan) % 360.0)):
        rows.append({"graha": name, "sidereal_lon": round(lon, 2), "rashi": JY.RASHI[int(lon // 30) % 12], "retrograde": True})
    return rows


def natal_nakshatra(dt_utc: datetime) -> tuple[int, float]:
    """(nakṣatra index 0–26, fraction elapsed) of the Moon at the birth instant."""
    moon = (AX.lon_of_date(ephem.Moon, dt_utc) - ayanamsa_at(dt_utc)) % 360.0
    return int(moon // _NAK) % 27, (moon % _NAK) / _NAK


def dasha_periods(birth_utc: datetime, count: int = 9) -> list[dict]:
    """Vimśottarī Mahādaśā sequence from birth: [{lord, years, start, end, nature}] (dates)."""
    n, frac = natal_nakshatra(birth_utc)
    start_idx = n % 9
    cursor = birth_utc.date()
    out = []
    for i in range(count):
        k = (start_idx + i) % 9
        lord, full = JY.DASHA_LORDS[k], JY.DASHA_YEARS[k]
        years = full * (1.0 - frac) if i == 0 else float(full)
        end = cursor + timedelta(days=years * _DAYS_PER_YEAR)
        out.append({"lord": lord, "years": years, "start": cursor, "end": end,
                    "nature": "benefic" if lord in JY.BENEFIC else "malefic"})
        cursor = end
    return out


def mahadasha_lord(birth_utc: datetime, on: date) -> str:
    """The Mahādaśā lord active on `on`."""
    for p in dasha_periods(birth_utc, count=12):
        if p["start"] <= on < p["end"]:
            return p["lord"]
    return dasha_periods(birth_utc, count=1)[0]["lord"]
