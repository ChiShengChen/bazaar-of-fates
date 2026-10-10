"""HTML renderers for the Space UI — the same sheets the Next.js app draws, as inline-styled HTML."""

from __future__ import annotations

import html

ELEM_COLOR = {"木": "#2f6b2f", "火": "#b4302b", "土": "#8a5a1b", "金": "#4a4238", "水": "#1f4e8c"}
STEM_ELEM = dict(zip("甲乙丙丁戊己庚辛壬癸", "木木火火土土金金水水"))
BRANCH_ELEM = dict(zip("子丑寅卯辰巳午未申酉戌亥", "水土木木土火火土金金土水"))
MAJOR = {"紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府", "太陰", "貪狼", "巨門", "天相", "天梁", "七殺", "破軍"}
LABELS = {
    "day_master": "日主", "dm_elem": "日主五行", "strength": "旺衰", "strength_ratio": "得力比", "favourable": "喜用", "avoid": "忌",
    "yongshen": "用神", "tiaohou": "調候", "pattern": "格局", "pillars": "四柱", "ten_gods": "十神", "hidden_stems": "藏干", "nayin": "納音",
    "kong_wang": "空亡", "shensha": "神煞", "tai_yuan": "胎元", "ming_gong": "命宮", "lunar": "農曆", "relations": "刑沖合會", "qi_yun": "起運",
    "dayun_sequence": "大運", "cheng_gu": "稱骨", "liunian_year": "流年", "current_liunian_elem": "流年五行", "current_dayun": "現行大運",
    "current_dayun_relations": "大運留意", "current_liunian": "今年流年", "current_liunian_relations": "流年留意", "almanac": "黃曆",
    "shen_gong_taixi": "身宮/胎息", "note": "註", "focus_topic": "問題主題", "focus_verdict": "本門派判斷", "focus_facts": None,
    "soul_star": "命主星", "body_star": "身主星", "five_elements_class": "五行局", "natal_sihua": "生年四化", "liunian_stem": "流年天干",
    "liunian_sihua": "流年四化", "sihua_landing": "四化落宮", "ziwei_regime": "流年判定", "life_palace_branch": "命宮地支", "body_palace": "身宮",
    "hour_branch": "生時", "lunar_birth": "農曆生辰", "life_palace_stars": "命宮星曜", "body_palace_stars": "身宮星曜", "palaces": "十二宮",
    "current_daxian": "現行大限", "daxian_sequence": "大限", "brightness": "亮度", "patterns": "格局", "current_liuyue": "流月",
    "astro_regime": "狀態", "mercury_retrograde": "水星逆行", "moon_illumination_pct": "月亮光照%", "moon_phase": "月相", "sun_sign": "太陽星座",
    "n_aspects": "相位數", "birth_moment_ut": "出生時刻 UT", "aspects": "相位", "ascendant": "上升", "house_system": "宮位制", "chart_ruler": "命主星",
    "angular_planets": "四正行星", "jyotish_regime": "daśā 狀態", "moon_nakshatra": "月宿", "moon_rashi": "月 rāśi", "mahadasha_lord": "大運主星",
    "dasha_nature": "吉凶", "ayanamsa_deg": "歲差", "grahas": "九曜", "lagna_rashi": "Lagna", "lagna_deg": "Lagna 度數",
    "qimen_regime": "狀態", "method": "起局法", "dun": "遁", "ju": "局", "yuan": "元", "term": "節氣", "day_hour": "日時", "xun": "旬",
    "zhifu": "值符", "zhishi": "值使", "active_gate": "值使門", "gate_class": "門類",
    "liuren_regime": "狀態", "day_pillar": "日柱", "yue_jiang": "月將", "occupy_hour": "占時", "four_courses": "四課", "course_type": "課體",
    "three_transmissions": "三傳", "generals": "天將", "yong_branch": "用神", "relation": "與日主",
    "qizheng_regime": "狀態", "ming_zhu_sign": "命主太陽", "jupiter_sign": "歲星", "mars_sign": "火星", "rahu_sign": "羅睺", "jupiter_blesses": "歲星拱照",
    "malefic_afflicts": "火羅沖剋", "seven": "七政", "four_remainders": "四餘", "ming_gong_sign": "命宮",
    "tieban_regime": "狀態", "ming_number": "命數", "liunian_verse_no": "流年條文", "liunian_verdict": "流年斷", "liunian_gua": "流年卦",
    "taiyi_regime": "狀態", "method": "積年法", "natal_accumulated_years": "命局積年", "natal_ju": "命局局數", "natal_palace": "命局太乙宮", "natal_wenchang_shiji": "命局文昌始擊", "natal_host_guest": "命局主客", "liunian_ju": "流年局數", "liunian_palace": "流年太乙宮", "liunian_wenchang_shiji": "流年文昌始擊", "liunian_judgements": "流年斷例", "brightness_school": "亮度流派",
    "liunian_host_guest": "流年主客", "verdict": "斷", "day_master_elem": "日主五行", "twelve_fortune": "十二運星", "tenchusatsu": "天中殺",
}
_CSS = ""


_ELEM_CLASS = {"木": "e-wood", "火": "e-fire", "土": "e-earth", "金": "e-metal", "水": "e-water"}


def _c(ch: str, big: bool = False) -> str:
    cls = _ELEM_CLASS.get(STEM_ELEM.get(ch) or BRANCH_ELEM.get(ch) or ch, "")
    return f'<span class="ch {cls}{" big" if big else ""}">{html.escape(ch)}</span>'


def _e(x) -> str:
    return html.escape(str(x))


def bazi(c: dict) -> str:
    P = c.get("pillars", [])
    s = c.get("strength", {})
    q = c.get("qi_yun", {})
    out = ['<div class="paper bz"><div class="title">八字命盤 <span class="seal">四柱</span></div><div class="head">']
    out.append(f"<div><span class='muted'>日主</span> {_c(c['day_master']['stem'])}（{c['day_master']['yinyang']}{c['day_master']['elem']}）　<span class='muted'>性別</span> {c['gender']}　"
               f"<span class='muted'>胎元</span> {_e(c['tai_yuan'])}［{_e(c['tai_yuan_nayin'])}］　<span class='muted'>命宮</span> {_e(c['ming_gong'])}［{_e(c['ming_gong_nayin'])}］</div>")
    out.append(f"<div><span class='muted'>節氣</span> {_e(c['jie_prev']['at'].replace('T', ' '))} {_e(c['jie_prev']['name'])} ～ {_e(c['jie_next']['at'].replace('T', ' '))} {_e(c['jie_next']['name'])}　"
               f"<span class='muted'>農曆</span> {_e(c['lunar']['text'])}</div>")
    out.append(f"<div><span class='muted'>起運</span> {_e(q.get('text', ''))}（{'順行' if q.get('forward') else '逆行'}）　<span class='muted'>交運</span> {_e(q.get('jiao_yun', '').replace('T', ' '))}　<span class='muted'>換運</span> 逢尾數 {_e(q.get('huan_yun_digit', ''))}</div>")
    if s:
        out.append(f"<div><span class='muted'>旺衰</span> <b>{_e(s['label'])}</b>（得力 {int(s['ratio'] * 100)}%）　<span class='muted'>格局</span> {_e(s['pattern'])}　<span class='muted'>用神</span> {_c(s['yongshen'])}　"
                   f"<span class='muted'>喜</span> {''.join(_c(e) for e in s['favourable'])}　<span class='muted'>忌</span> {''.join(_c(e) for e in s['avoid'])}<div class='muted' style='font-size:12px'>{_e(s['yongshen_why'])}；{_e(s['tiaohou_note'])}</div></div>")
    out.append("</div><div class='tw'><table><tr><th>四柱</th>" + "".join(f"<th>{_e(p['pillar'])}</th>" for p in P) + "</tr>")
    rows = [("十神", lambda p: _e(p["stem_god"])), ("天干", lambda p: _c(p["stem"], True)), ("地支", lambda p: _c(p["branch"], True) + f" <span class='muted'>{_e(p['zodiac'])}</span>"),
            ("藏干", lambda p: "<br>".join(_c(h["stem"]) + f"（{_e(h['god'])}）" for h in p["hidden"])), ("納音", lambda p: _e(p["nayin"])), ("長生", lambda p: _e(p["changsheng"])),
            ("空亡", lambda p: _e(p["kong_wang"])), ("神煞", lambda p: "<br>".join(map(_e, p["shensha"])) or "—")]
    for label, fn in rows:
        out.append(f"<tr><td>{label}</td>" + "".join(f"<td>{fn(p)}</td>" for p in P) + "</tr>")
    out.append("</table></div>")
    out.append(f"<div class='note'><span class='muted'>天干留意：</span>{_e('；'.join(c.get('stem_notes', [])) or '—')}</div><div class='note'><span class='muted'>地支留意：</span>{_e('；'.join(c.get('branch_notes', [])) or '—')}</div>")
    cg = c.get("cheng_gu", {})
    out.append(f"<div class='note'><span class='muted'>稱骨：</span>{_e(cg.get('label', ''))}（{cg.get('weight', '')} 兩）— {_e(cg.get('verdict', ''))}</div>")
    alm = c.get("almanac")
    if alm:
        out.append(f"<div class='note'><span class='muted'>黃曆：</span>{_e(alm['xiu'])}・建除 {_e(alm['jianchu'])}・宜 {_e('、'.join(alm['yi']))}・忌 {_e('、'.join(alm['ji']))}</div>")
    out.append("<div class='note muted'>大運（點選看流年請用網頁版）</div><div class='strip'>")
    for d in c.get("dayun", []):
        out.append(f"<div class='cell {'fav' if d['nature'] == 'favourable' else 'unf'}{' now' if d['current'] else ''}'><div class='muted'>{d['start_age']}歲·{d['start_year']}</div><div>{_c(d['stem'])}{_c(d['branch'])}</div><div>{_e(d['stem_god'])}</div><div class='muted'>{_e(d['changsheng'])}</div></div>")
    cur = next((d for d in c.get("dayun", []) if d["current"]), None)
    if cur:
        out.append("</div><div class='note muted'>現行大運的流年</div><div class='strip'>")
        for l in cur["liunian"]:
            out.append(f"<div class='cell {'fav' if l['nature'] == 'favourable' else 'unf'}{' now' if l['current'] else ''}'><div class='muted'>{l['age']}歲·{l['year']}</div><div>{_c(l['gz'][0])}{_c(l['gz'][1])}</div><div>{_e(l['stem_god'])}</div></div>")
    out.append("</div></div>")
    return "".join(out)


def ziwei(c: dict, readings: dict, subject: str) -> str:
    CELL = {5: (1, 1), 6: (1, 2), 7: (1, 3), 8: (1, 4), 4: (2, 1), 9: (2, 4), 3: (3, 1), 10: (3, 4), 2: (4, 1), 1: (4, 2), 0: (4, 3), 11: (4, 4)}
    B = "子丑寅卯辰巳午未申酉戌亥"
    out = ['<div class="paper"><div class="title">紫微斗數命盤 <span class="seal">十二宮</span></div><div class="zw">']
    for p in c.get("palaces", []):
        r, col = CELL[B.index(p["branch"])]
        stars = []
        for s in p["stars"]:
            bare = s.split("(")[0]
            br = (p.get("brightness") or {}).get(bare, "")
            stars.append(f"<span class='{'maj' if bare in MAJOR else 'min'}'>{_e(s)}{('<sup>' + _e(br) + '</sup>') if br else ''}</span>")
        have = {st.split("(")[0] for st in p["stars"]}
        adj = " ".join(_e(a) for a in p.get("adjective_stars", []) if a not in have)
        out.append(f"<div class='c{' body' if p['is_body'] else ''}' style='grid-row:{r};grid-column:{col}'><div>{' '.join(stars)}{('<div class=min>' + adj + '</div>') if adj else ''}</div>"
                   f"<div class='nm'><b>{_e(p['name'])}</b> <span class='min'>{_e(p.get('stem', ''))}{_e(p['branch'])}{'·' + _e(p['changsheng']) + '·' + _e(p['boshi']) if p.get('changsheng') else ''}</span></div></div>")
    out.append(f"<div class='ctr'><div class='min'>{_e(subject)}</div><div>命主 <b>{_e(readings.get('soul_star', '?'))}</b>・身主 {_e(readings.get('body_star', '?'))}</div><div>{_e(readings.get('five_elements_class', ''))}・命宮 {_e(readings.get('life_palace_branch', ''))}</div>"
               f"<div class='min'>生年四化 {_e(readings.get('natal_sihua', ''))}</div><div class='min'>{_e(readings.get('current_daxian', ''))}</div></div></div>")
    luck = c.get("luck", {})
    if luck.get("daxian"):
        out.append("<div class='bz'><div class='note muted'>大限（" + ("順行" if luck.get("forward") else "逆行") + f"，{luck.get('start_age')} 虛歲起）</div><div class='strip'>")
        for d in luck["daxian"]:
            out.append(f"<div class='cell{' now' if d['current'] else ''}'><div class='muted'>{d['ages'][0]}–{d['ages'][1]}歲</div><div><b>{_e(d['palace'])}</b></div><div>{_e(d['gz'])}</div><div class='muted'>{_e(d['changsheng'])}</div></div>")
        out.append("</div></div>")
    out.append("</div>")
    return "".join(out)


def liuyao(g: dict) -> str:
    out = ["<div class='paper bz'><div class='title'>六爻納甲 <span class='seal'>卦</span></div>", f"<div class='note'><b>{_e(g['name'])}</b>（{_e(g['palace'])}宮{_e(g['palace_elem'])}）世{g['shi']}應{g['ying']}・月建 {_e(g['month_branch'])}・日辰 {_e(g['day_gz'])}・旬空 {_e(g['kong_wang'])}" + (f"・變卦 {_e(g['changed']['name'])}" if g.get("changed") else "") + "</div>",
           "<div class='tw'><table><tr><th>爻</th><th>六神</th><th>六親</th><th>干支</th><th></th><th>世應</th><th>伏神</th><th>旺衰</th><th>變</th></tr>"]
    for r in reversed(g["lines"]):
        ch = g.get("changed")
        out.append(f"<tr style='{'background:#f3e8ff' if r['moving'] else ''}'><td>{r['pos']}</td><td>{_e(r['god'])}</td><td><b>{_e(r['relative'])}</b></td><td>{_e(r['stem'] + r['branch'])}</td>"
                   f"<td style='font-family:monospace'>{'▅▅▅▅▅' if r['yang'] else '▅▅　▅▅'}{' ●' if r['moving'] else ''}</td><td>{'世' if r['shi'] else '應' if r['ying'] else ''}</td><td class='muted'>{_e(r.get('hidden', ''))}</td>"
                   f"<td class='muted'>{_e('/'.join(r['notes']))}</td><td>{(_e(ch['line']['relative'] + ch['line']['stem'] + ch['line']['branch']) + '（' + _e(ch['relation']) + '）') if r['moving'] and ch else ''}</td></tr>")
    out.append("</table></div></div>")
    return "".join(out)


def qimen(c: dict) -> str:
    by = {p["palace"]: p for p in c.get("palaces", [])}
    out = [f"<div class='paper'><div class='title'>奇門遁甲 <span class='seal'>九宮</span></div><div class='note muted'>{_e(c.get('ju', ''))} · 值符 {_e(c.get('zhifu', ''))} · 值使 {_e(c.get('zhishi', ''))}</div><div class='qm'>"]
    for n in (4, 9, 2, 3, 5, 7, 8, 1, 6):
        p = by.get(n, {})
        cls = "good" if p.get("gate_cls") == "吉" else "bad" if p.get("gate_cls") == "凶" else ""
        out.append(f"<div class='c {cls}{' fu' if p.get('god') == '值符' else ''}'><div class='t'><span>{_e(p.get('god', ''))}</span><span class='muted'>{_e(p.get('name', ''))}</span></div>"
                   f"<div class='m'><b>{_e(p.get('star', ''))}</b><b>{_e(p.get('sky_stem', ''))}</b></div><div class='m'><span>{_e(p.get('gate', ''))}</span><span class='muted'>{_e(p.get('earth_stem', ''))}</span></div></div>")
    out.append("</div></div>")
    return "".join(out)


def liuren(c: dict) -> str:
    out = [f"<div class='paper bz'><div class='title'>大六壬課式 <span class='seal'>三傳</span></div><div class='note muted'>{_e(c.get('yue_jiang', ''))}將加{_e(c.get('occupy', ''))}時 · 天盤／地盤・天將</div><div class='lr'>"]
    for x in c.get("heaven_plate", []):
        out.append(f"<div class='c'><div class='g'>{_e((x.get('general') or '')[:1])}</div><b>{_e(x['sky'])}</b><div class='muted'>{_e(x['ground'])}</div></div>")
    out.append("</div><table><tr>" + "".join(f"<th>{_e(k['name'])}</th>" for k in c.get("courses", [])) + "</tr><tr>" + "".join(f"<td class='big'>{_e(k['upper'])}</td>" for k in c.get("courses", [])) + "</tr><tr>"
               + "".join(f"<td class='muted'>{_e(k['lower'])}{'·' + _e(k.get('general', '')) if k.get('general') else ''}</td>" for k in c.get("courses", [])) + "</tr></table>")
    tr = c.get("transmissions", []); tg = c.get("transmission_generals", [])
    out.append(f"<div class='note'><span class='muted'>{_e(c.get('kind', ''))}</span> · 三傳：" + "　".join(f"<b>{'初中末'[i]} {_e(t)}</b><span class='muted'>（{_e(tg[i]) if i < len(tg) else ''}）</span>" for i, t in enumerate(tr)) + "</div></div>")
    return "".join(out)


def readings_html(readings: dict) -> str:
    rows = []
    for k, v in readings.items():
        lab = LABELS.get(k, k)
        if lab is None:
            continue
        rows.append(f"<div class='k'>{_e(lab)}</div><div>{_e('、'.join(map(str, v)) if isinstance(v, list) else v)}</div>")
    return "<div class='paper'><div class='kv'>" + "".join(rows) + "</div></div>"


def xingming(c: dict) -> str:
    chars = "".join(f"<div class='cell'><div class='ch big'>{_e(x['char'])}</div><div class='muted' style='font-size:11px'>{_e(x['role'])}</div><div><b>{x['strokes']}</b> 畫</div></div>" for x in c.get("chars", []))
    rows = "".join(f"<tr><td style='text-align:left'><b>{_e(g['name'])}</b><div class='muted' style='font-size:11px'>{_e(g['role'])}</div></td><td class='nw'><b>{g['number']}</b>{('<div class=muted style=font-size:11px>數理 ' + str(g['shuli']) + '</div>') if g['shuli'] != g['number'] else ''}</td>"
                   f"<td class='nw'><span class='ch e-{ {'木':'wood','火':'fire','土':'earth','金':'metal','水':'water'}[g['element']] }'>{_e(g['element'])}</span>{_e(g['yinyang'])}</td>"
                   f"<td class='nw {'v-fav' if g['luck'] == '吉' else 'v-unf' if g['luck'] == '凶' else 'v-neu'}'>{_e(g['luck'])}</td><td class='nw'>{_e(g.get('bazi') or '—')}</td>"
                   f"<td style='text-align:left;font-size:11.5px'>{_e(g['formula'])}</td></tr>" for g in c.get("grids", []))
    rel = c.get("relations", {})
    rl = "　".join(f"<span class='muted'>{_e(k)}</span> {_e(v.get('text', ''))}（{_e(v.get('kind', ''))}）" for k, v in rel.items())
    bz = c.get("bazi") or {}
    bz_line = (f"<div class='note'><span class='muted'>八字喜用</span> {_e('、'.join(bz.get('favourable', [])))}　<span class='muted'>忌</span> {_e('、'.join(bz.get('avoid', [])) or '無')}　"
               f"<span class='muted'>日主</span> {_e(bz.get('day_master', ''))}{_e(bz.get('dm_elem', ''))} {_e(bz.get('strength', ''))}</div>") if bz and "error" not in bz else ""
    warn = "".join(f"<div class='note muted'>{_e(w)}</div>" for w in c.get("warnings", []))
    return (f"<div class='paper'><div class='title'>姓名學 <span class='seal'>五格</span></div><div class='head'>{_e(c.get('surname', ''))} {_e(c.get('given', ''))}　<span class='muted'>{_e(c.get('split_note', ''))}</span></div>"
            f"<div class='strip'>{chars}</div><div class='tw'><table><tr><th style='text-align:left'>格</th><th>數</th><th>五行</th><th>數理</th><th>對八字</th><th style='text-align:left'>算法</th></tr>{rows}</table></div>"
            f"<div class='note'><span class='muted'>三才</span> <b>{_e(c.get('sancai', ''))}</b>　{rl}</div>{bz_line}{warn}</div>")


def chart_html(chart) -> str:
    c, s = chart.chart or {}, chart.system
    try:
        if s == "bazi" and c.get("pillars"):
            return bazi(c)
        if s == "ziwei" and c.get("palaces"):
            return ziwei(c, chart.readings, chart.subject)
        if s == "liuyao" and c.get("hexagram", {}).get("lines"):
            return liuyao(c["hexagram"])
        if s == "qimen" and c.get("palaces"):
            return qimen(c)
        if s == "liuren" and c.get("courses"):
            return liuren(c)
        if s == "xingming" and c.get("grids"):
            return xingming(c)
    except Exception as e:  # noqa: BLE001
        return f"<div class='muted'>render error: {_e(e)}</div>"
    return ""
