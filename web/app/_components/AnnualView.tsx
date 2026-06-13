"use client";
import { AnnualReport, AnnualOverview } from "@/lib/api";
import { StarChart } from "../_charts/StarChart";

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

export function OverviewView({ o }: { o: AnnualOverview }) {
  return (
    <>
      <div className="card">
        <h3>多年運勢 Multi-year outlook · {o.subject} · {o.start_year}–{o.start_year + o.count - 1}</h3>

        {/* heatmap strip: one colour block per year, ★ marks a turning point */}
        <div style={{ display: "flex", gap: 3, margin: "4px 0 6px", overflowX: "auto" }}>
          {o.years.map((y) => (
            <div key={y.year} title={(y.turning || []).join(" · ") || `score ${y.score}`}
                 style={{ flex: "1 0 42px", minWidth: 42, textAlign: "center", padding: "8px 2px",
                          borderRadius: 5, background: scoreColor(y.score), fontSize: 11,
                          outline: (y.turning?.length ? "2px solid var(--accent)" : "none") }}>
              <div style={{ fontWeight: 600 }}>{String(y.year).slice(2)}{y.turning?.length ? " ★" : ""}</div>
              <div className="muted" style={{ fontSize: 9 }}>{y.bazi_element}</div>
            </div>
          ))}
        </div>
        <p className="muted" style={{ fontSize: 11, marginTop: 0 }}>
          綠＝喜用/吉、紅＝忌耗/凶（八字流年＋Jyotiṣa 大運）；★＝關鍵轉折年（換大運/換 daśā/八字翻轉）。
          green = favourable · red = challenging · ★ = turning point.
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
                <tr key={y.year} style={y.turning?.length ? { outline: "1px solid var(--accent)" } : {}}>
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
