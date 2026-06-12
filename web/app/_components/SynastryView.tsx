"use client";
import { Synastry } from "@/lib/api";
import { StarChart } from "../_charts/StarChart";
import { MidpointBlock } from "./MidpointBlock";

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
              aspectsDetail={s.a.chart.aspects_detail}
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

      {s.composite && s.composite.planets.length > 0 && (
        <MidpointBlock title="Composite chart 組合中點盤" m={s.composite}
          note="Each planet at the midpoint of the two natal longitudes. 每顆星取兩人黃經中點。" />
      )}
      {s.davison && s.davison.planets.length > 0 && (
        <MidpointBlock title="Davison chart 時空中點盤" m={s.davison}
          note="A real ephemeris chart for the midpoint moment & place. 兩人生時生地中點的真實天象盤。" />
      )}
    </>
  );
}
