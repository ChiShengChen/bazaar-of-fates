"""Birth input / 生辰輸入 — the one input the whole service takes.

Replaces the monorepo's "stock listing date": a person's birth moment (date +
time-of-day + optional birthplace). Time-of-day drives the 時柱 / Moon position;
birthplace (lat/lon) is what house-/ascendant-based systems (astrology, Jyotiṣa)
need — carried here so engines can use it as they grow into it.
取代母專案的「股票上市日」：一個人的出生時刻（日期＋時辰＋出生地）。
"""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator


class BirthInput(BaseModel):
    name: str | None = Field(default=None, description="Name, display only / 稱呼（可選）")
    birth_date: date = Field(..., description="Birth date / 出生日期")
    birth_time: time | None = Field(
        default=None, description="Birth time / 出生時刻（時辰）；unknown → noon 時柱以正午估算"
    )
    gender: str | None = Field(default=None, description="Gender / 性別（部分命理用神不同）")

    # birthplace — optional, needed for ascendant/house systems / 出生地，宮位系統需要
    place: str | None = Field(default=None, description="Birthplace name / 出生地名（顯示用）")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    tz_offset_hours: float = Field(default=8.0, description="Timezone offset / 出生地時區（東八區=+8；日光節約時間請加 1）")
    true_solar_time: bool = Field(
        default=False,
        description="Cast 干支 systems (八字/紫微/奇門/六壬…) on true solar time at the birthplace / 以出生地真太陽時排干支（需經度）",
    )

    @field_validator("birth_date")
    @classmethod
    def _supported_range(cls, v: date) -> date:
        # lunardate (農曆, used by 紫微/梅花/稱骨) covers 1900–2100; ephem and the 節氣 search are fine there too.
        if v.year < 1900 or v.year > 2099:
            raise ValueError("birth_date must be between 1900 and 2099 / 僅支援 1900–2099 年（農曆換算範圍）")
        return v

    @property
    def as_date(self) -> date:
        return self.birth_date

    @property
    def hour(self) -> int:
        """Clock hour 0–23; defaults to noon (12) when time-of-day is unknown."""
        return self.birth_time.hour if self.birth_time else 12

    @property
    def dt(self) -> datetime:
        t = self.birth_time or time(12, 0)
        return datetime.combine(self.birth_date, t)

    def label(self) -> str:
        who = self.name or "Querent 命主"
        when = self.birth_date.isoformat() + (
            f" {self.birth_time.strftime('%H:%M')}" if self.birth_time else " (time unknown 時辰未知)"
        )
        where = f" · {self.place}" if self.place else ""
        tst = " · 真太陽時" if self.true_solar_time and self.longitude is not None else ""
        return f"{who} · {when}{where}{tst}"
