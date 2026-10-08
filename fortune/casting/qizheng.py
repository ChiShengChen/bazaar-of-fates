"""七政四餘 — Chinese astral 命盤 (7 visibles + 4 shadow points), with this year's transits.

七政 are computed natively at the exact birth instant (true equinox of date, via
fortune.astro_ext); 四餘 use the engine's mean elements evaluated at that instant.
"""

from __future__ import annotations

from datetime import date, datetime

import ephem

from fortune import astro_ext as AX
from fortune.birth import BirthInput
from fortune.engines.qizheng import qizheng
from fortune.schemas import Chart

KEY, ZH, EN = "qizheng", "七政四餘", "Qi Zheng Si Yu · Seven Luminaries"
_NAMES = {"Sun": "日", "Moon": "月", "Mercury": "水", "Venus": "金", "Mars": "火", "Jupiter": "木", "Saturn": "土"}


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    birth_ut = AX.birth_utc(birth)
    rows = [{"body": _NAMES[p["body"]], "ecliptic_lon": p["ecliptic_lon"], "sign": p["sign"],
             "sign_zh": p["sign_zh"], "retrograde": p["retrograde"]} for p in AX.planets_at(birth_ut)]
    for nm, lon in qizheng.four_remainders(birth_ut).items():        # mean elements at the instant
        rows.append({"body": nm, "ecliptic_lon": round(lon, 2), "sign": AX.sign_of(lon), "sign_zh": AX.sign_zh(lon)})
    natal_sun_sign = qizheng._sign(rows[0]["ecliptic_lon"])

    # this year's transits (noon UT today, same frame as the natal positions)
    now = datetime(today.year, today.month, today.day, 12)
    jup, mars = qizheng._sign(AX.lon_of_date(ephem.Jupiter, now)), qizheng._sign(AX.lon_of_date(ephem.Mars, now))
    node = qizheng._sign(qizheng.four_remainders(now)["羅睺"])
    trine = {(natal_sun_sign + k) % 12 for k in (0, 4, 8)}
    opp = {(natal_sun_sign + k) % 12 for k in (0, 6)}
    benefic, malefic = jup in trine, (mars in opp) or (node in opp)
    regime = "malefic_affliction" if malefic else "benefic_blessing" if benefic else "neutral"
    S = qizheng.A._SIGNS
    readings = {
        "qizheng_regime": regime, "ming_zhu_sign": S[natal_sun_sign],
        "jupiter_sign": S[jup], "mars_sign": S[mars], "rahu_sign": S[node],
        "jupiter_blesses": "是" if benefic else "否", "malefic_afflicts": "是" if malefic else "否",
        "seven": "、".join(f"{r['body']}{r['sign_zh']}{' ℞' if r.get('retrograde') else ''}" for r in rows[:7]),
        "four_remainders": "、".join(f"{r['body']}{r['sign_zh']}" for r in rows[7:]),
    }
    chain = [
        f"立命（{birth_ut.isoformat(timespec='minutes')} UT{'' if birth.birth_time else '，時辰未知以正午計'}）：命主太陽躔 {S[natal_sun_sign]}（{rows[0]['sign_zh']}）。",
        "七政：" + "、".join(f"{r['body']}{r['sign']}" for r in rows[:7]) + "。",
        "四餘：" + "、".join(f"{r['body']}{r['sign']}" for r in rows[7:]) + "（羅睺=月升交點、計都=降交點、月孛=月遠地點、紫炁=虛擬之炁）。",
        f"流年躔度（{today.isoformat()}）：歲星(木)入{S[jup]}、火星入{S[mars]}、羅睺入{S[node]}。",
        f"歲星{'拱照命主（三合/同宮）' if benefic else '未照命主'}；火羅{'沖剋命主' if malefic else '無沖'}。",
    ]

    # 命宮 (rising "life palace") = the ascendant degree; needs 時辰 + 出生地
    asc = AX.ascendant_block(birth)
    if asc:
        for r in rows:
            r["house"] = AX.house_of(r["ecliptic_lon"], asc["longitude"])
        readings["ming_gong_sign"] = f"{asc['sign']} {asc['sign_zh']} {asc['longitude']:.1f}°"
        chain.insert(1, f"命宮（命度／上升）：{asc['sign_zh']}宮 {asc['longitude']:.1f}°"
                        f"——七政四餘以命度起十二宮。")
        ming_str = f"・命宮 {asc['sign_zh']}"
    else:
        readings["ming_gong_sign"] = "unknown — needs birth time + place 需時辰＋出生地"
        ming_str = ""

    summary = f"命主太陽 {S[natal_sun_sign]}{ming_str}・流年 {regime}"
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"bodies": rows}, reasoning_chain=chain, readings=readings, summary=summary,
        ascendant=asc,
    )
