"use client";
import { useEffect, useState } from "react";
import {
  apiBase, getSystems, getTimeline, streamReading, getSynastry,
  SystemInfo, Reading, Timeline, Synastry,
} from "@/lib/api";
import { ChartView } from "./_components/ChartView";
import { Houses } from "./_components/Houses";
import { TimelineView } from "./_components/TimelineView";
import { SynastryView } from "./_components/SynastryView";
import { BirthFields, FormState, emptyForm, toBirth } from "./_components/BirthFields";

const HOUSE_OPTS = [
  ["whole_sign", "whole-sign 整星座"], ["equal", "Equal 等宮"], ["placidus", "Placidus 不等宮"],
  ["koch", "Koch 不等宮"], ["regiomontanus", "Regiomontanus 不等宮"], ["campanus", "Campanus 不等宮"],
];

export default function Page() {
  const [systems, setSystems] = useState<SystemInfo[]>([]);
  const [sys, setSys] = useState("bazi");
  const [mode, setMode] = useState<"single" | "synastry">("single");
  const [houseSystem, setHouseSystem] = useState("whole_sign");
  const [transits, setTransits] = useState(false);
  const [focus, setFocus] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reading, setReading] = useState<Reading | null>(null);
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [synastry, setSynastry] = useState<Synastry | null>(null);

  const [formA, setFormA] = useState<FormState>(emptyForm({ name: "Mei 小美", gender: "female", time: "14:30", place: "Taipei 台北", lat: "25.04", lon: "121.56" }));
  const [formB, setFormB] = useState<FormState>(emptyForm({ name: "Ken 阿肯", gender: "male", date: "1988-11-02", time: "09:15", place: "Taipei 台北", lat: "25.04", lon: "121.56" }));
  const setA = (k: keyof FormState, v: string) => setFormA((f) => ({ ...f, [k]: v }));
  const setB = (k: keyof FormState, v: string) => setFormB((f) => ({ ...f, [k]: v }));

  useEffect(() => { getSystems().then(setSystems).catch((e) => setErr(String(e.message || e))); }, []);

  async function cast() {
    setBusy(true); setErr(null); setReading(null); setTimeline(null);
    const b = toBirth(formA);
    getTimeline(sys, b).then(setTimeline).catch(() => setTimeline(null));
    try {
      let acc = "";
      await streamReading(
        sys, b, focus || null, houseSystem, transits,
        (chart) => setReading({ ...(chart as Reading), interpretation: "" }),
        (delta) => { acc += delta; setReading((r) => (r ? { ...r, interpretation: acc } : r)); },
      );
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  }

  async function compare() {
    setBusy(true); setErr(null); setSynastry(null);
    try {
      setSynastry(await getSynastry(toBirth(formA), toBirth(formB), focus || null, houseSystem));
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  }

  function exportPng() {
    const svg = document.querySelector("#chart-area svg") as SVGSVGElement | null;
    if (!svg) return;
    const w = Number(svg.getAttribute("width")) || svg.viewBox.baseVal.width || 360;
    const h = Number(svg.getAttribute("height")) || svg.viewBox.baseVal.height || 360;
    const xml = new XMLSerializer().serializeToString(svg);
    const img = new Image();
    img.onload = () => {
      const scale = 2;
      const cv = document.createElement("canvas"); cv.width = w * scale; cv.height = h * scale;
      const ctx = cv.getContext("2d")!;
      ctx.fillStyle = "#0b0b10"; ctx.fillRect(0, 0, cv.width, cv.height);
      ctx.scale(scale, scale); ctx.drawImage(img, 0, 0, w, h);
      cv.toBlob((b) => {
        if (!b) return;
        const a = document.createElement("a");
        a.href = URL.createObjectURL(b); a.download = `${mode === "synastry" ? "synastry" : sys}-chart.png`; a.click();
        URL.revokeObjectURL(a.href);
      });
    };
    img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(xml)));
  }

  const hasSvgChart = mode === "synastry" || (reading && ["astrology", "qizheng", "jyotish"].includes(reading.system));
  const showResults = mode === "single" ? reading : synastry;

  return (
    <div className="wrap">
      <h1>Bazaar of Fates · 算命</h1>
      <div className="sub">
        Eleven divination engines · one birth input · deterministic chart + bilingual AI reading<br />
        十一套傳統命理排盤引擎 · 一個生辰 · 確定性命盤 + 雙語 AI 解讀
      </div>

      <div className="card">
        <div className="pills" style={{ marginBottom: 12 }}>
          <div className={`pill${mode === "single" ? " on" : ""}`} onClick={() => setMode("single")}>Single 單人</div>
          <div className={`pill${mode === "synastry" ? " on" : ""}`} onClick={() => setMode("synastry")}>Synastry 合盤</div>
        </div>

        <BirthFields f={formA} set={setA} />
        {mode === "synastry" && (
          <>
            <div className="muted" style={{ margin: "12px 0 4px" }}>Person B 第二人（合盤對象）</div>
            <BirthFields f={formB} set={setB} />
          </>
        )}

        {mode === "single" && (
          <div className="pills">
            {systems.map((s) => (
              <div key={s.key} className={`pill${s.key === sys ? " on" : ""}`} title={s.en}
                   onClick={() => setSys(s.key)}>{s.en} · {s.zh}{s.available ? "" : " ⚠"}</div>
            ))}
          </div>
        )}

        <div className="row">
          <div><label>Ask about (optional) 想問</label>
            <input value={focus} onChange={(e) => setFocus(e.target.value)} placeholder="career / love / health 事業 / 感情 / 健康" /></div>
          {(mode === "synastry" || sys === "astrology") && (
            <div style={{ flex: 0, minWidth: 160 }}><label>Houses 宮位制</label>
              <select value={houseSystem} onChange={(e) => setHouseSystem(e.target.value)}>
                {HOUSE_OPTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
          )}
          {mode === "single" && sys === "astrology" && (
            <div style={{ flex: 0 }}><label>&nbsp;</label>
              <label style={{ display: "flex", gap: 6, alignItems: "center", cursor: "pointer" }}>
                <input type="checkbox" checked={transits} onChange={(e) => setTransits(e.target.checked)} style={{ width: "auto" }} />
                Transits 行運
              </label>
            </div>
          )}
          <div style={{ flex: 0 }}>
            {mode === "single"
              ? <button onClick={cast} disabled={busy}>{busy ? "Casting… 排盤中" : "Cast + Read 排盤＋解讀"}</button>
              : <button onClick={compare} disabled={busy}>{busy ? "Comparing… 合盤中" : "Compare 合盤"}</button>}
          </div>
        </div>
        <div className="muted" style={{ marginTop: 10 }}>API: {apiBase()}</div>
      </div>

      {err && <div className="card err">{err}</div>}

      {showResults && (
        <div className="card noprint" style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="muted">Share 分享：</span>
          {hasSvgChart && <button onClick={exportPng}>Download chart PNG 下載星盤</button>}
          <button onClick={() => window.print()} style={{ background: "#27272a", color: "var(--ink)" }}>Print / Save PDF 列印・存 PDF</button>
        </div>
      )}

      {mode === "synastry" && synastry && <SynastryView s={synastry} busy={busy} />}

      {mode === "single" && reading && (
        <>
          <div className="card">
            <h3>{reading.system_en} · {reading.system_zh} · {reading.subject}</h3>
            <div className="summary">{reading.summary}</div>
            <div className="cols">
              <div id="chart-area"><ChartView r={reading} /></div>
              <div>
                <h3>Casting steps 排盤步驟</h3>
                <ul className="chain">{reading.reasoning_chain.map((c, i) => <li key={i}>{c}</li>)}</ul>
              </div>
            </div>
          </div>

          {["astrology", "qizheng", "jyotish"].includes(reading.system) && (
            <div className="card"><h3>Ascendant & Houses 上升與宮位</h3><Houses asc={reading.ascendant} /></div>
          )}

          {timeline && timeline.kind !== "none" && <div className="card"><TimelineView t={timeline} /></div>}

          <div className="card">
            <h3>Reading 解讀{busy ? " · streaming…" : ""}</h3>
            <div className="interp">{reading.interpretation}{busy && <span className="cursor">▍</span>}</div>
          </div>

          <div className="card">
            <h3>Chart elements 命盤要素</h3>
            <div className="kv">
              {Object.entries(reading.readings).map(([k, v]) => (
                <div key={k} style={{ display: "contents" }}>
                  <div className="k">{k}</div><div>{Array.isArray(v) ? v.join("、") : String(v)}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
