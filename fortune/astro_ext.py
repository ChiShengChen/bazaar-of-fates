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


def _ramc_eps_phi(birth: BirthInput):
    """(RAMC deg, obliquity rad, latitude rad) for the birth moment, or None."""
    if not has_birth_geometry(birth):
        return None
    obs = ephem.Observer()
    obs.lat = str(birth.latitude)
    obs.lon = str(birth.longitude)
    obs.date = ephem.Date(_utc(birth))
    ramc = math.degrees(float(obs.sidereal_time())) % 360.0
    jd = float(obs.date) + 2415020.0
    return ramc, math.radians(_obliquity_deg(jd)), math.radians(float(birth.latitude))


def mc_lon(birth: BirthInput) -> float | None:
    """Ecliptic longitude of the Midheaven (the meridian ∩ ecliptic)."""
    g = _ramc_eps_phi(birth)
    if g is None:
        return None
    ramc, eps, _phi = g
    r = math.radians(ramc)
    return round(math.degrees(math.atan2(math.sin(r), math.cos(r) * math.cos(eps))) % 360.0, 2)


def _lon_from_ra(ra_deg: float, eps: float) -> float:
    """Ecliptic longitude on the ecliptic (β=0) whose right ascension is ra."""
    r = math.radians(ra_deg)
    return math.degrees(math.atan2(math.sin(r), math.cos(r) * math.cos(eps))) % 360.0


def _placidus_cusp(ramc: float, eps: float, phi: float, offset: float, frac: float, from_ic: bool) -> float:
    """One Placidus intermediate cusp by the semi-arc method (iterate on the cusp's
    own declination). 11/12 measure a fraction of the semi-diurnal arc east of the MC;
    2/3 measure a fraction of the semi-nocturnal arc back from the IC."""
    lam = (ramc + offset) % 360.0                       # initial guess
    for _ in range(60):
        decl = math.asin(math.sin(eps) * math.sin(math.radians(lam)))
        x = math.tan(phi) * math.tan(decl)
        x = max(-1.0, min(1.0, x))                       # clamp near the poles
        ad = math.degrees(math.asin(x))                 # ascensional difference
        if from_ic:
            ra = (ramc + 180.0) - frac * (90.0 - ad)    # cusps 2, 3
        else:
            ra = ramc + frac * (90.0 + ad)              # cusps 11, 12
        new = _lon_from_ra(ra, eps)
        if abs((new - lam + 180.0) % 360.0 - 180.0) < 1e-7:
            lam = new
            break
        lam = new
    return lam % 360.0


def placidus_houses(birth: BirthInput) -> list[dict] | None:
    """12 Placidus cusps. Cusp 1 == ascendant and cusp 10 == MC by construction.
    Undefined inside the polar circles → returns None (caller falls back to whole-sign)."""
    g = _ramc_eps_phi(birth)
    if g is None:
        return None
    ramc, eps, phi = g
    if abs(math.degrees(phi)) > 66.0:                   # Placidus breaks down past the polar circle
        return None
    asc = ascendant_lon(birth)
    mc = mc_lon(birth)
    if asc is None or mc is None:
        return None
    c11 = _placidus_cusp(ramc, eps, phi, 30.0, 1.0 / 3.0, from_ic=False)
    c12 = _placidus_cusp(ramc, eps, phi, 60.0, 2.0 / 3.0, from_ic=False)
    c2 = _placidus_cusp(ramc, eps, phi, 120.0, 2.0 / 3.0, from_ic=True)
    c3 = _placidus_cusp(ramc, eps, phi, 150.0, 1.0 / 3.0, from_ic=True)
    lons = [asc, c2, c3, (mc + 180.0) % 360.0, (c11 + 180.0) % 360.0, (c12 + 180.0) % 360.0,
            (asc + 180.0) % 360.0, (c2 + 180.0) % 360.0, (c3 + 180.0) % 360.0, mc, c11, c12]
    return [{"house": i + 1, "longitude": round(lon, 2), "sign": sign_of(lon), "sign_zh": sign_zh(lon)}
            for i, lon in enumerate(lons)]


def house_of_cusps(planet_lon: float, cusps: list[dict]) -> int:
    """House number a planet falls in, given 12 ecliptic cusp longitudes (any system)."""
    lons = [c["longitude"] for c in cusps]
    for i in range(12):
        a, b = lons[i], lons[(i + 1) % 12]
        span = (b - a) % 360.0
        if (planet_lon - a) % 360.0 < span:
            return i + 1
    return 1


def _asc_at(ramc_deg: float, eps: float, phi: float) -> float:
    """Ascendant longitude for an arbitrary RAMC (used by Koch's shifted-meridian cusps)."""
    r = math.radians(ramc_deg)
    asc = math.degrees(math.atan2(math.cos(r),
                                  -(math.sin(r) * math.cos(eps) + math.tan(phi) * math.sin(eps)))) % 360.0
    if not _is_eastern(asc, ramc_deg % 360.0, math.degrees(eps)):
        asc = (asc + 180.0) % 360.0
    return asc


def _cusp_row(lon: float, house: int) -> dict:
    return {"house": house, "longitude": round(lon % 360.0, 2), "sign": sign_of(lon), "sign_zh": sign_zh(lon)}


def equal_houses(asc_lon: float) -> list[dict]:
    """Equal houses: every cusp is exactly 30° from the ascendant degree."""
    return [_cusp_row((asc_lon + 30.0 * i) % 360.0, i + 1) for i in range(12)]


def koch_houses(birth: BirthInput) -> list[dict] | None:
    """Koch (Geburtsort) houses. Cusp 1 == ascendant, cusp 10 == MC; the four
    intermediate cusps trisect the ascendant's diurnal/nocturnal semi-arc in RA.
    Undefined past the polar circle → None."""
    g = _ramc_eps_phi(birth)
    if g is None:
        return None
    ramc, eps, phi = g
    if abs(math.degrees(phi)) > 66.0:
        return None
    asc, mc = ascendant_lon(birth), mc_lon(birth)
    if asc is None or mc is None:
        return None
    # Koch trisects the Asc→MC arc in sidereal time; the step is a third of the MC's
    # semi-diurnal arc: a = (90 + AD_mc)/3, AD_mc = ascensional difference of the MC.
    decl_mc = math.asin(math.sin(eps) * math.sin(math.radians(mc)))
    ad_mc = math.degrees(math.asin(max(-1.0, min(1.0, math.tan(phi) * math.tan(decl_mc)))))
    a = (90.0 + ad_mc) / 3.0
    c11 = _asc_at(ramc - 2.0 * a, eps, phi)
    c12 = _asc_at(ramc - 1.0 * a, eps, phi)
    c2 = _asc_at(ramc + 1.0 * a, eps, phi)
    c3 = _asc_at(ramc + 2.0 * a, eps, phi)
    lons = [asc, c2, c3, (mc + 180.0) % 360.0, (c11 + 180.0) % 360.0, (c12 + 180.0) % 360.0,
            (asc + 180.0) % 360.0, (c2 + 180.0) % 360.0, (c3 + 180.0) % 360.0, mc, c11, c12]
    return [_cusp_row(lon, i + 1) for i, lon in enumerate(lons)]


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


def ascendant_block(birth: BirthInput, *, ayanamsa: float = 0.0,
                    house_system: str = "whole_sign") -> dict | None:
    """Uniform ascendant payload for the Chart.ascendant field.
    `ayanamsa` > 0 gives the sidereal (Jyotiṣa) ascendant; 0 = tropical (Western).
    `house_system`: "whole_sign" (default) or "placidus" (tropical only; falls back
    to whole-sign past the polar circle)."""
    trop = ascendant_lon(birth)
    if trop is None:
        return None
    lon = (trop - ayanamsa) % 360.0

    used = "whole_sign"
    houses = whole_sign_houses(lon)
    if house_system == "equal":
        houses, used = equal_houses(lon), "equal"
    elif house_system in ("placidus", "koch") and ayanamsa == 0.0:   # quadrant systems: tropical only
        quad = placidus_houses(birth) if house_system == "placidus" else koch_houses(birth)
        if quad is not None:
            houses, used = quad, house_system

    block = {
        "longitude": round(lon, 2),
        "sign": sign_of(lon),
        "sign_zh": sign_zh(lon),
        "house_system": used,
        "sidereal": ayanamsa > 0,
        "houses": houses,
    }
    if used in ("placidus", "koch"):
        block["mc"] = mc_lon(birth)
    return block
