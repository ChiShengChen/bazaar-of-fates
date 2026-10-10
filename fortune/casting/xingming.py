"""姓名學 — 熊崎式五格剖象法 via fortune.xingming: 康熙筆畫 (Unihan 部首原形＋其餘筆畫), 天人地外總五格, 三才, 81 數理,
and the 八字 link (each 格's element against the same 旺衰／喜用 the 八字 sheet uses).

The name comes from `birth.full_name`, or from `birth.name` when that is a 2–5 character Chinese name.
Options: stroke_basis kangxi｜modern, numeral_strokes value｜shape, jiashu on｜off (熊崎式 假數).
"""

from __future__ import annotations

import re
from datetime import datetime

from fortune import bazi_ext as X
from fortune.birth import BirthInput
from fortune.schemas import Chart
from fortune.xingming import engine as N

KEY, ZH, EN = "xingming", "姓名學", "Xing Ming · Name Numerology"
_CJK = re.compile(r"^[㐀-鿿豈-﫿　 ]{2,7}$")
GRID_ROLE = {"天格": "先天運：祖蔭與早年環境，自己改不了", "人格": "主運：姓名的核心，主性格與一生主軸", "地格": "前運：中年以前，與子女、部屬、家庭",
             "外格": "副運：人際、社交、外在機緣", "總格": "後運：中年以後的總結"}


def _name_of(birth: BirthInput) -> str:
    if birth.full_name and birth.full_name.strip():
        return birth.full_name.strip()
    if birth.name and _CJK.match(birth.name.strip()):
        return birth.name.strip()
    raise N.NameInputError("姓名學需要中文全名（birth.full_name）/ Name numerology needs a Chinese full name", "needs_full_name")


def build(full_name: str, birth: BirthInput | None = None, *, stroke_basis: str = "kangxi", numeral_strokes: str = "value", jiashu: str = "on") -> Chart:
    rules = N.Rules(stroke_basis=stroke_basis if stroke_basis in ("kangxi", "modern") else "kangxi",
                    numeral_strokes=numeral_strokes if numeral_strokes in ("value", "shape") else "value", jiashu="off" if jiashu in ("off", False) else "on")
    nc = N.analyze(full_name, rules)
    grids = {name: nc.grids[name] for name in N.GRID_NAMES}
    t, r, d = (grids[x].element for x in ("天格", "人格", "地格"))
    bazi = None
    if birth is not None:
        try:
            full = X.full_chart(birth)
            st = full["strength"]
            fav, avoid = list(st["favourable"]), list(st.get("avoid") or [])
            tag = lambda e: "喜用" if e in fav else ("忌" if e in avoid else "閒")  # noqa: E731
            bazi = {"favourable": fav, "avoid": avoid, "day_master": st["day_master"], "dm_elem": st["dm_elem"], "strength": st["label"].split("（")[0],
                    "grids": {name: tag(g.element) for name, g in grids.items()}}
        except Exception as e:  # noqa: BLE001 — the name sheet stands on its own
            bazi = {"error": str(e)}
    score = sum(nc.relations[k]["score"] for k in ("成功運", "基礎運", "社交運")) + {"吉": 1, "半吉": 0, "凶": -1}[grids["人格"].luck] + {"吉": 0.5, "半吉": 0, "凶": -0.5}[grids["總格"].luck]
    readings = {
        "xingming_regime": "favourable" if score >= 1.5 else "unfavourable" if score <= -1 else "neutral",
        "姓名": f"{nc.surname} {nc.given}（{'複姓' if len(nc.surname) > 1 else '單姓'}、{'單名' if len(nc.given) == 1 else f'{len(nc.given)} 字名'}）",
        "筆畫": "、".join(f"{c.char}{c.strokes}" for c in nc.chars) + f"（{'康熙' if rules.stroke_basis == 'kangxi' else '現代'}筆畫）",
        **{name: f"{g.number}{'（數理取 ' + str(g.shuli) + '）' if g.shuli != g.number else ''}・{g.element}・{g.luck}" for name, g in grids.items()},
        "三才": f"{nc.sancai}（天{t} 人{r} 地{d}）",
        "成功運": nc.relations["成功運"]["text"] + f"（{nc.relations['成功運']['kind']}）",
        "基礎運": nc.relations["基礎運"]["text"] + f"（{nc.relations['基礎運']['kind']}）",
        "社交運": nc.relations["社交運"]["text"] + f"（{nc.relations['社交運']['kind']}）",
    }
    if bazi and "error" not in bazi:
        readings["八字喜用"] = f"喜 {'、'.join(bazi['favourable'])}・忌 {'、'.join(bazi['avoid']) or '無'}（日主{bazi['day_master']}{bazi['dm_elem']}，{bazi['strength']}）"
        readings["五格對八字"] = "、".join(f"{name}{grids[name].element}：{v}" for name, v in bazi["grids"].items())
        readings["人格對八字"] = f"人格{r}：{bazi['grids']['人格']}"
    if nc.warnings:
        readings["注意"] = "；".join(nc.warnings)
    chain = [f"分姓名：{nc.split_note}。",
             "筆畫：" + "；".join(f"{c.char}（{c.role}）{c.strokes} 畫 — {c.how}" for c in nc.chars) + "。",
             "五格：" + "；".join(f"{name} {g.formula} ＝ {g.number} → {g.element}（{g.yinyang}）{g.luck}" for name, g in grids.items()) + "。",
             f"三才 {nc.sancai}：{nc.relations['成功運']['text']}（成功運）、{nc.relations['基礎運']['text']}（基礎運）、{nc.relations['社交運']['text']}（社交運）。"]
    if bazi and "error" not in bazi:
        chain.append(f"配八字：日主{bazi['day_master']}{bazi['dm_elem']} {bazi['strength']}，喜 {'、'.join(bazi['favourable'])}；" + "、".join(f"{n}{grids[n].element}{v}" for n, v in bazi["grids"].items()) + "（姓名論八字以人格為主）。")
    elif bazi:
        chain.append(f"配八字：未能排出八字（{bazi['error']}），只論姓名本身。")
    else:
        chain.append("未提供生辰，只論姓名本身。")
    summary = f"{nc.surname}{nc.given}：人格 {grids['人格'].number}{grids['人格'].element}{grids['人格'].luck}・三才 {nc.sancai}・總格 {grids['總格'].number}{grids['總格'].luck}" + (f"・人格對八字{bazi['grids']['人格']}" if bazi and 'error' not in bazi else "")
    return Chart(
        system=KEY, system_en=EN, system_zh=ZH, subject=(birth.label() if birth else f"{nc.surname}{nc.given}"), cast_at=(birth.dt if birth else datetime.now().replace(microsecond=0)),
        chart={"surname": nc.surname, "given": nc.given, "split_note": nc.split_note,
               "chars": [{"char": c.char, "role": c.role, "strokes": c.strokes, "kangxi": c.kangxi, "modern": c.modern, "traditional": c.traditional, "how": c.how} for c in nc.chars],
               "grids": [{"name": g.name, "id": N.GRID_IDS[g.name], "number": g.number, "shuli": g.shuli, "element": g.element, "yinyang": g.yinyang, "luck": g.luck,
                          "formula": g.formula, "role": GRID_ROLE[g.name], "bazi": (bazi or {}).get("grids", {}).get(g.name, "")} for g in grids.values()],
               "sancai": nc.sancai, "relations": nc.relations, "rules": {"stroke_basis": rules.stroke_basis, "numeral_strokes": rules.numeral_strokes, "jiashu": rules.jiashu},
               "bazi": bazi, "warnings": nc.warnings, "score": score},
        reasoning_chain=chain, readings=readings, summary=summary,
    )


def cast(birth: BirthInput, *, stroke_basis: str = "kangxi", numeral_strokes: str = "value", jiashu: str = "on") -> Chart:
    return build(_name_of(birth), birth, stroke_basis=stroke_basis, numeral_strokes=numeral_strokes, jiashu=jiashu)
