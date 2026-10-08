"""六爻（納甲）— the birth moment's hexagram with 京房納甲, 八宮世應, 六親, 六神, 伏神, 旺衰.

The hexagram and 動爻 come from the classical 年月日時起卦 (shared with 梅花易數); the 納甲
layer is fortune.liuyao_ext. 月建/日辰 for 旺衰 are the birth month/day pillars.
"""

from __future__ import annotations

from fortune import bazi_ext as X
from fortune import liuyao_ext as LY
from fortune.birth import BirthInput
from fortune.casting.iching import divine as _meihua
from fortune.engines.iching import iching
from fortune.schemas import Chart

KEY, ZH, EN = "liuyao", "六爻（納甲）", "Liu Yao · Six Lines"


def cast(birth: BirthInput) -> Chart:
    div = _meihua(birth)
    p = X.exact_pillars(X.cast_dt(birth), birth.tz_offset_hours)
    g = LY.cast(div["lines"], div["moving"], p["day"]["stem_idx"], p["day"]["branch_idx"], p["month"]["branch_idx"])
    rows = g["lines"]
    shi_line = rows[g["shi"] - 1]
    mv = rows[g["moving"] - 1]
    chain = [
        f"起卦（{div['numbers']['lunar_text']}）：本卦 {g['name']}（第 {g['num']} 卦），{g['palace']}宮（{g['palace_elem']}），"
        f"世在{g['shi']}爻、應在{g['ying']}爻；月建 {g['month_branch']}、日辰 {g['day_gz']}（旬空 {g['kong_wang']}）。",
        "納甲：" + "、".join(f"{r['pos']}爻{r['stem']}{r['branch']}{r['relative']}{'（世）' if r['shi'] else '（應）' if r['ying'] else ''}" for r in rows) + "。",
        "六神：" + "、".join(f"{r['pos']}爻{r['god']}" for r in rows) + f"（{p['day']['stem']}日起{rows[0]['god']}）。",
        "旺衰：" + "、".join(f"{r['pos']}爻{r['branch']}{r['relative']} " + "/".join(r["notes"]) for r in rows) + "。",
    ]
    if g["hidden"]:
        chain.append("伏神：" + "、".join(f"{h['relative']}{h['stem']}{h['branch']} 伏於{h['pos']}爻{h['under']}之下" for h in g["hidden"]) + "。")
    if g["changed"]:
        c = g["changed"]
        chain.append(f"動爻：{g['moving']}爻 {mv['relative']}{mv['stem']}{mv['branch']} 動，變 {c['line']['relative']}{c['line']['stem']}{c['line']['branch']}（{c['relation']}）→ 變卦 {c['name']}（{c['palace']}宮）。")
    summary = f"{g['name']}（{g['palace']}宮）・世 {shi_line['relative']}{shi_line['branch']}・{g['moving']}爻{mv['relative']}動{('→' + g['changed']['name']) if g['changed'] else ''}"
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart={"hexagram": g, "diagram": iching.line_diagram(div)},
        reasoning_chain=chain,
        readings={
            "本卦": f"{g['name']}（{g['palace']}宮{g['palace_elem']}）", "世應": f"世{g['shi']}爻 {shi_line['relative']}{shi_line['branch']}・應{g['ying']}爻 {rows[g['ying'] - 1]['relative']}{rows[g['ying'] - 1]['branch']}",
            "六爻": "　".join(f"{r['pos']}:{r['god']}{r['relative']}{r['stem']}{r['branch']}{'動' if r['moving'] else ''}[{'/'.join(r['notes'])}]" for r in rows),
            "伏神": "、".join(f"{h['relative']}{h['stem']}{h['branch']}伏{h['pos']}爻" for h in g["hidden"]) or "—",
            "動爻": f"{g['moving']}爻 {mv['relative']}{mv['branch']} → {g['changed']['line']['relative']}{g['changed']['line']['branch']}（{g['changed']['relation']}）" if g["changed"] else "—",
            "變卦": g["changed"]["name"] if g["changed"] else "—",
            "月建日辰": f"月建 {g['month_branch']}・日辰 {g['day_gz']}・旬空 {g['kong_wang']}",
        },
        summary=summary,
    )
