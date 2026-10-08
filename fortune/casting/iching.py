"""梅花易數 — traditional 時間起卦 from the birth moment (農曆年月日＋時辰).

Native casting rule (the engine's `cast` is a Gregorian-date hash; the classical
年月日時起卦 is):
  上卦 = (年支數 + 農曆月 + 農曆日) mod 8        (0 → 8 坤)
  下卦 = (年支數 + 農曆月 + 農曆日 + 時辰數) mod 8
  動爻 = (年支數 + 農曆月 + 農曆日 + 時辰數) mod 6  (0 → 6)
with 年支數 子=1…亥=12 and 時辰數 子=1…亥=12, trigrams in 先天 order 乾1 兌2 離3 震4 巽5 坎6 艮7 坤8.
The engine's 六十四卦 table, 互卦/變卦, 體用 and 五行生剋 verdict are reused unchanged.
"""

from __future__ import annotations

from fortune import bazi_ext as X
from fortune.birth import BirthInput
from fortune.engines.iching import iching
from fortune.schemas import Chart

KEY, ZH, EN = "iching", "梅花易數", "Plum-Blossom I Ching"


def divine(birth: BirthInput) -> dict:
    hb = X.exact_pillars(X.cast_dt(birth), birth.tz_offset_hours)["hour"]["branch_idx"]
    lunar = X.lunar_info(X.cast_dt(birth).date(), hb)
    yz = (lunar["year"] - 4) % 12 + 1                     # 年支數 子=1 … 亥=12
    m, d, h = lunar["month"], lunar["day"], hb + 1
    s_upper, s_all = yz + m + d, yz + m + d + h
    upper = iching.ORDER[(s_upper % 8 or 8) - 1]
    lower = iching.ORDER[(s_all % 8 or 8) - 1]
    moving = s_all % 6 or 6

    ben_num, ben_name = iching.kingwen(upper, lower)
    lines = iching._lines_bottom_top(upper, lower)
    hu_lower = iching._trigram_by_lines(tuple(lines[1:4]))
    hu_upper = iching._trigram_by_lines(tuple(lines[2:5]))
    hu_num, hu_name = iching.kingwen(hu_upper, hu_lower)
    changed = list(lines)
    changed[moving - 1] ^= 1
    bian_lower = iching._trigram_by_lines(tuple(changed[0:3]))
    bian_upper = iching._trigram_by_lines(tuple(changed[3:6]))
    bian_num, bian_name = iching.kingwen(bian_upper, bian_lower)
    yong, ti = (lower, upper) if moving <= 3 else (upper, lower)
    relation, verdict, auspicious = iching.wuxing_relation(ti, yong)
    return {
        "upper": upper, "lower": lower, "moving": moving, "lines": lines,
        "ben_num": ben_num, "ben_name": ben_name, "hu_num": hu_num, "hu_name": hu_name,
        "bian_num": bian_num, "bian_name": bian_name,
        "ti": ti, "yong": yong, "ti_wuxing": iching.TRIGRAMS[ti]["wuxing"], "yong_wuxing": iching.TRIGRAMS[yong]["wuxing"],
        "relation": relation, "verdict": verdict, "auspicious": auspicious,
        "ti_is_yang": iching.TRIGRAMS[ti]["yang"],
        "numbers": {"year_branch": yz, "lunar_month": m, "lunar_day": d, "hour": h,
                    "upper_sum": s_upper, "lower_sum": s_all, "lunar_text": lunar["text"]},
    }


def cast(birth: BirthInput) -> Chart:
    div = divine(birth)
    n = div["numbers"]
    chain = [
        f"起卦（農曆 {n['lunar_text']}{'，時辰未知以午時計' if not birth.birth_time else ''}）："
        f"年支 {n['year_branch']} ＋ 月 {n['lunar_month']} ＋ 日 {n['lunar_day']} ＝ {n['upper_sum']} → 上卦 {div['upper']}；"
        f"＋ 時 {n['hour']} ＝ {n['lower_sum']} → 下卦 {div['lower']}、動爻 {div['moving']}",
        f"本卦：{div['ben_name']}（第 {div['ben_num']} 卦）",
        f"互卦：{div['hu_name']}　變卦：{div['bian_name']}（動爻 第 {div['moving']} 爻）",
        f"體用：體={div['ti']}（{div['ti_wuxing']}）・用={div['yong']}（{div['yong_wuxing']}）",
        f"五行：{div['relation']} → {div['verdict']}",
    ]
    summary = f"{div['ben_name']}・{div['relation']}・{div['verdict']}"
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"hexagram": div, "diagram": iching.line_diagram(div)},
        reasoning_chain=chain,
        readings={
            "起卦數": f"年支{n['year_branch']}＋月{n['lunar_month']}＋日{n['lunar_day']}＋時{n['hour']}",
            "本卦": div["ben_name"], "互卦": div["hu_name"], "變卦": div["bian_name"],
            "動爻": div["moving"], "體用關係": div["relation"], "斷": div["verdict"], "auspicious": div["auspicious"],
        },
        summary=summary,
    )
