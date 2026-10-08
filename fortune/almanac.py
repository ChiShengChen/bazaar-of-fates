"""黃曆 almanac block for the birth day — via lunar-python (MIT, 6tail) when installed.

Day-level 通書 facts the 八字 sheet traditionally carries: 二十八宿, 建除十二值, 彭祖百忌,
吉神/凶煞, 宜/忌, 喜神/財神/福神 方位, 六曜, 物候, 月相. Also 身宮 and 胎息 of the 八字.
Optional: returns None when lunar-python is absent. Nothing else depends on it.
"""

from __future__ import annotations

from datetime import datetime

try:                                                   # lunar-python speaks 簡體; the rest of this app is 正體
    from opencc import OpenCC
    _CC = OpenCC("s2twp")
except Exception:  # noqa: BLE001
    _CC = None


def t(x):
    """Recursively convert 簡體 → 台灣正體 (words included: 软件→軟體 style) when OpenCC is available."""
    if _CC is None:
        return x
    if isinstance(x, str):
        return _CC.convert(x).replace("兇", "凶")     # OpenCC prefers 兇; 命理 writes 吉凶
    if isinstance(x, list):
        return [t(i) for i in x]
    if isinstance(x, dict):
        return {t(k): t(v) for k, v in x.items()}
    return x


def almanac(dt_local: datetime) -> dict | None:
    try:
        from lunar_python import Solar
    except Exception:  # noqa: BLE001
        return None
    l = Solar.fromYmdHms(dt_local.year, dt_local.month, dt_local.day, dt_local.hour, dt_local.minute, 0).getLunar()
    ec = l.getEightChar()
    return t({
        "xiu": f"{l.getXiu()}{l.getZheng()}{l.getAnimal()}（{l.getXiuLuck()}）", "jianchu": l.getZhiXing(),
        "pengzu": [l.getPengZuGan(), l.getPengZuZhi()],
        "jishen": list(l.getDayJiShen()), "xiongsha": list(l.getDayXiongSha()),
        "yi": list(l.getDayYi())[:8], "ji": list(l.getDayJi())[:8],
        "positions": {"喜神": l.getDayPositionXiDesc(), "財神": l.getDayPositionCaiDesc(), "福神": l.getDayPositionFuDesc()},
        "liuyao": l.getLiuYao(), "wuhou": l.getWuHou(), "yuexiang": l.getYueXiang(),
        "shen_gong": ec.getShenGong(), "tai_xi": ec.getTaiXi(),
        "source": "lunar-python (MIT) — 6tail/lunar; 繁體 via OpenCC s2twp",
    })
