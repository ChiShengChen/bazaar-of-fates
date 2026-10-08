"""八字（四柱）— cast the natal 命盤 from birth date + 時辰.

Adapter over fortune/engines/bazi/bazi.py (喜用神 / 旺衰) + the native fortune/bazi_ext.py
(exact 節氣 pillars, 十神, 藏干, 納音, 空亡, 神煞, 胎元/命宮, 起運, 大運/流年/流月, 稱骨).
Birth hour drives the 時柱 (defaults to noon → 午時 when unknown); the engine pins 日柱
to the verified 甲子 anchor.
"""

from __future__ import annotations

from datetime import date

from fortune import bazi_ext as X
from fortune.birth import BirthInput
from fortune.engines.bazi import bazi   # liunian_elem
from fortune.schemas import Chart

KEY, ZH, EN = "bazi", "八字（四柱）", "BaZi · Four Pillars"
_ORDER = ("year", "month", "day", "hour")


def _hidden_text(p: dict) -> str:
    return "".join(f"{h['stem']}({h['god']})" for h in p["hidden"])


def cast(birth: BirthInput) -> Chart:
    today = date.today()
    full = X.full_chart(birth, today=today)
    rows = full["pillars"]
    fav = full["strength"]                      # 月令 + 通根 + 透干 analysis (bazi_ext.strength_analysis)

    cur_dy = next((d for d in full["dayun"] if d["current"]), None)
    cur_ln = next((l for d in full["dayun"] for l in d["liunian"] if l["current"]), None)
    qy = full["qi_yun"]

    chain = [
        f"{p['pillar']}：{p['gz']}（{p['stem_elem']}{p['branch_elem']}・{p['zodiac']}）十神 {p['stem_god']}・藏干 {_hidden_text(p)}・納音 {p['nayin']}・空亡 {p['kong_wang']}"
        for p in rows
    ]
    if full["true_solar_time"]:
        chain.insert(0, f"真太陽時：時鐘 {full['clock'].replace('T', ' ')} → 真太陽時 {full['solar'].replace('T', ' ')}（經度 {birth.longitude}°）")
    chain.insert(0, f"節氣：{full['jie_prev']['name']} {full['jie_prev']['at'][:16].replace('T', ' ')} ～ "
                    f"{full['jie_next']['name']} {full['jie_next']['at'][:16].replace('T', ' ')}（公曆 {full['solar'].replace('T', ' ')}・農曆 {full['lunar']['text']}）")
    chain.append(f"旺衰：{'；'.join(fav['lines'])}")
    chain.append(f"日主 {fav['day_master']}（{fav['dm_elem']}）生扶 {fav['support']} ／ 剋洩耗 {fav['drain']}（得力比 {fav['ratio']:.0%}）→ {fav['label']}；"
                 f"{fav['pattern_note']}")
    chain.append(f"用神：{fav['yongshen']}（{fav['yongshen_why']}）；喜 {'、'.join(fav['favourable'])}、忌 {'、'.join(fav['avoid'])}；{fav['tiaohou_note']}")
    chain.append(f"胎元 {full['tai_yuan']}［{full['tai_yuan_nayin']}］・命宮 {full['ming_gong']}［{full['ming_gong_nayin']}］")
    if full["stem_notes"] or full["branch_notes"]:
        chain.append("留意：" + "；".join(full["stem_notes"] + full["branch_notes"]))
    chain.append(f"{qy['text']}（{'順行' if qy['forward'] else '逆行'}，{'陽' if full['pillars'][0]['stem_idx'] % 2 == 0 else '陰'}{full['gender']}命）"
                 f"・交運 {qy['jiao_yun'].replace('T', ' ')}・逢尾數 {qy['huan_yun_digit']} 之年換運")
    if cur_dy:
        chain.append(f"現行大運 {cur_dy['gz']}（{cur_dy['stem_god']}・{cur_dy['changsheng']}・{cur_dy['start_year']}–{cur_dy['end_year']}）"
                     + (f"・流年 {cur_ln['year']} {cur_ln['gz']}（{cur_ln['stem_god']}）" if cur_ln else ""))
    chain.append(f"稱骨 {full['cheng_gu']['label']}：{full['cheng_gu']['verdict']}")

    summary = (
        f"日主 {fav['day_master']}{fav['dm_elem']}・{fav['label']}・"
        f"喜用 {'、'.join(fav['favourable'])}"
    )
    readings = {
        "day_master": fav["day_master"], "dm_elem": fav["dm_elem"],
        "strength": fav["label"], "strength_ratio": f"{fav['ratio']:.0%}（生扶 {fav['support']} / 剋洩耗 {fav['drain']}）",
        "favourable": fav["favourable"], "avoid": fav["avoid"], "yongshen": f"{fav['yongshen']}：{fav['yongshen_why']}",
        "tiaohou": fav["tiaohou_note"], "pattern": fav["pattern"],
        "pillars": "　".join(f"{p['pillar']}{p['gz']}" for p in rows),
        "ten_gods": "　".join(f"{p['pillar']}{p['stem_god']}" for p in rows),
        "hidden_stems": "　".join(f"{p['branch']}:{_hidden_text(p)}" for p in rows),
        "nayin": "　".join(f"{p['gz']}{p['nayin']}" for p in rows),
        "kong_wang": "　".join(f"{p['pillar']}{p['kong_wang']}" for p in rows),
        "shensha": "　".join(f"{p['pillar']}:{'、'.join(p['shensha']) or '—'}" for p in rows),
        "tai_yuan": full["tai_yuan"], "ming_gong": full["ming_gong"],
        "lunar": full["lunar"]["text"],
        "relations": "；".join(full["stem_notes"] + full["branch_notes"]) or "—",
        "qi_yun": f"{qy['text']}・交運 {qy['jiao_yun'][:10]}",
        "dayun_sequence": "　".join(f"{d['start_age']}歲{d['gz']}({d['stem_god']})" for d in full["dayun"]),
        "cheng_gu": f"{full['cheng_gu']['label']}（{full['cheng_gu']['weight']} 兩）",
        "liunian_year": today.year,
        "current_liunian_elem": bazi.liunian_elem(today),   # 今年的流年五行（不是出生年）
    }
    if cur_dy:
        readings["current_dayun"] = f"{cur_dy['gz']}（{cur_dy['stem_god']}・{cur_dy['changsheng']}・{cur_dy['start_year']}–{cur_dy['end_year']}）"
        readings["current_dayun_relations"] = "；".join(cur_dy["stem_notes"] + cur_dy["branch_notes"]) or "—"
    if cur_ln:
        readings["current_liunian"] = f"{cur_ln['year']} {cur_ln['gz']}（{cur_ln['stem_god']}）神煞 {'、'.join(cur_ln['shensha']) or '—'}"
        readings["current_liunian_relations"] = "；".join(cur_ln["stem_notes"] + cur_ln["branch_notes"]) or "—"
    if full["gender_assumed"]:
        readings["note"] = "性別未填，起運方向以男命推算 / gender unset → assumed male for 大運 direction"

    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=birth.label(), cast_at=birth.dt,
        chart=full,
        reasoning_chain=chain,
        readings=readings,
        summary=summary,
    )
