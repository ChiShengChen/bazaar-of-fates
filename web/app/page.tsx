"use client";
import { useEffect, useState } from "react";
import {
  apiBase, getSystems, getTimeline, streamReading, getSynastry, getGroup, getCast, getAnnual,
  SystemInfo, Reading, Timeline, Synastry, GroupResult, AnnualReport,
} from "@/lib/api";
import { ChartView } from "./_components/ChartView";
import { Houses } from "./_components/Houses";
import { TimelineView } from "./_components/TimelineView";
import { SynastryView } from "./_components/SynastryView";
import { GroupView } from "./_components/GroupView";
import { AnnualView } from "./_components/AnnualView";
import { BirthFields, FormState, emptyForm, toBirth } from "./_components/BirthFields";

const HOUSE_OPTS = [
  ["whole_sign", "whole-sign 整星座"], ["equal", "Equal 等宮"], ["placidus", "Placidus 不等宮"],
  ["koch", "Koch 不等宮"], ["regiomontanus", "Regiomontanus 不等宮"], ["campanus", "Campanus 不等宮"],
];

export default function Page() {
  const [systems, setSystems] = useState<SystemInfo[]>([]);
  const [sys, setSys] = useState("bazi");
  const [mode, setMode] = useState<"single" | "synastry" | "group" | "annual">("single");
  const [houseSystem, setHouseSystem] = useState("whole_sign");
  const [overlay, setOverlay] = useState<"none" | "transits" | "progress" | "solar_return" | "lunar_return">("none");
  const [progMethod, setProgMethod] = useState("secondary");
  const [tightOnly, setTightOnly] = useState(false);
  const [transitOffset, setTransitOffset] = useState(0);   // days from today
  const [focus, setFocus] = useState("");

  const dateFromOffset = (off: number) => new Date(Date.now() + off * 86400000).toISOString().slice(0, 10);
  const transitDate = dateFromOffset(transitOffset);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reading, setReading] = useState<Reading | null>(null);
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [synastry, setSynastry] = useState<Synastry | null>(null);
  const [group, setGroup] = useState<GroupResult | null>(null);
  const [annual, setAnnual] = useState<AnnualReport | null>(null);
  const [annualYear, setAnnualYear] = useState(new Date().getFullYear());
  const [formsG, setFormsG] = useState<FormState[]>([
    emptyForm({ name: "Mei 小美", gender: "female", time: "14:30", place: "Taipei", lat: "25.04", lon: "121.56" }),
    emptyForm({ name: "Ken 阿肯", gender: "male", date: "1988-11-02", time: "09:15", place: "Tokyo", lat: "35.68", lon: "139.69" }),
    emptyForm({ name: "Lin 小琳", gender: "female", date: "1992-03-08", time: "20:40", place: "HK", lat: "22.3", lon: "114.2" }),
  ]);
  const setG = (idx: number, k: keyof FormState, v: string) =>
    setFormsG((fs) => fs.map((f, i) => (i === idx ? { ...f, [k]: v } : f)));

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
        sys, b, focus || null, houseSystem,
        overlay === "transits", overlay !== "none" ? transitDate : null,
        overlay === "progress", progMethod, overlay === "solar_return", overlay === "lunar_return",
        (chart) => setReading({ ...(chart as Reading), interpretation: "" }),
        (delta) => { acc += delta; setReading((r) => (r ? { ...r, interpretation: acc } : r)); },
      );
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  }

  // live scrubbing of the transit/progression date: refresh only the outer ring (no LLM), debounced
  function scrubTransit(off: number) {
    setTransitOffset(off);
    if (!reading || reading.system !== "astrology" || overlay === "none") return;
    const td = dateFromOffset(off);
    clearTimeout((scrubTransit as any)._t);
    (scrubTransit as any)._t = setTimeout(async () => {
      try {
        const c = await getCast("astrology", toBirth(formA), {
          house_system: houseSystem, transit_date: td,
          transits: overlay === "transits", progress: overlay === "progress",
          progress_method: progMethod, solar_return: overlay === "solar_return", lunar_return: overlay === "lunar_return",
        });
        setReading((r) => (r ? { ...r, chart: {
          ...r.chart,
          transits: c.chart.transits, transit_aspects: c.chart.transit_aspects, major_transits: c.chart.major_transits,
          progressions: c.chart.progressions, progression_aspects: c.chart.progression_aspects,
          progression_houses: c.chart.progression_houses, major_progressions: c.chart.major_progressions,
          solar_return: c.chart.solar_return, solar_return_aspects: c.chart.solar_return_aspects, solar_return_houses: c.chart.solar_return_houses,
          lunar_return: c.chart.lunar_return, lunar_return_aspects: c.chart.lunar_return_aspects, lunar_return_houses: c.chart.lunar_return_houses,
        }, readings: { ...r.readings, ...c.readings } } : r));
      } catch { /* ignore scrub errors */ }
    }, 120);
  }

  async function compare() {
    setBusy(true); setErr(null); setSynastry(null);
    try {
      setSynastry(await getSynastry(toBirth(formA), toBirth(formB), focus || null, houseSystem));
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  }

  async function compareGroup() {
    setBusy(true); setErr(null); setGroup(null);
    try {
      setGroup(await getGroup(formsG.map(toBirth), focus || null, houseSystem));
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  }

  async function generateAnnual() {
    setBusy(true); setErr(null); setAnnual(null);
    try {
      setAnnual(await getAnnual(toBirth(formA), annualYear, focus || null));
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

  const hasSvgChart = mode === "synastry" || (mode === "single" && reading && ["astrology", "qizheng", "jyotish"].includes(reading.system));
  const showResults = mode === "single" ? reading : mode === "synastry" ? synastry : mode === "group" ? group : annual;

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
          <div className={`pill${mode === "group" ? " on" : ""}`} onClick={() => setMode("group")}>Group 團體</div>
          <div className={`pill${mode === "annual" ? " on" : ""}`} onClick={() => setMode("annual")}>Annual 年度報告</div>
        </div>

        {mode !== "group" && <BirthFields f={formA} set={setA} />}
        {mode === "synastry" && (
          <>
            <div className="muted" style={{ margin: "12px 0 4px" }}>Person B 第二人（合盤對象）</div>
            <BirthFields f={formB} set={setB} />
          </>
        )}
        {mode === "group" && (
          <>
            {formsG.map((f, i) => (
              <div key={i}>
                <div className="muted" style={{ margin: "10px 0 4px", display: "flex", justifyContent: "space-between" }}>
                  <span>Person {i + 1} 第{i + 1}人</span>
                  {formsG.length > 2 && <span style={{ cursor: "pointer", color: "var(--bad)" }}
                    onClick={() => setFormsG((fs) => fs.filter((_, j) => j !== i))}>✕ remove 移除</span>}
                </div>
                <BirthFields f={f} set={(k, v) => setG(i, k, v)} />
              </div>
            ))}
            {formsG.length < 8 && (
              <div className="pills" style={{ marginTop: 8 }}>
                <span className="pill" onClick={() => setFormsG((fs) => [...fs, emptyForm({ name: `P${fs.length + 1}`, date: "1990-01-01", time: "12:00", place: "Taipei", lat: "25.04", lon: "121.56" })])}>+ add person 加一人</span>
              </div>
            )}
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
          {(mode === "synastry" || mode === "group" || (mode === "single" && sys === "astrology")) && (
            <div style={{ flex: 0, minWidth: 160 }}><label>Houses 宮位制</label>
              <select value={houseSystem} onChange={(e) => setHouseSystem(e.target.value)}>
                {HOUSE_OPTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
          )}
          {mode === "single" && sys === "astrology" && (
            <div style={{ flex: 0, minWidth: 150 }}><label>Overlay 疊加</label>
              <select value={overlay} onChange={(e) => setOverlay(e.target.value as any)}>
                <option value="none">none 無</option>
                <option value="transits">transits 行運</option>
                <option value="progress">progressions 推運</option>
                <option value="solar_return">solar return 太陽回歸</option>
                <option value="lunar_return">lunar return 月亮回歸</option>
              </select>
            </div>
          )}
          {mode === "single" && sys === "astrology" && overlay !== "none" && (
            <div style={{ flex: 0 }}><label>&nbsp;</label>
              <label style={{ display: "flex", gap: 6, alignItems: "center", cursor: "pointer", fontSize: 13 }}>
                <input type="checkbox" checked={tightOnly} onChange={(e) => setTightOnly(e.target.checked)} style={{ width: "auto" }} />
                tight ≤3° 緊密
              </label>
            </div>
          )}
          {mode === "single" && sys === "astrology" && overlay === "progress" && (
            <div style={{ flex: 0, minWidth: 150 }}><label>Method 推運法</label>
              <select value={progMethod} onChange={(e) => setProgMethod(e.target.value)}>
                <option value="secondary">secondary 二次推運</option>
                <option value="solar_arc">solar arc 太陽弧</option>
              </select>
            </div>
          )}
          {mode === "annual" && (
            <div style={{ flex: 0, minWidth: 110 }}><label>Year 年份</label>
              <input type="number" value={annualYear} onChange={(e) => setAnnualYear(Number(e.target.value))} /></div>
          )}
          <div style={{ flex: 0 }}>
            {mode === "single" && <button onClick={cast} disabled={busy}>{busy ? "Casting… 排盤中" : "Cast + Read 排盤＋解讀"}</button>}
            {mode === "synastry" && <button onClick={compare} disabled={busy}>{busy ? "Comparing… 合盤中" : "Compare 合盤"}</button>}
            {mode === "group" && <button onClick={compareGroup} disabled={busy}>{busy ? "Comparing… 合盤中" : "Compare group 團體合盤"}</button>}
            {mode === "annual" && <button onClick={generateAnnual} disabled={busy}>{busy ? "Generating… 產生中" : "Annual report 年度報告"}</button>}
          </div>
        </div>
        {mode === "single" && sys === "astrology" && overlay !== "none" && (
          <div style={{ marginTop: 12 }}>
            <label>{overlay === "progress" ? "Progress-to date 推運至" : overlay === "solar_return" ? "Return year 回歸年份" : overlay === "lunar_return" ? "Return month 回歸月份" : "Transit date 行運日期"} — drag to scrub 拖曳 · <b>{overlay === "solar_return" ? transitDate.slice(0, 4) : transitDate}</b>{transitOffset === 0 ? " (today 今天)" : ` (${transitOffset > 0 ? "+" : ""}${transitOffset}d)`}</label>
            <input type="range" min={-1825} max={1825} value={transitOffset}
                   onChange={(e) => scrubTransit(Number(e.target.value))} style={{ width: "100%" }} />
          </div>
        )}
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
      {mode === "group" && group && <GroupView g={group} />}
      {mode === "annual" && annual && <AnnualView a={annual} />}

      {mode === "single" && reading && (
        <>
          <div className="card">
            <h3>{reading.system_en} · {reading.system_zh} · {reading.subject}</h3>
            <div className="summary">{reading.summary}</div>
            <div className="cols">
              <div id="chart-area"><ChartView r={reading} tightOnly={tightOnly} /></div>
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

          {(reading.chart?.solar_return_timeline?.length ?? 0) > 0 && (
            <div className="card"><TimelineView t={{ system: "astrology", system_zh: "", kind: "sr",
              kind_label: `Solar Return ${reading.readings?.solar_return_year ?? ""} — key transits 流年關鍵行運`,
              periods: reading.chart.solar_return_timeline, note: "" } as any} /></div>
          )}

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
