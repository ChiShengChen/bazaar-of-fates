"use client";
import { useRef, useState } from "react";
import { AnnualReport, AnnualOverview } from "@/lib/api";
import { StarChart } from "../_charts/StarChart";

// drag across the chart to select a year range → zoom; returns the slice + a selection overlay
function useDragZoom(total: number) {
  const ref = useRef<HTMLDivElement>(null);
  const [range, setRange] = useState<[number, number] | null>(null);
  const [sel, setSel] = useState<[number, number] | null>(null);
  const idxAt = (clientX: number) => {
    const r = ref.current!.getBoundingClientRect();
    return Math.max(0, Math.min(total - 1, Math.floor(((clientX - r.left) / r.width) * total)));
  };
  const handlers = {
    onMouseDown: (e: React.MouseEvent) => setSel([idxAt(e.clientX), idxAt(e.clientX)]),
    onMouseMove: (e: React.MouseEvent) => setSel((s) => (s ? [s[0], idxAt(e.clientX)] : s)),
    onMouseUp: () => { if (sel) { const [a, b] = sel; if (Math.abs(a - b) >= 1) setRange([Math.min(a, b), Math.max(a, b)]); setSel(null); } },
    onMouseLeave: () => setSel(null),
  };
  const lo = range ? range[0] : 0;
  const hi = range ? range[1] : total - 1;
  const selRect = sel && Math.abs(sel[0] - sel[1]) >= 1
    ? { left: `${(Math.min(sel[0], sel[1]) / total) * 100}%`, width: `${((Math.abs(sel[0] - sel[1]) + 1) / total) * 100}%` }
    : null;
  return { ref, handlers, lo, hi, zoomed: range != null, reset: () => setRange(null), selRect };
}

export function AnnualView({ a }: { a: AnnualReport }) {
  const s = a.sections || {};
  const c = s.solar_return?.chart;
  return (
    <>
      <div className="card">
        <h3>年度報告 Annual Report · {a.subject} · {a.year}</h3>
        <div className="summary">{a.summary}</div>
        {c && (
          <div id="chart-area" style={{ maxWidth: 380, margin: "6px auto 12px" }}>
            <StarChart chart={c.natal} cusps={c.natal_houses} outer={c.sr_planets}
                       outerCusps={c.sr_houses} crossAspects={c.sr_aspects}
                       outerLabel={`solar return 太陽回歸 ${a.year}`} />
          </div>
        )}
        <div className="kv">
          {s.solar_return?.ascendant && <><div className="k">Solar Return 上升</div><div>{s.solar_return.ascendant} · {s.solar_return.moment}</div></>}
          {s.bazi && <><div className="k">八字流年</div><div>{s.bazi.liunian_element}（{s.bazi.verdict}）· 大運 {s.bazi.dayun} · 喜用 {(s.bazi.favourable || []).join("、")}</div></>}
          {s.ziwei && <><div className="k">紫微四化</div><div>{s.ziwei.year_stem}年：{(s.ziwei.sihua || []).join("、")}</div></>}
          {s.jyotish && <><div className="k">Jyotiṣa 大運</div><div>{s.jyotish.mahadasha_lord}（{s.jyotish.nature}）</div></>}
        </div>
        {(s.solar_return?.highlights?.length ?? 0) > 0 && (
          <>
            <h3 style={{ marginTop: 14 }}>Solar Return highlights 流年重點</h3>
            <ul className="chain">{s.solar_return!.highlights!.map((h, i) => <li key={i}>{h}</li>)}</ul>
          </>
        )}
        {(s.solar_return?.key_transits?.length ?? 0) > 0 && (
          <>
            <h3 style={{ marginTop: 14 }}>Key transits this year 今年關鍵行運</h3>
            <ul className="chain">{s.solar_return!.key_transits!.map((t: any, i: number) =>
              <li key={i}>{t.label} — {t.start}</li>)}</ul>
          </>
        )}
      </div>
      <div className="card">
        <h3>Reading 年度解讀</h3>
        <div className="interp">{a.interpretation}</div>
      </div>
    </>
  );
}

const fav = (v?: string) => (v || "").startsWith("favourable")
  ? { color: "var(--good)" } : (v ? { color: "var(--bad)" } : {});

// score −2..+2 → heatmap colour (green favourable, red challenging)
function scoreColor(score: number): string {
  const m: Record<number, string> = {
    2: "rgba(52,211,153,0.72)", 1: "rgba(52,211,153,0.40)", 0: "#3f3f46",
    [-1]: "rgba(251,113,133,0.40)", [-2]: "rgba(251,113,133,0.72)",
  };
  return m[Math.max(-2, Math.min(2, score))] ?? "#3f3f46";
}

// turning-point event → a distinct glyph + colour (Saturn / Jupiter / 大運 / daśā / 八字)
function marker(ev: string): { s: string; c: string } {
  if (ev.includes("Saturn return")) return { s: "♄", c: "#fbbf24" };
  if (ev.includes("Jupiter return")) return { s: "♃", c: "#60a5fa" };
  if (ev.includes("大運")) return { s: "運", c: "#a78bfa" };
  if (ev.includes("daśā")) return { s: "↻", c: "#818cf8" };
  if (ev.includes("八字")) return ev.includes("favourable") ? { s: "☯", c: "#34d399" } : { s: "☯", c: "#fb7185" };
  return { s: "★", c: "#a78bfa" };
}

// a colour-block strip (no trend line) for one person, used in the comparison view
function Strip({ years, label, color }: { years: AnnualOverview["years"]; label: string; color: string }) {
  return (
    <div style={{ margin: "2px 0" }}>
      <div style={{ fontSize: 11, color }}>{label}</div>
      <div style={{ display: "flex", gap: 3 }}>
        {years.map((y) => (
          <div key={y.year} title={`${y.year} · score ${y.score} · 八字 ${y.bazi_element}（${y.bazi_verdict}）· Jyotiṣa ${y.jyotish_lord}`}
               style={{ flex: "1 0 40px", minWidth: 40, textAlign: "center", padding: "5px 2px",
                        borderRadius: 4, background: scoreColor(y.score), fontSize: 10 }}>
            {y.bazi_element}{y.turning?.length ? " ★" : ""}
          </div>
        ))}
      </div>
    </div>
  );
}

export function CompareView({ a, b }: { a: AnnualOverview; b: AnnualOverview }) {
  const N = Math.min(a.years.length, b.years.length);
  const A = a.years.slice(0, N), B = b.years.slice(0, N);
  const z = useDragZoom(N);
  const va = A.slice(z.lo, z.hi + 1), vb = B.slice(z.lo, z.hi + 1), m = va.length;
  const yOf = (sc: number) => 20 - sc * 7;
  const line = (ys: AnnualOverview["years"]) => ys.map((y, i) => `${i + 0.5},${yOf(y.score)}`).join(" ");
  const dots = (ys: AnnualOverview["years"], color: string, name: string) =>
    ys.map((y, i) => (
      <div key={name + y.year}
           title={`${name} · ${y.year} · score ${y.score > 0 ? "+" : ""}${y.score} · 八字 ${y.bazi_element}（${y.bazi_verdict}）· Jyotiṣa ${y.jyotish_lord}`}
           style={{ position: "absolute", left: `${((i + 0.5) / m) * 100}%`, top: `${(yOf(y.score) / 40) * 100}%`,
                    transform: "translate(-50%,-50%)", width: 9, height: 9, borderRadius: "50%",
                    background: color, border: "1.5px solid #1c1917" }} />
    ));
  // 契合年: neither in a bad year and together positive · 共同低潮: both non-positive and together low
  const isC = (sa: number, sb: number) => sa >= 0 && sb >= 0 && sa + sb >= 2;
  const isT = (sa: number, sb: number) => sa <= 0 && sb <= 0 && sa + sb <= -2;
  const compat = A.filter((y, i) => isC(y.score, B[i].score)).map((y) => y.year);
  const tough = A.filter((y, i) => isT(y.score, B[i].score)).map((y) => y.year);
  const isCompat = (yr: number) => compat.includes(yr);
  return (
    <div className="card">
      <h3>雙人對照 Two-person comparison · {a.subject} ✕ {b.subject}</h3>
      <p className="muted" style={{ fontSize: 12, marginTop: -4 }}>
        <span style={{ color: "#fde047" }}>● {a.subject.split(" ")[0]}</span>
        <span style={{ color: "#22d3ee" }}>● {b.subject.split(" ")[0]}</span>
        　— favourability trend −2…+2; drag to zoom 拖曳縮放.
        {z.zoomed && <button onClick={z.reset} style={{ marginLeft: 8, padding: "1px 8px", fontSize: 11 }}>↺ reset</button>}
      </p>
      <div ref={z.ref} {...z.handlers} style={{ position: "relative", height: 96, userSelect: "none", cursor: "crosshair" }}>
        <svg viewBox={`0 0 ${m} 40`} preserveAspectRatio="none" style={{ width: "100%", height: "100%" }}>
          {va.map((y, i) => isC(y.score, vb[i].score)
            ? <rect key={y.year} x={i} y={0} width={1} height={40} fill="#fde047" opacity={0.14} /> : null)}
          <line x1={0} y1={20} x2={m} y2={20} stroke="#52525b" strokeWidth={1} vectorEffect="non-scaling-stroke" opacity={0.5} strokeDasharray="3 3" />
          <polyline points={line(va)} fill="none" stroke="#fde047" strokeWidth={2} vectorEffect="non-scaling-stroke" />
          <polyline points={line(vb)} fill="none" stroke="#22d3ee" strokeWidth={2} vectorEffect="non-scaling-stroke" />
        </svg>
        {dots(va, "#fde047", a.subject.split(" ")[0])}
        {dots(vb, "#22d3ee", b.subject.split(" ")[0])}
        {z.selRect && <div style={{ position: "absolute", top: 0, bottom: 0, ...z.selRect, background: "rgba(255,255,255,0.14)", pointerEvents: "none" }} />}
      </div>
      <div style={{ display: "flex", gap: 3, fontSize: 10, margin: "2px 0 6px" }}>
        {va.map((y) => <div key={y.year} style={{ flex: "1 0 40px", minWidth: 40, textAlign: "center", color: isCompat(y.year) ? "#fde047" : "#71717a" }}>{String(y.year).slice(2)}{isCompat(y.year) ? "✦" : ""}</div>)}
      </div>
      <Strip years={va} label={a.subject} color="#fde047" />
      <Strip years={vb} label={b.subject} color="#22d3ee" />
      <p style={{ fontSize: 13, marginTop: 8 }}>
        <b style={{ color: "#fde047" }}>✦ 契合年 best shared years:</b> {compat.length ? compat.join(", ") : "—"}（兩人皆吉，宜共同大事）
        {tough.length ? <span className="muted">　· 共同低潮 caution: {tough.join(", ")}</span> : null}
      </p>
    </div>
  );
}

export function OverviewView({ o, onYear }: { o: AnnualOverview; onYear?: (year: number) => void }) {
  const z = useDragZoom(o.years.length);
  const view = o.years.slice(z.lo, z.hi + 1);
  const n = view.length;
  const yOf = (sc: number) => 20 - sc * 7;   // score −2..+2 → y in a 0..40 viewBox
  return (
    <>
      <div className="card">
        <h3>多年運勢 Multi-year outlook · {o.subject} · {o.start_year}–{o.start_year + o.count - 1}
          {z.zoomed && <button onClick={z.reset} style={{ marginLeft: 8, padding: "1px 8px", fontSize: 11 }}>↺ reset</button>}
        </h3>

        {/* heatmap + score trend line; drag to zoom, click a year to expand */}
        <div ref={z.ref} {...z.handlers} style={{ position: "relative", margin: "4px 0 6px", userSelect: "none", cursor: "crosshair" }}>
          <div style={{ display: "flex", gap: 3 }}>
            {view.map((y) => (
              <div key={y.year} onClick={() => onYear?.(y.year)}
                   title={[(y.turning || []).join(" · ") || `score ${y.score}`, onYear ? "— click for full report 點看完整年度報告" : ""].filter(Boolean).join(" ")}
                   style={{ flex: "1 0 44px", minWidth: 44, textAlign: "center", padding: "8px 2px 7px",
                            borderRadius: 5, background: scoreColor(y.score), fontSize: 11,
                            cursor: onYear ? "pointer" : "default",
                            outline: (y.turning?.length ? "2px solid var(--accent)" : "none") }}>
                <div style={{ fontWeight: 600 }}>{String(y.year).slice(2)}</div>
                <div style={{ fontSize: 12, minHeight: 14, letterSpacing: 1 }}>
                  {(y.turning || []).map((ev, k) => { const m = marker(ev); return <span key={k} style={{ color: m.c }}>{m.s}</span>; })}
                </div>
                <div className="muted" style={{ fontSize: 9 }}>{y.bazi_element}</div>
              </div>
            ))}
          </div>
          <svg viewBox={`0 0 ${n} 40`} preserveAspectRatio="none"
               style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
            <line x1={0} y1={20} x2={n} y2={20} stroke="#52525b" strokeWidth={1} vectorEffect="non-scaling-stroke" opacity={0.5} strokeDasharray="3 3" />
            <polyline points={view.map((y, i) => `${i + 0.5},${yOf(y.score)}`).join(" ")} fill="none" stroke="#fde047" strokeWidth={2} vectorEffect="non-scaling-stroke" opacity={0.95} />
          </svg>
          {view.map((y, i) => (
            <div key={`d${y.year}`} onClick={() => onYear?.(y.year)}
                 title={`${y.year} · score ${y.score > 0 ? "+" : ""}${y.score} · 八字 ${y.bazi_element}（${y.bazi_verdict}）· Jyotiṣa ${y.jyotish_lord}（${y.jyotish_nature}）`}
                 style={{ position: "absolute", left: `${((i + 0.5) / n) * 100}%`, top: `${(yOf(y.score) / 40) * 100}%`,
                          transform: "translate(-50%,-50%)", width: 10, height: 10, borderRadius: "50%",
                          background: "#fde047", border: "1.5px solid #1c1917", cursor: onYear ? "pointer" : "default" }} />
          ))}
          {z.selRect && <div style={{ position: "absolute", top: 0, bottom: 0, ...z.selRect, background: "rgba(255,255,255,0.14)", pointerEvents: "none" }} />}
        </div>
        <p className="muted" style={{ fontSize: 11, marginTop: 0 }}>
          色塊：綠＝喜用/吉、紅＝忌耗/凶；<b style={{ color: "#fde047" }}>黃線</b>＝逐年吉凶分數（−2…+2）趨勢。
          轉折符號 turning markers：<span style={{ color: "#fbbf24" }}>♄</span> 土星回歸 · <span style={{ color: "#60a5fa" }}>♃</span> 木星回歸 · <span style={{ color: "#a78bfa" }}>運</span> 換大運 · <span style={{ color: "#818cf8" }}>↻</span> 換 daśā · <span style={{ color: "#34d399" }}>☯</span>/<span style={{ color: "#fb7185" }}>☯</span> 八字翻轉。**點任一年看完整年度報告**。
        </p>

        {(o.turning_points?.length ?? 0) > 0 && (
          <p style={{ fontSize: 13 }}>
            <b>關鍵轉折 Turning points:</b>{" "}
            {o.turning_points.map((t, i) => (
              <span key={t.year}>{i > 0 ? "　" : ""}<b style={{ color: "var(--accent)" }}>{t.year}</b>：{t.events.join(" / ")}</span>
            ))}
          </p>
        )}

        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr>
              <th>Year 年</th><th>Age 歲</th><th>SR 上升</th><th>八字流年</th><th>大運</th><th>紫微</th><th>Jyotiṣa daśā</th><th>轉折</th>
            </tr></thead>
            <tbody>
              {o.years.map((y) => (
                <tr key={y.year} onClick={() => onYear?.(y.year)}
                    style={{ cursor: onYear ? "pointer" : "default", ...(y.turning?.length ? { outline: "1px solid var(--accent)" } : {}) }}>
                  <td><b>{y.year}</b></td><td className="muted">{y.age}</td>
                  <td>{y.sr_ascendant}</td>
                  <td style={fav(y.bazi_verdict)}>{y.bazi_element}</td>
                  <td className="muted">{y.dayun}</td>
                  <td>{y.ziwei_stem}年</td>
                  <td style={{ color: y.jyotish_nature === "benefic" ? "var(--good)" : "var(--bad)" }}>{y.jyotish_lord}</td>
                  <td style={{ color: "var(--accent)", fontSize: 11 }}>{(y.turning || []).join(" / ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card">
        <h3>Arc reading 走勢解讀</h3>
        <div className="interp">{o.interpretation}</div>
      </div>
    </>
  );
}
