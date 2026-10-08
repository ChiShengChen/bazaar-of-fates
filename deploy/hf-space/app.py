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

import gradio as gr

from fortune import casting, focus as F, geo, zeri as Z
from fortune.api.main import app as api
from fortune.birth import BirthInput
from fortune.interpret import interpret, interpret_synthesis, interpret_zeri

SYSTEMS = [(f"{s['zh']} · {s['en']}", s["key"]) for s in casting.systems()]
PURPOSES = [(f"{v['zh']} · {v['en']}", k) for k, v in Z.PURPOSES.items()]
LANGS = [("中文", "zh"), ("English", "en"), ("中文 + English", "both")]
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
    return BirthInput(name=name or None, birth_date=d, birth_time=tt, gender=gender or None, place=place or None,
                      latitude=lat, longitude=lon, tz_offset_hours=tz, true_solar_time=bool(tst))


def _kv(readings: dict) -> list[list[str]]:
    return [[k, "、".join(map(str, v)) if isinstance(v, list) else str(v)] for k, v in readings.items()]


def cast_one(name, d, t, gender, place, tst, system, question, lang, read):
    try:
        b = _birth(name, d, t, gender, place, tst)
        chart = casting.cast(system, b, transits=(system == "astrology"))
        if question:
            topic = F.classify(question)
            fx = F.extract(chart, topic, {"male": True, "female": False}.get(gender or ""))
            chart.readings["focus_topic"] = F.topic_label(topic)
            chart.readings["focus_verdict"] = f"{fx['verdict']}（{fx['reason']}）"
        prose = interpret(chart, focus=question or None, lang=lang).interpretation if read else ""
        return (f"**{chart.system_en} · {chart.system_zh}** — {chart.subject}\n\n### {chart.summary}",
                "\n".join(f"{i + 1}. {c}" for i, c in enumerate(chart.reasoning_chain)), _kv(chart.readings), prose,
                json.dumps(chart.model_dump(mode="json"), ensure_ascii=False, indent=1))
    except Exception as e:  # noqa: BLE001
        return f"⚠️ {e}", "", [], "", ""


def synthesize(name, d, t, gender, place, tst, question, lang, read):
    try:
        b = _birth(name, d, t, gender, place, tst)
        charts = {k: casting.cast(k, b, transits=(k == "astrology")) for k in casting.REGISTRY}
        syn = F.synthesize(charts, F.classify(question), {"male": True, "female": False}.get(gender or ""))
        rows = [[r["system_zh"], r["verdict_zh"], r["reason"]] for r in syn["systems"]]
        head = f"### {syn['summary']}\n\n一致：{'、'.join(syn['consensus']) or '—'}　相左：{'、'.join(syn['conflicts']) or '—'}"
        prose = interpret_synthesis(syn, focus=question, lang=lang) if read else ""
        return head, rows, prose
    except Exception as e:  # noqa: BLE001
        return f"⚠️ {e}", [], ""


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
            rows.append([f"#{i}", dd, x["weekday"], x["gz"]["day"], "★" * x["grade"], f"{x['score']:+}",
                         "、".join(f"{h['branch']}時" for h in x.get("hours", []) if h.get("best")),
                         "、".join(x["qimen"]["lucky_dirs"][:3]),
                         "；".join(f"{r['src']}{r['delta']:+} {r['text']}" for r in x["reasons"][:4])])
        head = f"### 擇日 {out['purpose_label']} {out['start']} → {out['end']}\n\n忌日：{'、'.join(out['avoid'][:15]) or '—'}"
        prose = interpret_zeri(out, lang=lang) if read else ""
        return head, rows, prose
    except Exception as e:  # noqa: BLE001
        return f"⚠️ {e}", [], ""


with gr.Blocks(title="Bazaar of Fates · 算命") as demo:
    gr.Markdown("# 🔮 Bazaar of Fates · 算命\n十三套傳統命理 · 一個生辰 · 確定性命盤 — 西洋占星 · 八字 · 紫微斗數 · 梅花易數 · 六爻 · 小六壬 · 四柱推命 · 七政四餘 · 鐵板神數 · 奇門遁甲 · 大六壬 · 太乙神數 · Jyotiṣa　"
                "[GitHub](https://github.com/ChiShengChen/bazaar-of-fates) · `pip install bazaar-of-fates` · [API docs](docs) · [static UI](web/)")
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
        go = gr.Button("Cast 排盤", variant="primary")
        head = gr.Markdown()
        with gr.Row():
            chain = gr.Markdown(label="排盤步驟")
            kv = gr.Dataframe(headers=["item", "value"], label="命盤要素", wrap=True)
        prose = gr.Markdown(label="解讀")
        with gr.Accordion("raw JSON", open=False):
            raw = gr.Code(language="json")
        go.click(cast_one, [name, bdate, btime, gender, place, tst, system, question, lang, read], [head, chain, kv, prose, raw])

    with gr.Tab("Synthesis 綜合會診"):
        go2 = gr.Button("Synthesize 十三套會診", variant="primary")
        head2 = gr.Markdown(); table2 = gr.Dataframe(headers=["系統", "判斷", "依據"], wrap=True); prose2 = gr.Markdown()
        go2.click(synthesize, [name, bdate, btime, gender, place, tst, question, lang, read], [head2, table2, prose2])

    with gr.Tab("Dates 擇日"):
        with gr.Row():
            purpose = gr.Dropdown(label="Purpose 目的", choices=PURPOSES, value="wedding")
            start = gr.Textbox(label="From 起", value=date.today().isoformat())
            end = gr.Textbox(label="To 迄（≤121 天）", value=date.fromordinal(date.today().toordinal() + 60).isoformat())
        go3 = gr.Button("Pick dates 擇日", variant="primary")
        head3 = gr.Markdown(); table3 = gr.Dataframe(headers=["#", "日期", "週", "日柱", "等級", "分數", "吉時", "吉方", "依據"], wrap=True); prose3 = gr.Markdown()
        go3.click(pick_dates, [name, bdate, btime, gender, place, tst, purpose, start, end, lang, read], [head3, table3, prose3])

    gr.Markdown(f"<sub>{DISCLAIMER}</sub>")

# Hugging Face's Gradio runtime pre-binds port 7860 for `demo.launch()`, so we must launch the Blocks
# (not run uvicorn ourselves) and then graft the FastAPI routes (/cast, /synthesis, /zeri, /docs, /web …)
# onto Gradio's own FastAPI app.
if __name__ == "__main__":
    app, _local, _share = demo.launch(server_name="0.0.0.0", prevent_thread_lock=True, theme=gr.themes.Soft(primary_hue="purple"))
    app.include_router(api.router)
    demo.block_thread()
