"use client";
import { Synastry, MidpointChart } from "@/lib/api";
import { StarChart } from "../_charts/StarChart";
import { TimelineView } from "./TimelineView";

const HARMONIOUS = new Set(["trine", "sextile", "conjunction"]);

function MidpointBlock({ title, note, m }: { title: string; note: string; m: MidpointChart }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <p className="muted" style={{ marginTop: -4 }}>{note}{m.datetime ? ` · ${m.datetime} UT @ ${m.latitude},${m.longitude}` : ""}</p>
      <div className="cols">
        <div>
          <StarChart chart={m.planets} aspectsDetail={m.aspects} cusps={m.ascendant?.houses || []} />
        </div>
        <div>
          <table><tbody>
            {m.planets.map((p, i) => (
              <tr key={i}><td>{p.body}</td><td>{p.sign} {p.sign_zh}</td><td className="muted">{p.ecliptic_lon.toFixed(1)}°</td></tr>
            ))}
            {m.ascendant && (
              <tr><td><b>ASC</b></td><td>{m.ascendant.sign} {m.ascendant.sign_zh}</td>
                <td className="muted">{m.ascendant.longitude.toFixed(1)}°</td></tr>
            )}
          </tbody></table>
        </div>
      </div>
      {m.timeline && m.timeline.periods.length > 0 && (
        <div style={{ marginTop: 12 }}><TimelineView t={{ system: "davison", system_zh: "", kind: "returns", kind_label: m.timeline.kind_label, periods: m.timeline.periods, note: "" } as any} /></div>
      )}
      {m.interpretation && <div className="interp" style={{ marginTop: 12 }}>{m.interpretation}</div>}
    </div>
  );
}

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
