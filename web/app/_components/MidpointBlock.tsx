"use client";
import { MidpointChart } from "@/lib/api";
import { StarChart } from "../_charts/StarChart";
import { TimelineView } from "./TimelineView";

// Shared renderer for any derived chart (composite / Davison / group composite):
// a wheel + a planet table + optional return-timeline + optional bilingual reading.
export function MidpointBlock({ title, note, m }: { title: string; note: string; m: MidpointChart }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <p className="muted" style={{ marginTop: -4 }}>{note}{m.datetime ? ` · ${m.datetime} UT @ ${m.latitude},${m.longitude}` : ""}</p>
      <div className="cols">
        <div><StarChart chart={m.planets} aspectsDetail={m.aspects} cusps={m.ascendant?.houses || []} /></div>
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
        <div style={{ marginTop: 12 }}>
          <TimelineView t={{ system: "davison", system_zh: "", kind: "returns", kind_label: m.timeline.kind_label, periods: m.timeline.periods, note: "" } as any} />
        </div>
      )}
      {m.interpretation && <div className="interp" style={{ marginTop: 12 }}>{m.interpretation}</div>}
    </div>
  );
}
