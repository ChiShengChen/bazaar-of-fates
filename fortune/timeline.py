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

from fortune.birth import BirthInput
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

_TERM_DATES = BZ._MONTH_TERMS   # (month, day, branch_idx, label)


def _nearest_term_days(d: date, forward: bool) -> int:
    """Approx days from d to the next (forward) / previous (backward) 節 boundary."""
    cands: list[date] = []
    for yr in (d.year - 1, d.year, d.year + 1):
        for (mo, day, _bi, _t) in _TERM_DATES:
            try:
                cands.append(date(yr, mo, day))
            except ValueError:
                pass
    if forward:
        nxt = min((c for c in cands if c > d), default=d + timedelta(days=15))
        return (nxt - d).days
    prv = max((c for c in cands if c <= d), default=d - timedelta(days=15))
    return (d - prv).days


def bazi_dayun(birth: BirthInput, count: int = 8) -> Timeline:
    d = birth.as_date
    ys, _yb = BZ.year_pillar(d)
    ms, mb = BZ.month_pillar(d)
    year_yang = BZ.STEM_YINYANG[ys] == "陽"
    male = _is_male(birth)
    note = ""
    if male is None:
        male = True
        note = "性別未填，大運方向以「陽年順、陰年逆」預設男命 / gender unset → assumed male"
    forward = (year_yang and male) or (not year_yang and not male)   # 陽男陰女順, 陰男陽女逆

    start_age = round(_nearest_term_days(d, forward) / 3.0, 1)        # 三日折一年
    pillars = BZ.four_pillars(d, birth.hour)
    fav = set(BZ.strength_and_favourable(pillars)["favourable"])
    today = _today()

    periods: list[Period] = []
    for i in range(count):
        step = (i + 1) if forward else -(i + 1)
        s = (ms + step) % 10
        b = (mb + step) % 12
        elem = BZ.STEM_ELEM[s]
        age0 = start_age + 10 * i
        start_d = d + timedelta(days=age0 * _DAYS_PER_YEAR)
        end_d = d + timedelta(days=(age0 + 10) * _DAYS_PER_YEAR)
        nature = "favourable" if elem in fav else "unfavourable"
        periods.append(Period(
            index=i, label=BZ.STEMS[s] + BZ.BRANCHES[b],
            detail=f"{elem}・age {age0:.0f}–{age0 + 10:.0f}",
            start=start_d.isoformat(), end=end_d.isoformat(), start_age=age0,
            nature=nature, current=start_d <= today < end_d,
        ))
    return Timeline(system="bazi", system_en="BaZi · Four Pillars", system_zh="八字（四柱）",
                    kind="dayun", kind_label=f"大運 · Luck Pillars（{'順行' if forward else '逆行'}）",
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


_BUILDERS = {"jyotish": jyotish_dasha, "bazi": bazi_dayun, "ziwei": ziwei_liunian}


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
