"""Registry of the 13 命理 systems → their cast(birth) adapter.
十三套命理系統 → 各自的 cast(birth) 轉接器。

Each value is (English name, 中文名, "module:function"). Imports are lazy so a
half-wired engine never breaks the whole service — `systems()` reports which
casters import cleanly. / 惰性 import，未接好的引擎不會拖垮整個服務。
"""

from __future__ import annotations

import importlib
import inspect

from fortune.birth import BirthInput
from fortune.schemas import Chart

# key : (English name, 中文名, dotted "module:func")
REGISTRY: dict[str, tuple[str, str, str]] = {
    "astrology": ("Western Astrology", "西洋占星", "fortune.casting.astrology:cast"),
    "bazi": ("BaZi · Four Pillars", "八字（四柱）", "fortune.casting.bazi:cast"),
    "ziwei": ("Zi Wei Dou Shu · Purple Star", "紫微斗數", "fortune.casting.ziwei:cast"),
    "iching": ("Plum-Blossom I Ching", "梅花易數", "fortune.casting.iching:cast"),
    "suimei": ("Shichū-Suimei · JP Four Pillars", "四柱推命（日）", "fortune.casting.suimei:cast"),
    "qizheng": ("Qi Zheng Si Yu · Seven Luminaries", "七政四餘", "fortune.casting.qizheng:cast"),
    "tieban": ("Tie Ban Shen Shu · Iron Plate", "鐵板神數", "fortune.casting.tieban:cast"),
    "qimen": ("Qi Men Dun Jia", "奇門遁甲", "fortune.casting.qimen:cast"),
    "liuren": ("Da Liu Ren", "大六壬", "fortune.casting.liuren:cast"),
    "taiyi": ("Tai Yi Shen Shu", "太乙神數", "fortune.casting.taiyi:cast"),
    "jyotish": ("Jyotiṣa · Vedic Astrology", "Jyotiṣa（吠陀占星）", "fortune.casting.jyotish:cast"),
    "liuyao": ("Liu Yao · Six Lines", "六爻（納甲）", "fortune.casting.liuyao:cast"),
    "xiaoliuren": ("Xiao Liu Ren", "小六壬", "fortune.casting.xiaoliuren:cast"),
}


# Systems that need more than the birth moment (a Chinese full name); listed by systems() with needs_name=True,
# castable through cast(), but not part of the 13-system loops (synthesis / specialists / `all`).
EXTRA: dict[str, tuple[str, str, str]] = {
    "xingming": ("Xing Ming · Name Numerology", "姓名學", "fortune.casting.xingming:cast"),
}


def _resolve(spec: str):
    mod, fn = spec.split(":")
    return getattr(importlib.import_module(mod), fn)


def cast(system: str, birth: BirthInput, **opts) -> Chart:
    """Cast `system` for `birth`. Extra options (e.g. house_system="placidus") are
    forwarded only to casters whose signature accepts them; others ignore them."""
    spec = REGISTRY.get(system) or EXTRA.get(system)
    if not spec:
        raise KeyError(f"unknown system: {system!r}. known: {', '.join(list(REGISTRY) + list(EXTRA))}")
    fn = _resolve(spec[2])
    accepted = inspect.signature(fn).parameters
    kw = {k: v for k, v in opts.items() if k in accepted}
    return fn(birth, **kw)


def systems() -> list[dict[str, object]]:
    """[{key, en, zh, available}] for the UI menu. / 給前端選單用。"""
    out: list[dict[str, object]] = []
    for key, (en, zh, spec) in list(REGISTRY.items()) + list(EXTRA.items()):
        try:
            _resolve(spec)
            ok = True
        except Exception:  # noqa: BLE001
            ok = False
        row = {"key": key, "en": en, "zh": zh, "available": ok}
        if key in EXTRA:
            row["needs_name"] = True
        out.append(row)
    return out
