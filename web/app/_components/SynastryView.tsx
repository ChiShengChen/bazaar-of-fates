"use client";
import { Synastry } from "@/lib/api";
import { StarChart } from "../_charts/StarChart";

const HARMONIOUS = new Set(["trine", "sextile", "conjunction"]);

export function SynastryView({ s, busy }: { s: Synastry; busy: boolean }) {
  return (
    <>
      <div className="card">
        <h3>合盤 Synastry · {s.a.subject} ✕ {s.b.subject}</h3>
        <div className="summary">{s.summary}</div>
        <div className="cols">
          <div id="chart-area">
            <StarChart
              chart={s.a.chart.planets || []}
              cusps={s.a.ascendant?.houses || []}
              outer={s.b.chart.planets || []}
              crossAspects={s.cross_aspects}
              aspects={s.a.chart.aspects || []}
              outerLabel={`outer 外圈 = ${s.b.subject}`}
            />
          </div>
          <div>
            <h3>Cross-aspects 星際相位</h3>
            <table><tbody>
              {s.cross_aspects.map((x, i) => (
                <tr key={i}>
                  <td>{x.a}</td>
                  <td style={{ color: HARMONIOUS.has(x.type) ? "var(--good)" : "var(--bad)" }}>{x.type}</td>
                  <td>{x.b}</td>
                  <td className="muted">{x.orb}°</td>
                </tr>
              ))}
            </tbody></table>
          </div>
        </div>
      </div>
      <div className="card">
        <h3>Relationship reading 合盤解讀{busy ? " · …" : ""}</h3>
        <div className="interp">{s.interpretation}</div>
      </div>
    </>
  );
}
