"""生辰輸入 — the one input the whole 算命 service takes.

Replaces the monorepo's "stock listing date": a person's birth moment (date +
time-of-day + optional birthplace). Time-of-day drives the 時柱 / Moon position;
birthplace (lat/lon) is what house-/ascendant-based systems (占星, Jyotiṣa) need —
carried here so engines can use it as they grow into it.
"""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator


class BirthInput(BaseModel):
    name: str | None = Field(default=None, description="稱呼（可選，只用於解讀文案）")
    birth_date: date = Field(..., description="出生日期")
    birth_time: time | None = Field(
        default=None, description="出生時刻（時辰）。未知時 時柱以正午估算"
    )
    gender: str | None = Field(default=None, description="性別（部分命理用神不同）")

    # birthplace — optional, needed for ascendant/house systems
    place: str | None = Field(default=None, description="出生地名（顯示用）")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    tz_offset_hours: float = Field(default=8.0, description="出生地時區（東八區=+8）")

    @field_validator("birth_date")
    @classmethod
    def _not_absurd(cls, v: date) -> date:
        if v.year < 1 or v.year > 9999:
            raise ValueError("birth_date out of range")
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
        who = self.name or "命主"
        when = self.birth_date.isoformat() + (
            f" {self.birth_time.strftime('%H:%M')}" if self.birth_time else " (時辰未知)"
        )
        where = f" · {self.place}" if self.place else ""
        return f"{who} · {when}{where}"
