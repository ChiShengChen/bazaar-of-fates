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

export function OverviewView({ o }: { o: AnnualOverview }) {
  return (
    <>
      <div className="card">
        <h3>多年運勢 Multi-year outlook · {o.subject} · {o.start_year}–{o.start_year + o.count - 1}</h3>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr>
              <th>Year 年</th><th>Age 歲</th><th>SR 上升</th><th>八字流年</th><th>大運</th><th>紫微</th><th>Jyotiṣa daśā</th>
            </tr></thead>
            <tbody>
              {o.years.map((y) => (
                <tr key={y.year}>
                  <td><b>{y.year}</b></td><td className="muted">{y.age}</td>
                  <td>{y.sr_ascendant}</td>
                  <td style={fav(y.bazi_verdict)}>{y.bazi_element}</td>
                  <td className="muted">{y.dayun}</td>
                  <td>{y.ziwei_stem}年</td>
                  <td style={{ color: y.jyotish_nature === "benefic" ? "var(--good)" : "var(--bad)" }}>{y.jyotish_lord}</td>
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
