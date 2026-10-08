"""大六壬 — 命課 cast at the birth moment: 月將加時 → 天地盤 → 四課 → 三傳（賊克・比用）.

Native 起課 (the synced engine's simplified `yong_branch` has the 月將 mapping reversed —
it puts the Sun in Aries at 寅; 太陽躔降婁(Aries) is the 戌將). Rules here:
  月將  = the 地支 of the sign the Sun occupies (子=Aquarius … 亥=Pisces, i.e. 戌=Aries)
  天盤  = 月將 placed on the 占時 (birth hour) branch; 天盤 over X = X + 月將 − 占時
  四課  = 日干寄宮上神, its 上神; 日支上神, its 上神
  三傳  = 賊克法 (下賊上 first, then 上克下); 比用 to break ties; else the 日支上神
          (伏吟 / 返吟 / 涉害 etc. are not implemented and fall back the same way, flagged).
"""

from __future__ import annotations

import ephem

from fortune import astro_ext as AX
from fortune import bazi_ext as X
from fortune.birth import BirthInput
from fortune.engines.liuren import liuren
from fortune.schemas import Chart

KEY, ZH, EN = "liuren", "大六壬", "Da Liu Ren"
B, S = X.BRANCHES, X.STEMS
BE = X.BRANCH_ELEM
_JI_GONG = [2, 4, 5, 7, 5, 7, 8, 10, 11, 1]      # 日干寄宮: 甲寅 乙辰 丙巳 丁未 戊巳 己未 庚申 辛戌 壬亥 癸丑
_YUEJIANG_NAME = ["神后", "大吉", "功曹", "太衝", "天罡", "太乙", "勝光", "小吉", "傳送", "從魁", "河魁", "登明"]


def _ke(a_elem: str, b_elem: str) -> bool:
    return X.KE[a_elem] == b_elem


def cast(birth: BirthInput) -> Chart:
    birth_ut = AX.birth_utc(birth)
    p = X.exact_pillars(birth.dt, birth.tz_offset_hours)
    ds, db, hb = p["day"]["stem_idx"], p["day"]["branch_idx"], p["hour"]["branch_idx"]
    day_stem, dm_elem = S[ds], X.STEM_ELEM[ds]

    sun_sign = int(AX.lon_of_date(ephem.Sun, birth_ut) // 30) % 12
    yj = (10 - sun_sign) % 12                                    # 月將 (Aries→戌 … Pisces→亥)
    shift = (yj - hb) % 12
    up = lambda x: (x + shift) % 12                              # 天盤 branch sitting over 地盤 x

    k1 = up(_JI_GONG[ds]); k2 = up(k1); k3 = up(db); k4 = up(k3)   # 四課 上神
    courses = [("第一課", _JI_GONG[ds], k1, dm_elem), ("第二課", k1, k2, BE[k1]),
               ("第三課", db, k3, BE[db]), ("第四課", k3, k4, BE[k3])]

    # 賊克: 下賊上 (lower 剋 upper) takes precedence over 上克下
    zei = [c for c in courses if _ke(c[3], BE[c[2]])]
    ke_ = [c for c in courses if _ke(BE[c[2]], c[3])]
    method, cands = ("賊克法（下賊上）", zei) if zei else ("賊克法（上克下）", ke_) if ke_ else ("", [])
    note = ""
    if len(cands) > 1:                                           # 比用: 上神 陰陽 same as 日干
        bi = [c for c in cands if c[2] % 2 == ds % 2]
        if len(bi) == 1:
            cands, method = bi, method + "・比用"
        else:
            note = "多課賊克且比用不決，應用涉害法；此處取首課（簡化）"
            cands = cands[:1]
    if not cands:
        if shift == 0:
            note = "月將加時同位＝伏吟課，未實作，暫以日支上神為初傳"
        elif shift == 6:
            note = "月將與占時相沖＝返吟課，未實作，暫以日支上神為初傳"
        else:
            note = "四課無賊克，應用遙克／昴星等法；此處以日支上神為初傳（簡化）"
        method, cands = "日支上神（簡化）", [courses[2]]
    chu = cands[0][2]; zhong = up(chu); mo = up(zhong)
    rel, good = liuren._relation(dm_elem, BE[chu])

    readings = {
        "liuren_regime": "supported" if good else "afflicted",
        "day_master": f"{day_stem}（{dm_elem}）", "day_pillar": p["day"]["gz"],
        "yue_jiang": f"{B[yj]}（{_YUEJIANG_NAME[yj]}）", "occupy_hour": B[hb] + ("（時辰未知，以午時計）" if not birth.birth_time else ""),
        "four_courses": "　".join(f"{n} {B[u]}/{B[l] if i else S[ds]}" for i, (n, l, u, _e) in enumerate(courses)),
        "method": method + (f"；{note}" if note else ""),
        "three_transmissions": f"初傳 {B[chu]}・中傳 {B[zhong]}・末傳 {B[mo]}",
        "yong_branch": f"{B[chu]}（{BE[chu]}）", "relation": rel,
    }
    chain = [
        f"命課（{birth.dt.isoformat(timespec='minutes')} 本地時）：日干 {day_stem}，日支 {B[db]}，占時 {B[hb]}。",
        f"月將：太陽躔 {AX.sign_zh(sun_sign * 30)}宮 → {B[yj]}將（{_YUEJIANG_NAME[yj]}）；月將加占時 {B[hb]} 起天地盤。",
        "四課：" + "、".join(f"{n} {B[u]}／{B[l] if i else S[ds] + '（寄' + B[l] + '）'}" for i, (n, l, u, _e) in enumerate(courses)) + "。",
        f"三傳（{method}）：初傳 {B[chu]}、中傳 {B[zhong]}、末傳 {B[mo]}。" + (f"（{note}）" if note else ""),
        f"初傳 {B[chu]}（{BE[chu]}）與日主 {day_stem}（{dm_elem}）：{rel} → {'吉' if good else '凶'}。",
    ]
    summary = f"日干 {day_stem}（{dm_elem}）・{B[yj]}將加{B[hb]}時・三傳 {B[chu]}{B[zhong]}{B[mo]}・{rel}"
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"day_stem": day_stem, "day_stem_elem": dm_elem, "yue_jiang": B[yj], "occupy": B[hb],
               "heaven_plate": [{"ground": B[i], "sky": B[up(i)]} for i in range(12)],
               "courses": [{"name": n, "lower": B[l] if i else S[ds], "upper": B[u]} for i, (n, l, u, _e) in enumerate(courses)],
               "transmissions": [B[chu], B[zhong], B[mo]]},
        reasoning_chain=chain, readings=readings, summary=summary,
    )
