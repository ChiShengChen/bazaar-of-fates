"""Registry of the 11 命理 systems → their cast(birth) adapter.

Each value is (中文名, "module:function"). Imports are lazy so a half-wired engine
never breaks the whole service — `systems()` reports which casters import cleanly.
"""

from __future__ import annotations

import importlib

from fortune.birth import BirthInput
from fortune.schemas import Chart

# key : (中文名, dotted "module:func")
REGISTRY: dict[str, tuple[str, str]] = {
    "astrology": ("西洋占星", "fortune.casting.astrology:cast"),
    "bazi": ("八字（四柱）", "fortune.casting.bazi:cast"),
    "ziwei": ("紫微斗數", "fortune.casting.ziwei:cast"),
    "iching": ("梅花易數", "fortune.casting.iching:cast"),
    "suimei": ("四柱推命（日）", "fortune.casting.suimei:cast"),
    "qizheng": ("七政四餘", "fortune.casting.qizheng:cast"),
    "tieban": ("鐵板神數", "fortune.casting.tieban:cast"),
    "qimen": ("奇門遁甲", "fortune.casting.qimen:cast"),
    "liuren": ("大六壬", "fortune.casting.liuren:cast"),
    "taiyi": ("太乙神數", "fortune.casting.taiyi:cast"),
    "jyotish": ("Jyotiṣa（吠陀占星）", "fortune.casting.jyotish:cast"),
}


def _resolve(spec: str):
    mod, fn = spec.split(":")
    return getattr(importlib.import_module(mod), fn)


def cast(system: str, birth: BirthInput) -> Chart:
    if system not in REGISTRY:
        raise KeyError(f"unknown system: {system!r}. known: {', '.join(REGISTRY)}")
    return _resolve(REGISTRY[system][1])(birth)


def systems() -> list[dict[str, object]]:
    """[{key, zh, available}] for the UI menu."""
    out: list[dict[str, object]] = []
    for key, (zh, spec) in REGISTRY.items():
        try:
            _resolve(spec)
            ok = True
        except Exception:  # noqa: BLE001
            ok = False
        out.append({"key": key, "zh": zh, "available": ok})
    return out
