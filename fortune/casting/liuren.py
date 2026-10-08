"""大六壬 — 命課 cast at the birth moment: 月將加時 → 天地盤 → 四課 → 三傳（九宗門）.

Native 起課 (fortune.liuren_ext). The synced engine's simplified `yong_branch` has the 月將
mapping reversed (Sun in Aries at 寅; 太陽躔降婁(Aries) is the 戌將), so only its 五行
relation helper is reused. 月將 = the 地支 of the sign the Sun occupies (子=Aquarius …
戌=Aries, 亥=Pisces); 占時 = the birth hour (true solar time if requested).
"""

from __future__ import annotations

import ephem

from fortune import astro_ext as AX
from fortune import bazi_ext as X
from fortune import liuren_ext as LX
from fortune.birth import BirthInput
from fortune.engines.liuren import liuren
from fortune.schemas import Chart

KEY, ZH, EN = "liuren", "大六壬", "Da Liu Ren"
B, S = X.BRANCHES, X.STEMS
BE = X.BRANCH_ELEM
_YUEJIANG_NAME = ["神后", "大吉", "功曹", "太衝", "天罡", "太乙", "勝光", "小吉", "傳送", "從魁", "河魁", "登明"]


def cast(birth: BirthInput) -> Chart:
    birth_ut = AX.birth_utc(birth)
    cdt = X.cast_dt(birth)
    p = X.exact_pillars(cdt, birth.tz_offset_hours)
    ds, db, hb = p["day"]["stem_idx"], p["day"]["branch_idx"], p["hour"]["branch_idx"]
    day_stem, dm_elem = S[ds], X.STEM_ELEM[ds]
    sun_sign = int(AX.lon_of_date(ephem.Sun, birth_ut) // 30) % 12
    yj = (10 - sun_sign) % 12                                    # 月將 (Aries→戌 … Pisces→亥)

    k = LX.cast(ds, db, hb, yj)
    chu = k["chu"]
    rel, good = liuren._relation(dm_elem, BE[chu])
    tr = k["transmissions"]
    readings = {
        "liuren_regime": "supported" if good else "afflicted",
        "day_master": f"{day_stem}（{dm_elem}）・{'陽' if k['yang_day'] else '陰'}日", "day_pillar": p["day"]["gz"],
        "yue_jiang": f"{B[yj]}（{_YUEJIANG_NAME[yj]}）", "occupy_hour": B[hb] + ("（時辰未知，以午時計）" if not birth.birth_time else ""),
        "four_courses": "　".join(f"{c['name']} {c['upper']}/{c['lower']}" for c in k["courses"]),
        "course_type": k["kind"] + (f"；{'；'.join(k['notes'])}" if k["notes"] else ""),
        "three_transmissions": f"初傳 {tr[0]}・中傳 {tr[1]}・末傳 {tr[2]}",
        "yong_branch": f"{tr[0]}（{BE[chu]}）", "relation": rel,
    }
    chain = [
        f"命課（{cdt.isoformat(timespec='minutes')}{' 真太陽時' if cdt != birth.dt else ' 本地時'}）：日干 {day_stem}（{'陽' if k['yang_day'] else '陰'}日），日支 {B[db]}，占時 {B[hb]}。",
        f"月將：太陽躔 {AX.sign_zh(sun_sign * 30)}宮 → {B[yj]}將（{_YUEJIANG_NAME[yj]}）；月將加占時 {B[hb]} 起天地盤。",
        "四課：" + "、".join(f"{c['name']} {c['upper']}／{c['lower']}" + ("（寄" + c['lower_branch'] + "）" if i == 0 else "") for i, c in enumerate(k["courses"])) + "。",
        f"課體：{k['kind']}" + (f"（{'；'.join(k['notes'])}）" if k["notes"] else "") + f"；三傳：初 {tr[0]}、中 {tr[1]}、末 {tr[2]}。",
        f"初傳 {tr[0]}（{BE[chu]}）與日主 {day_stem}（{dm_elem}）：{rel} → {'吉' if good else '凶'}。",
    ]
    summary = f"日干 {day_stem}（{dm_elem}）・{B[yj]}將加{B[hb]}時・{k['kind'].split('（')[0]}・三傳 {''.join(tr)}・{rel}"
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"day_stem": day_stem, "day_stem_elem": dm_elem, "yue_jiang": B[yj], "occupy": B[hb],
               "heaven_plate": k["heaven_plate"], "courses": k["courses"], "kind": k["kind"], "transmissions": tr},
        reasoning_chain=chain, readings=readings, summary=summary,
    )
