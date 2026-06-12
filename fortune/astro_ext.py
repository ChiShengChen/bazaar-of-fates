"""Ascendant / houses — the place-&-time-aware layer the synced engines don't carry.

The monorepo engines compute planetary longitudes from the *date* alone (a stock has
no birth time or birthplace). Real fortune-telling needs the **ascendant** (rising
degree) and **houses**, which depend on the exact birth moment AND latitude/longitude.
This native module adds that on top of `ephem`, shared by astrology · qizheng · jyotish.
It is NOT synced — `sync_from_main.sh` never touches it.

上升點與宮位 — 母 repo 引擎只用日期算行星經度（股票沒有時辰、出生地）。真正算命需要
上升（命度）與十二宮，取決於精確的出生時刻與經緯度。此原生模組以 ephem 補上，三系共用。
"""

from __future__ import annotations

import math
from datetime import timedelta

import ephem

from fortune.birth import BirthInput

_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
          "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
_SIGNS_ZH = ["牡羊", "金牛", "雙子", "巨蟹", "獅子", "處女",
             "天秤", "天蠍", "射手", "摩羯", "水瓶", "雙魚"]


def sign_of(lon: float) -> str:
    return _SIGNS[int(lon // 30) % 12]


def sign_zh(lon: float) -> str:
    return _SIGNS_ZH[int(lon // 30) % 12]


def has_birth_geometry(birth: BirthInput) -> bool:
    """True iff we have the time-of-day AND a birthplace — required for the ascendant."""
    return birth.birth_time is not None and birth.latitude is not None and birth.longitude is not None


def _utc(birth: BirthInput):
    """Local naive birth datetime → UTC, using the carried tz offset."""
    return birth.dt - timedelta(hours=birth.tz_offset_hours)


def _obliquity_deg(jd: float) -> float:
    """Mean obliquity of the ecliptic (Laskar/Meeus low-order), degrees."""
    t = (jd - 2451545.0) / 36525.0
    return 23.439291 - 0.0130042 * t - 1.64e-7 * t * t + 5.04e-7 * t ** 3


def ascendant_lon(birth: BirthInput) -> float | None:
    """Tropical ecliptic longitude of the ascendant, or None if time/place is missing.

    RAMC = local apparent sidereal time (ephem, longitude-aware); the rising degree is
        λ = atan2( cos RAMC , −(sin RAMC·cos ε + tan φ·sin ε) )
    rotated into the eastern-horizon quadrant.
    """
    if not has_birth_geometry(birth):
        return None
    obs = ephem.Observer()
    obs.lat = str(birth.latitude)
    obs.lon = str(birth.longitude)
    obs.date = ephem.Date(_utc(birth))
    ramc = float(obs.sidereal_time())                       # radians, local apparent
    jd = float(obs.date) + 2415020.0                        # ephem epoch → Julian Date
    eps = math.radians(_obliquity_deg(jd))
    phi = math.radians(float(birth.latitude))
    asc = math.atan2(math.cos(ramc),
                     -(math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps)))
    asc_deg = math.degrees(asc) % 360.0
    # The atan2 branch can land on the descendant; the ascendant is the point whose
    # RA is within 90°–270° of the RAMC (rising in the east). Flip if it's the wrong one.
    if not _is_eastern(asc_deg, math.degrees(ramc) % 360.0, math.degrees(eps)):
        asc_deg = (asc_deg + 180.0) % 360.0
    return round(asc_deg, 2)


def _is_eastern(lambda_deg: float, ramc_deg: float, eps_deg: float) -> bool:
    """Is ecliptic longitude λ on the eastern (rising) side of the meridian?
    Convert λ to right ascension and check it leads the RAMC by 0–180°."""
    lam = math.radians(lambda_deg)
    eps = math.radians(eps_deg)
    ra = math.degrees(math.atan2(math.sin(lam) * math.cos(eps), math.cos(lam))) % 360.0
    return 0.0 < (ra - ramc_deg) % 360.0 < 180.0


def whole_sign_houses(asc_lon: float) -> list[dict]:
    """12 whole-sign houses: house 1 = the ascendant's whole sign, then sequential signs."""
    asc_sign = int(asc_lon // 30) % 12
    houses = []
    for h in range(12):
        s = (asc_sign + h) % 12
        houses.append({"house": h + 1, "sign": _SIGNS[s], "sign_zh": _SIGNS_ZH[s], "sign_index": s})
    return houses


def house_of(planet_lon: float, asc_lon: float) -> int:
    """Whole-sign house number (1–12) a planet falls in."""
    return ((int(planet_lon // 30) - int(asc_lon // 30)) % 12) + 1


def ascendant_block(birth: BirthInput, *, ayanamsa: float = 0.0) -> dict | None:
    """Uniform ascendant payload for the Chart.ascendant field.
    `ayanamsa` > 0 gives the sidereal (Jyotiṣa) ascendant; 0 = tropical (Western)."""
    trop = ascendant_lon(birth)
    if trop is None:
        return None
    lon = (trop - ayanamsa) % 360.0
    return {
        "longitude": round(lon, 2),
        "sign": sign_of(lon),
        "sign_zh": sign_zh(lon),
        "house_system": "whole_sign",
        "sidereal": ayanamsa > 0,
        "houses": whole_sign_houses(lon),
    }
