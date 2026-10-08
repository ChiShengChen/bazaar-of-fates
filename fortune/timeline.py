"""Life timelines / 大運・流年 — the time axis the point-in-time chart doesn't show.

Native module (not synced). Builds reproducible period sequences from the synced
engine primitives:
  • jyotish — Vimśottarī Mahādaśā (120-yr cycle of 9 planetary lords)
  • bazi    — 大運 (10-year luck pillars, direction by 年干陰陽 × gender) + 流年 nature
  • ziwei   — 流年四化 for the years ahead
Systems without a natural period concept return an empty timeline.
"""

from __future__ import annotations

from datetime import date, timedelta

import ephem

from fortune.birth import BirthInput
from fortune.engines.astrology import astro as ASTRO
from fortune.engines.bazi import bazi as BZ
from fortune.engines.jyotish import jyotish as JY
from fortune.engines.ziwei import ziwei as ZW
from fortune.schemas import Period, Timeline

_DAYS_PER_YEAR = 365.2425


def _is_male(birth: BirthInput) -> bool | None:
    g = (birth.gender or "").strip().lower()
    if g in {"male", "m", "男", "boy", "man"}:
        return True
    if g in {"female", "f", "女", "girl", "woman"}:
        return False
    return None


def _today() -> date:
    return date.today()


# --- Jyotiṣa Vimśottarī Mahādaśā ------------------------------------------------

def jyotish_dasha(birth: BirthInput, count: int = 9) -> Timeline:
    n, frac = JY.natal_nakshatra(birth.as_date)
    start_idx = n % 9
    today = _today()
    periods: list[Period] = []
    cursor = birth.as_date
    for i in range(count):
        lord = JY.DASHA_LORDS[(start_idx + i) % 9]
        full = JY.DASHA_YEARS[(start_idx + i) % 9]
        years = full * (1.0 - frac) if i == 0 else float(full)
        end = cursor + timedelta(days=years * _DAYS_PER_YEAR)
        nature = "benefic" if lord in JY.BENEFIC else "malefic"
        periods.append(Period(
            index=i, label=lord, detail=f"{years:.1f} yr daśā",
            start=cursor.isoformat(), end=end.isoformat(),
            start_age=round((cursor - birth.as_date).days / _DAYS_PER_YEAR, 1),
            nature=nature, current=cursor <= today < end,
        ))
        cursor = end
    return Timeline(system="jyotish", system_en="Jyotiṣa · Vedic Astrology", system_zh="Jyotiṣa（吠陀占星）",
                    kind="mahadasha", kind_label="Vimśottarī Mahādaśā · 大運（120年九曜）", periods=periods)


# --- BaZi 大運 (10-year luck pillars) ------------------------------------------

def bazi_dayun(birth: BirthInput, count: int = 9) -> Timeline:
    """大運 from the exact-節氣 起運 in fortune/bazi_ext (三日折一年, to the hour)."""
    from fortune import bazi_ext as X

    full = X.full_chart(birth, dayun_count=count, today=_today())
    qy = full["qi_yun"]
    note = ""
    if full["gender_assumed"]:
        note = "性別未填，大運方向以「陽年順、陰年逆」預設男命 / gender unset → assumed male"
    periods: list[Period] = []
    for d in full["dayun"]:
        periods.append(Period(
            index=d["index"], label=d["gz"],
            detail=f"{d['stem_god']}・{d['changsheng']}・age {d['start_age']}–{d['start_age'] + 10}",
            start=f"{d['start_year']}-01-01", end=f"{d['end_year']}-12-31", start_age=float(d["start_age"]),
            nature=d["nature"], current=d["current"],
        ))
    return Timeline(system="bazi", system_en="BaZi · Four Pillars", system_zh="八字（四柱）",
                    kind="dayun",
                    kind_label=f"大運 · Luck Pillars（{'順行' if qy['forward'] else '逆行'}・{qy['text']}）",
                    periods=periods, note=note)


# --- 紫微 流年四化 --------------------------------------------------------------

def ziwei_liunian(birth: BirthInput, count: int = 12) -> Timeline:
    today = _today()
    y0 = today.year
    periods: list[Period] = []
    for i in range(count):
        yr = y0 + i
        anchor = date(yr, 6, 1)                          # mid-year, safely past 立春
        stem, mut = ZW.liunian_sihua(anchor)
        detail = "、".join(f"{mut[j]}化{ZW.HUA[j]}" for j in range(4))
        periods.append(Period(
            index=i, label=f"{yr} {stem}年", detail=detail,
            start=date(yr, 1, 1).isoformat(), end=date(yr, 12, 31).isoformat(),
            start_age=round((date(yr, 1, 1) - birth.as_date).days / _DAYS_PER_YEAR, 1),
            nature="neutral", current=yr == today.year,
        ))
    return Timeline(system="ziwei", system_en="Zi Wei Dou Shu · Purple Star", system_zh="紫微斗數",
                    kind="liunian_sihua", kind_label="流年四化 · Annual Transformations", periods=periods)


# --- 西洋占星 planet returns (life milestones) ---------------------------------

_RETURNS = {"Jupiter": (ephem.Jupiter, 11.862, "benefic"),
            "Saturn": (ephem.Saturn, 29.457, "malefic")}


def _return_dates(natal_lon: float, body_cls, birth_date: date, period_years: float, n: int) -> list[date]:
    """Dates of the first n returns of `body` to `natal_lon` after birth (transit conjunct natal)."""
    out = []
    for k in range(1, n + 1):
        approx = birth_date + timedelta(days=int(period_years * k * _DAYS_PER_YEAR))
        best = (approx, 999.0)
        for off in range(-400, 401, 5):                   # coarse, then fine
            dd = approx + timedelta(days=off)
            sep = ASTRO._separation(ASTRO._lon(body_cls, dd), natal_lon)
            if sep < best[1]:
                best = (dd, sep)
        d0 = best[0]
        for off in range(-5, 6):
            dd = d0 + timedelta(days=off)
            sep = ASTRO._separation(ASTRO._lon(body_cls, dd), natal_lon)
            if sep < best[1]:
                best = (dd, sep)
        out.append(best[0])
    return out


def astrology_returns(birth: BirthInput) -> Timeline:
    """Jupiter (~12 yr) & Saturn (~29.5 yr) returns over the lifespan — the classic
    'Saturn return at ~29' milestones."""
    natal = {b: lon for (b, lon, _s, _r) in ASTRO.chart_for(birth.as_date)}
    today = _today()
    periods: list[Period] = []
    for body, (cls, per, nature) in _RETURNS.items():
        n = int(95 / per)
        for k, rd in enumerate(_return_dates(natal[body], cls, birth.as_date, per, n), start=1):
            age = round((rd - birth.as_date).days / _DAYS_PER_YEAR, 1)
            periods.append(Period(
                index=0, label=f"{body} return #{k}", detail=f"≈ age {age:.0f}",
                start=rd.isoformat(), end="", start_age=age, nature=nature,
                current=abs((rd - today).days) <= 183))
    periods.sort(key=lambda p: p.start)
    for i, p in enumerate(periods):
        p.index = i
    return Timeline(system="astrology", system_en="Western Astrology", system_zh="西洋占星",
                    kind="planet_returns", kind_label="Planet returns 行星回歸（木12年・土29.5年）",
                    periods=periods)


_BUILDERS = {"jyotish": jyotish_dasha, "bazi": bazi_dayun, "ziwei": ziwei_liunian,
             "astrology": astrology_returns}


def timeline(system: str, birth: BirthInput) -> Timeline:
    """Life timeline for `system`, or an empty (kind='none') timeline if it has none."""
    builder = _BUILDERS.get(system)
    if builder is None:
        from fortune.casting import REGISTRY
        zh = REGISTRY.get(system, ("", system, ""))[1]
        return Timeline(system=system, system_zh=zh, kind="none",
                        kind_label="— no life-timeline for this system 此系統無大運/流年時間軸 —")
    return builder(birth)


def has_timeline(system: str) -> bool:
    return system in _BUILDERS
