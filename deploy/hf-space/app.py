"""Bazaar of Fates · 算命 — Hugging Face Space (Gradio SDK, free CPU).

A Gradio front end over the same engines, with the FastAPI app mounted alongside it
(/docs, /cast/{system}, /synthesis, /zeri …) so the API is usable from the Space too.
"""

from __future__ import annotations

import json
import os
from datetime import date, time

os.environ.setdefault("BAZAAR_STATIC_PATH", "/web")      # the Gradio UI owns "/"; the no-build page lives at /web
os.environ.setdefault("CORS_ORIGINS", "*")

import html

import gradio as gr

try:                                                     # ZeroGPU Spaces require at least one @spaces.GPU function at
    import spaces                                        # startup; nothing here needs a GPU, so this is a no-op stub
    @spaces.GPU(duration=1)
    def _zero_gpu_stub() -> str:
        return "ok"
except Exception:  # noqa: BLE001
    _zero_gpu_stub = None

from fortune import ask as AK, casting, focus as F, geo, love as LV, specialist as SP, zeri as Z
from fortune.api.main import app as api
from fortune.birth import BirthInput
from fortune.schemas import Chart
from fortune.interpret import interpret, interpret_synthesis, interpret_zeri

import render as R
from theme import CSS as THEME_CSS, HERO

SYSTEMS = [(f"{s['zh']} · {s['en']}", s["key"]) for s in casting.systems()]
PNG_JS = """() => {
  const run = () => {
    const el = document.querySelector('#board .paper') || document.querySelector('#board');
    if (!el) return;
    html2canvas(el, {scale: 2, backgroundColor: '#f3e9d2', useCORS: true}).then(cv => {
      const a = document.createElement('a'); a.download = 'bazaar-of-fates.png'; a.href = cv.toDataURL('image/png'); a.click();
    });
  };
  if (window.html2canvas) return run();
  const s = document.createElement('script'); s.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js'; s.onload = run; document.head.appendChild(s);
}"""
PURPOSES = [(f"{v['zh']} · {v['en']}", k) for k, v in Z.PURPOSES.items()]
LANGS = [("中文", "zh"), ("English", "en"), ("中文 + English", "both")]
TOPICS = [("自動分科 auto", "auto")] + [(f"{v['title']} · {v['en']}", k) for k, v in SP.SPECS.items()]
ASK_SYSTEMS = [(f"{v} · {k}", k) for k, v in AK.SYSTEMS.items()]
_SHEET = {"career": "事業方向", "wealth": "財性與財庫", "health": "體質與臟腑", "study": "學習型態與科系", "family": "六親宮位"}
DISCLAIMER = "僅供文化、教育與娛樂用途；命理不應作為財務、醫療或法律決策的依據。 Cultural / educational / entertainment only."


def _birth(name, d, t, gender, place, tst) -> BirthInput:
    d = date.fromisoformat(str(d).strip())
    tt = None
    if t and str(t).strip():
        h, m = str(t).strip().split(":")[:2]
        tt = time(int(h), int(m))
    lat = lon = None
    tz = 8.0
    hit = geo.lookup(place, d) if place else None
    if hit:
        lat, lon, tz = hit["latitude"], hit["longitude"], hit["tz_offset_hours"]
    import re as _re
    full = name.strip() if name and _re.match(r'^[\u3400-\u9fff\uf900-\ufaff　 ]{2,7}$', name.strip()) else None
    return BirthInput(full_name=full, name=name or None, birth_date=d, birth_time=tt, gender=gender or None, place=place or None,
                      latitude=lat, longitude=lon, tz_offset_hours=tz, true_solar_time=bool(tst))


def _focus_line(readings: dict) -> str:
    if readings.get("focus_topic"):
        return f"**問題主題：{readings['focus_topic']}**　本門派規則判斷：{readings.get('focus_verdict', '')}\n\n"
    return ""


def _share_url(request, **params) -> str:
    from urllib.parse import urlencode
    q = urlencode({k: v for k, v in params.items() if v not in (None, "", False)})
    host = request.headers.get("host", "") if request is not None else ""
    base = f"https://{host}" if host and not host.startswith(("localhost", "127.")) else f"http://{host}"
    return f"{base}/?{q}"


def cast_one(name, d, t, gender, place, tst, system, question, lang, read, request: gr.Request = None):
    try:
        b = _birth(name, d, t, gender, place, tst)
        chart = casting.cast(system, b, transits=(system == "astrology"))
        if question:
            topic = F.classify(question)
            fx = F.extract(chart, topic, {"male": True, "female": False}.get(gender or ""))
            chart.readings["focus_topic"] = F.topic_label(topic)
            chart.readings["focus_verdict"] = f"{fx['verdict']}（{fx['reason']}）"
        prose = interpret(chart, focus=question or None, lang=lang).interpretation if read else ""
        head = f"**{chart.system_en} · {chart.system_zh}** — {chart.subject}\n\n### {chart.summary}\n\n" + _focus_line(chart.readings)
        board = R.chart_html(chart)
        if not board:                                      # systems without a dedicated sheet: the key facts
            board = R.readings_html(chart.readings)
        chain = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(chart.reasoning_chain))
        url = _share_url(request, name=name, date=d, time=t, gender=gender, place=place, tst="1" if tst else "", system=system, q=question, lang=lang)
        share = f"<div class='share'>🔗 分享連結 Share：<a href='{html.escape(url)}' target='_blank'>{html.escape(url)}</a></div>"
        return (head, board, prose, chain, R.readings_html(chart.readings), json.dumps(chart.model_dump(mode="json"), ensure_ascii=False, indent=1), share)
    except Exception as e:  # noqa: BLE001
        return f"⚠️ {e}", "", "", "", "", "", ""


def synthesize(name, d, t, gender, place, tst, question, lang, read):
    try:
        b = _birth(name, d, t, gender, place, tst)
        charts = {k: casting.cast(k, b, transits=(k == "astrology")) for k in casting.REGISTRY}
        syn = F.synthesize(charts, F.classify(question), {"male": True, "female": False}.get(gender or ""))
        head = f"### {syn['summary']}\n\n一致：{'、'.join(syn['consensus']) or '—'}　相左：{'、'.join(syn['conflicts']) or '—'}"
        cls = {"favourable": "v-fav", "neutral": "v-neu", "unfavourable": "v-unf"}
        rows = "".join(
            f"<tr class='{'conflict' if r['verdict'] != 'neutral' and r['verdict'] != syn['lean'] else ''}'><td style='text-align:left'><b>{R._e(r['system_zh'])}</b><div class='muted' style='font-size:11px'>{R._e(r['system_en'])}</div></td>"
            f"<td class='{cls[r['verdict']]}'>{R._e(r['verdict_zh'])}</td><td style='text-align:left'>{R._e(r['reason'])}</td></tr>" for r in syn["systems"])
        table = f"<div class='paper'><div class='title'>十三術會診 <span class='seal'>{R._e(syn['lean_zh'])}</span></div><div class='tw'><table><tr><th style='text-align:left'>系統</th><th>判斷</th><th style='text-align:left'>依據（該門派規則）</th></tr>{rows}</table></div></div>"
        prose = interpret_synthesis(syn, focus=question, lang=lang) if read else ""
        return head, table, prose
    except Exception as e:  # noqa: BLE001
        return f"⚠️ {e}", "", ""


def pick_dates(name, d, t, gender, place, tst, purpose, start, end, lang, read):
    try:
        b = _birth(name, d, t, gender, place, tst)
        s, e = date.fromisoformat(str(start).strip()), date.fromisoformat(str(end).strip())
        if e < s or (e - s).days > 120:
            return "⚠️ 區間需在 121 天內", [], ""
        out = Z.select(b, s, e, purpose, top=10)
        by = {x["date"]: x for x in out["days"]}
        rows = []
        for i, dd in enumerate(out["best"], 1):
            x = by[dd]
            hours = "、".join(f"{h['branch']}時" for h in x.get("hours", []) if h.get("best"))
            why = "；".join(f"{r['src']}{r['delta']:+} {r['text']}" for r in x["reasons"][:4])
            rows.append(f"<tr><td class='nw'>#{i}</td><td class='nw'><b>{dd}</b><div class='muted' style='font-size:11px'>{R._e(x['weekday'])} · 農曆 {R._e(x['lunar'])}</div></td><td class='nw'>{R._c(x['gz']['day'][0])}{R._c(x['gz']['day'][1])}</td>"
                        f"<td class='star'>{'★' * x['grade']}{'☆' * (5 - x['grade'])}</td><td class='nw'>{x['score']:+}</td><td class='nw'>{R._e(hours)}</td><td style='text-align:left'>{R._e('、'.join(x['qimen']['lucky_dirs'][:3]))}</td><td style='text-align:left;font-size:12px'>{R._e(why)}</td></tr>")
        table = (f"<div class='paper'><div class='title'>擇日 · {R._e(out['purpose_label'])} <span class='seal'>吉日</span></div>"
                 f"<div class='tw'><table><tr><th>#</th><th>日期</th><th>日柱</th><th>等級</th><th>分數</th><th>吉時</th><th style='text-align:left'>吉方</th><th style='text-align:left'>依據</th></tr>{''.join(rows)}</table></div>"
                 f"<div class='note'><span class='muted'>忌日：</span>{R._e('、'.join(out['avoid'][:20]) or '—')}</div></div>")
        head = f"### 擇日 {out['purpose_label']} {out['start']} → {out['end']}"
        prose = interpret_zeri(out, lang=lang) if read else ""
        return head, table, prose
    except Exception as e:  # noqa: BLE001
        return f"⚠️ {e}", "", ""


def _reasons(rs, n=4):
    return "；".join(f"{r['src']}{r['delta']:+} {r['text']}" for r in rs[:n])


def love_consult(name, d, t, gender, place, tst, question, lang, read, p_name, p_date, p_time, p_gender, p_place, years):
    try:
        b = _birth(name, d, t, gender, place, tst)
        partner = _birth(p_name, p_date, p_time, p_gender, p_place, tst) if p_date and str(p_date).strip() else None
        out = LV.consult(b, question or None, partner=partner, years=int(years or 8), read=bool(read), lang=lang)
        head = f"### 感情專科 · {R._e(out['subject'])}\n\n問：{R._e(question or '整體感情運')}　子題：**{R._e(out['intent_label'])}**"
        # 命 — natal disposition
        nat = "".join(f"<tr><td style='text-align:left'><b>{R._e(r['system_zh'])}</b></td><td class='nw'>{r['score']:+.1f}</td>"
                      f"<td style='text-align:left;font-size:12px'>{R._e('；'.join(r['reasons']) or '—')}</td></tr>" for r in out["natal"]["systems"])
        natal_html = (f"<div class='paper'><div class='title'>命 · 感情格局 <span class='seal'>{R._e(out['natal']['label'])}</span></div>"
                      f"<div class='tw'><table><tr><th style='text-align:left'>系統</th><th>分</th><th style='text-align:left'>依據</th></tr>{nat}</table></div></div>")
        # 運 — the years
        yrs = "".join(f"<tr class='{'now' if y['marriage_sign'] else ''}'><td class='nw'><b>{y['year']}</b><div class='muted' style='font-size:11px'>{y['age']} 歲</div></td>"
                      f"<td class='star'>{'★' * y['grade']}{'☆' * (5 - y['grade'])}</td><td class='nw'>{y['score']:+}</td><td class='nw'>{'♥ 婚緣' if y['marriage_sign'] else ''}</td>"
                      f"<td style='text-align:left;font-size:12px'>{R._e(_reasons(y['reasons']))}</td></tr>" for y in out["timing"]["years"])
        timing_html = (f"<div class='paper'><div class='title'>運 · 桃花年／婚緣年 <span class='seal'>{R._e('、'.join(map(str, out['timing']['best'])) or '—')}</span></div>"
                       f"<div class='tw'><table><tr><th>年</th><th>等級</th><th>分</th><th></th><th style='text-align:left'>依據（八字流年・紫微流年四化・西洋行運・daśā）</th></tr>{yrs}</table></div>"
                       f"<div class='note'><span class='muted'>宜守：</span>{R._e('、'.join(map(str, out['timing']['caution'])) or '—')}</div></div>")
        match_html = ""
        if out["match"]:
            m = out["match"]
            mr = "".join(f"<tr><td class='nw'>{R._e(r['src'])}</td><td class='nw {'v-fav' if r['delta'] > 0 else 'v-unf' if r['delta'] < 0 else 'v-neu'}'>{r['delta']:+}</td>"
                         f"<td style='text-align:left;font-size:12px'>{R._e(r['text'])}</td></tr>" for r in m["reasons"])
            match_html = (f"<div class='paper'><div class='title'>合婚 · {R._e(m['a'].split(' · ')[0])} ✕ {R._e(m['b'].split(' · ')[0])} <span class='seal'>{R._e(m['label'])}</span></div>"
                          f"<div class='tw'><table><tr><th>來源</th><th>分</th><th style='text-align:left'>依據</th></tr>{mr}</table></div>"
                          f"<div class='note'>{R._e(m['facts'].get('合盤 composite', ''))}</div></div>")
        prose = out.get("interpretation", "") if read else ""
        return head, natal_html, timing_html, match_html, prose, json.dumps(out, ensure_ascii=False, indent=1, default=str)
    except Exception as e:  # noqa: BLE001
        return f"⚠️ {e}", "", "", "", "", ""


def _fact(v) -> str:
    if isinstance(v, dict):
        return "<br>".join(f"<span class='muted'>{R._e(k)}</span> {R._e(x)}" for k, x in v.items())
    if isinstance(v, list):
        return "、".join(R._e(x) for x in v)
    return R._e(v)


def specialist_consult(name, d, t, gender, place, tst, question, lang, read, topic, years):
    try:
        b = _birth(name, d, t, gender, place, tst)
        topic = SP.route(question) if topic == "auto" else topic
        if topic == "love":
            head, natal_html, timing_html, match_html, prose, raw = love_consult(name, d, t, gender, place, tst, question, lang, read, "", "", "", "", "", years)
            return head + "\n\n（感情問題已轉給感情專科；要合婚請用 Love 分頁）", natal_html, timing_html, match_html, prose, raw
        out = SP.consult(topic, b, question or None, years=int(years or 8), read=bool(read), lang=lang)
        sp = SP.spec(topic)
        head = f"### {R._e(sp['title'])} · {R._e(out['subject'])}\n\n問：{R._e(question or '整體' + sp['zh'] + '運')}　子題：**{R._e(out['intent_label'])}**"
        nat = "".join(f"<tr><td style='text-align:left'><b>{R._e(r['system_zh'])}</b></td><td class='nw'>{r['score']:+.1f}</td>"
                      f"<td style='text-align:left;font-size:12px'>{R._e('；'.join(r['reasons']) or '—')}</td></tr>" for r in out["natal"]["systems"])
        natal_html = (f"<div class='paper'><div class='title'>命 · {R._e(sp['zh'])}格局 <span class='seal'>{R._e(out['natal']['label'])}</span></div>"
                      f"<div class='tw'><table><tr><th style='text-align:left'>系統</th><th>分</th><th style='text-align:left'>依據</th></tr>{nat}</table></div></div>")
        tl = out["timing"]["sign_label"]
        yrs = "".join(f"<tr class='{'now' if y['sign'] else ''}'><td class='nw'><b>{y['year']}</b><div class='muted' style='font-size:11px'>{y['age']} 歲</div></td>"
                      f"<td class='star'>{'★' * y['grade']}{'☆' * (5 - y['grade'])}</td><td class='nw'>{y['score']:+}</td><td class='nw'>{'◆ ' + R._e(tl) if y['sign'] else ''}</td>"
                      f"<td style='text-align:left;font-size:12px'>{R._e(_reasons(y['reasons']))}</td></tr>" for y in out["timing"]["years"])
        timing_html = (f"<div class='paper'><div class='title'>運 · {R._e(sp['zh'])}流年 <span class='seal'>{R._e('、'.join(map(str, out['timing']['best'])) or '—')}</span></div>"
                       f"<div class='tw'><table><tr><th>年</th><th>等級</th><th>分</th><th></th><th style='text-align:left'>依據（八字流年・紫微流年四化・西洋行運・daśā）</th></tr>{yrs}</table></div>"
                       f"<div class='note'><span class='muted'>{'需注意' if topic == 'health' else '宜守'}：</span>{R._e('、'.join(map(str, out['timing']['caution'])) or '—')}</div></div>")
        ex = out["extra"]
        rows = "".join(f"<tr><td style='text-align:left;white-space:nowrap'><b>{R._e(k)}</b></td><td style='text-align:left;font-size:12px'>{_fact(v)}</td></tr>" for k, v in ex.get("facts", {}).items())
        extra_html = (f"<div class='paper'><div class='title'>{R._e(_SHEET[topic])}</div><div class='tw'><table>{rows}</table></div>"
                      f"<div class='note'>{R._e(ex.get('summary', ''))}</div></div>") if rows else ""
        prose = out.get("interpretation", "") if read else ""
        return head, natal_html, timing_html, extra_html, prose, json.dumps(out, ensure_ascii=False, indent=1, default=str)
    except Exception as e:  # noqa: BLE001
        return f"⚠️ {e}", "", "", "", "", ""


def ask_now(system, question, at, place, numbers, text, coins, lang, read):
    try:
        from datetime import datetime as _dt
        nums = [int(x) for x in str(numbers).replace("，", ",").split(",") if x.strip()] if numbers and str(numbers).strip() else None
        cs = [int(x) for x in str(coins).replace("，", ",").split(",") if x.strip()] if coins and str(coins).strip() else None
        out = AK.ask(system, question or None, at=_dt.fromisoformat(at.strip()) if at and at.strip() else None, place=place or None,
                     numbers=nums, text=(text or None), coins=cs, read=bool(read), lang=lang)
        v = out["verdict"]
        head = (f"### {R._e(out['system_zh'])}問事 · {R._e(out['at'])}{(' · ' + R._e(place)) if place else ''}（{R._e(out['method'])}）\n\n"
                f"問：{R._e(question or '—')}　分題：**{R._e(out['topic_label'])}**　→ **{R._e(v['verdict_zh'])}**（{v['score']:+}）")
        board = R.chart_html(Chart(**out["chart"])) if system in ("qimen", "liuren", "liuyao") else ""
        if not board:
            ch = out["chart"]
            diag = "<br>".join(R._e(x) for x in ch["chart"].get("diagram", []))
            board = f"<div class='paper'><div class='title'>{R._e(ch['summary'])}</div><div style='font-family:monospace;font-size:18px;line-height:1.5'>{diag}</div></div>" if diag else ""
        chain = "<div class='paper'><div class='title'>起局</div>" + "".join(f"<div style='font-size:12.5px;color:#1f1a12;padding:3px 0;border-bottom:1px dashed rgba(184,154,90,.4)'><b style='color:#b4302b'>{i}.</b> {R._e(x)}</div>" for i, x in enumerate(out["chart"]["reasoning_chain"], 1)) + "</div>"
        rows = "".join(f"<tr><td style='text-align:left;font-size:12.5px'>{R._e(r)}</td></tr>" for r in v["reasons"])
        facts = "".join(f"<tr><td style='text-align:left;white-space:nowrap'><b>{R._e(k)}</b></td><td style='text-align:left;font-size:12px'>{_fact(x)}</td></tr>" for k, x in v["facts"].items())
        verdict = (f"<div class='paper'><div class='title'>斷 <span class='seal'>{R._e(v['verdict_zh'])} {v['score']:+}</span></div><div class='tw'><table>{rows}</table></div>"
                   f"<div class='note'>{R._e(v.get('timing_hint', ''))}{('　吉方：' + R._e('、'.join(v['lucky_directions']))) if v.get('lucky_directions') else ''}</div>"
                   f"<div class='tw'><table>{facts}</table></div></div>")
        prose = out.get("interpretation", "") if read else ""
        return head, board + chain, verdict, prose, json.dumps(out, ensure_ascii=False, indent=1, default=str)
    except Exception as e:  # noqa: BLE001
        return f"⚠️ {e}", "", "", "", ""


with gr.Blocks(title="Bazaar of Fates · 算命") as demo:
    gr.HTML(HERO)
    with gr.Row():
        name = gr.Textbox(label="Name 稱呼", value="Mei", scale=1)
        bdate = gr.Textbox(label="Birth date 出生日期 (YYYY-MM-DD)", value="1990-06-15", scale=1)
        btime = gr.Textbox(label="Birth time 時刻 (HH:MM，空白＝正午)", value="14:30", scale=1)
        gender = gr.Dropdown(label="Gender 性別", choices=[("female 女", "female"), ("male 男", "male")], value="female", scale=1)
        place = gr.Textbox(label="Birthplace 出生地", value="台北", scale=1)
        tst = gr.Checkbox(label="真太陽時", value=False, scale=0)
    with gr.Row():
        question = gr.Textbox(label="Ask about 想問（可空）", placeholder="事業 / 感情 / 財運 / 健康 …", scale=3)
        lang = gr.Dropdown(label="Reading 解讀語言", choices=LANGS, value="zh", scale=1)
        read = gr.Checkbox(label="附解讀 reading", value=True, scale=0)

    with gr.Tab("Single 單盤"):
        system = gr.Dropdown(label="System 系統", choices=SYSTEMS, value="bazi")
        go = gr.Button("排 盤 · Cast", variant="primary")
        head = gr.Markdown()
        board = gr.HTML(label="命盤", elem_id="board")
        with gr.Row():
            share = gr.HTML()
            png = gr.Button("⬇ 下載盤面 PNG · Save as image", variant="secondary", scale=0)
        prose = gr.Markdown(label="解讀")
        with gr.Accordion("排盤步驟 Casting steps", open=False):
            chain = gr.Markdown()
        with gr.Accordion("命盤要素 Chart elements", open=False):
            kv = gr.HTML()
        with gr.Accordion("raw JSON", open=False):
            raw = gr.Code(language="json")
        outs = [head, board, prose, chain, kv, raw, share]
        go.click(cast_one, [name, bdate, btime, gender, place, tst, system, question, lang, read], outs)
        png.click(None, js=PNG_JS)

    with gr.Tab("Synthesis 綜合會診"):
        go2 = gr.Button("會 診 · 十三術同問", variant="primary")
        head2 = gr.Markdown(); table2 = gr.HTML(); prose2 = gr.Markdown()
        go2.click(synthesize, [name, bdate, btime, gender, place, tst, question, lang, read], [head2, table2, prose2])

    with gr.Tab("Dates 擇日"):
        with gr.Row():
            purpose = gr.Dropdown(label="Purpose 目的", choices=PURPOSES, value="wedding")
            start = gr.Textbox(label="From 起", value=date.today().isoformat())
            end = gr.Textbox(label="To 迄（≤121 天）", value=date.fromordinal(date.today().toordinal() + 60).isoformat())
        go3 = gr.Button("擇 日 · Pick dates", variant="primary")
        head3 = gr.Markdown(); table3 = gr.HTML(); prose3 = gr.Markdown()
        go3.click(pick_dates, [name, bdate, btime, gender, place, tst, purpose, start, end, lang, read], [head3, table3, prose3])

    with gr.Tab("Love 感情專科"):
        gr.Markdown("專看感情的命理師：上方填自己的生辰與想問的問題（何時有緣／合不合／復合／該不該分開／婚姻／第三者）；要合婚就填對方。")
        with gr.Row():
            p_name = gr.Textbox(label="對方稱呼 Partner", scale=1)
            p_date = gr.Textbox(label="對方出生日期 (YYYY-MM-DD，可空)", scale=1)
            p_time = gr.Textbox(label="對方時刻 (HH:MM)", scale=1)
            p_gender = gr.Dropdown(label="對方性別", choices=[("—", ""), ("female 女", "female"), ("male 男", "male")], value="", scale=1)
            p_place = gr.Textbox(label="對方出生地", scale=1)
            years = gr.Number(label="看幾年 Years", value=8, precision=0, scale=0)
        go4 = gr.Button("問 感 情 · Ask the love reader", variant="primary")
        head4 = gr.Markdown(); natal4 = gr.HTML(); timing4 = gr.HTML(); match4 = gr.HTML(); prose4 = gr.Markdown()
        with gr.Accordion("raw JSON", open=False):
            raw4 = gr.Code(language="json")
        go4.click(love_consult, [name, bdate, btime, gender, place, tst, question, lang, read, p_name, p_date, p_time, p_gender, p_place, years],
                  [head4, natal4, timing4, match4, prose4, raw4])

    with gr.Tab("專科 Consult"):
        gr.Markdown("事業・財運・健康・學業・家庭，各一位只看一題的命理師：上方填生辰與問題，這裡選科（或自動分科）。命（四系統評分）→ 運（逐年，每一分列依據）→ 專科表。健康科不是醫療建議。")
        with gr.Row():
            topic = gr.Dropdown(label="Specialist 專科", choices=TOPICS, value="auto", scale=2)
            years5 = gr.Number(label="看幾年 Years", value=8, precision=0, scale=0)
        go5 = gr.Button("問 專 科 · Ask the specialist", variant="primary")
        head5 = gr.Markdown(); natal5 = gr.HTML(); timing5 = gr.HTML(); extra5 = gr.HTML(); prose5 = gr.Markdown()
        with gr.Accordion("raw JSON", open=False):
            raw5 = gr.Code(language="json")
        go5.click(specialist_consult, [name, bdate, btime, gender, place, tst, question, lang, read, topic, years5], [head5, natal5, timing5, extra5, prose5, raw5])

    with gr.Tab("問事 Ask"):
        gr.Markdown("不用生辰：以**問的這一刻**起局（奇門時盤・六壬時課・梅花・六爻・小六壬）。梅花可給 1–3 個數字或一句話起卦；六爻可輸入六次擲錢（自初爻起，6 老陰／7 少陽／8 少陰／9 老陽）。上方「想問」欄即問題。")
        with gr.Row():
            ask_sys = gr.Dropdown(label="System 術數", choices=ASK_SYSTEMS, value="qimen", scale=2)
            ask_at = gr.Textbox(label="時刻 (YYYY-MM-DDTHH:MM，空白＝現在)", scale=2)
            ask_place = gr.Textbox(label="地點（時區用，可空）", value="台北", scale=1)
        with gr.Row():
            ask_numbers = gr.Textbox(label="梅花 數字（如 3,7,9）", scale=1)
            ask_text = gr.Textbox(label="梅花 字占（一句話）", scale=2)
            ask_coins = gr.Textbox(label="六爻 擲錢（如 7,8,9,8,6,7）", scale=1)
        go6 = gr.Button("起 局 · Ask", variant="primary")
        head6 = gr.Markdown(); board6 = gr.HTML(); verdict6 = gr.HTML(); prose6 = gr.Markdown()
        with gr.Accordion("raw JSON", open=False):
            raw6 = gr.Code(language="json")
        go6.click(ask_now, [ask_sys, question, ask_at, ask_place, ask_numbers, ask_text, ask_coins, lang, read], [head6, board6, verdict6, prose6, raw6])

    gr.HTML(f"<div style='text-align:center;color:#9c8c68;font-size:12px;letter-spacing:.1em;padding:14px 0 4px'>{DISCLAIMER}</div>")

    def load_from_url(request: gr.Request):
        """?name=&date=&time=&gender=&place=&tst=1&system=&q=&lang= → fill the form and cast at once."""
        p = dict(request.query_params) if request is not None else {}
        if not p.get("date"):
            return [gr.update()] * 9 + [gr.update()] * len(outs)
        vals = [p.get("name", ""), p["date"], p.get("time", ""), p.get("gender") or None, p.get("place", ""), p.get("tst") == "1",
                p.get("system", "bazi"), p.get("q", ""), p.get("lang", "zh")]
        res = cast_one(*vals, True, request)
        return vals + list(res)

    demo.load(load_from_url, None, [name, bdate, btime, gender, place, tst, system, question, lang] + outs)

# Hugging Face's Gradio runtime pre-binds port 7860 for `demo.launch()`, so we must launch the Blocks
# (not run uvicorn ourselves) and then graft the FastAPI routes (/cast, /synthesis, /zeri, /docs, /web …)
# onto Gradio's own FastAPI app.
if __name__ == "__main__":
    import threading
    _theme = gr.themes.Base(primary_hue="amber", neutral_hue="slate")
    try:
        app, _local, _share = demo.launch(server_name="0.0.0.0", prevent_thread_lock=True, ssr_mode=False, theme=_theme, css=THEME_CSS)
    except TypeError:                                  # gradio < 6: css/theme live on Blocks()
        demo.css = THEME_CSS
        app, _local, _share = demo.launch(server_name="0.0.0.0", prevent_thread_lock=True, ssr_mode=False)
    app.include_router(api.router)          # /cast, /synthesis, /zeri, /docs … on the same port
    if os.path.exists("web/index.html"):     # the no-build static page, shipped alongside app.py in the Space
        from fastapi.staticfiles import StaticFiles
        app.mount("/web", StaticFiles(directory="web", html=True), name="web")
    threading.Event().wait()                # keep the process alive (block_thread() returns at once under HF's runtime)
