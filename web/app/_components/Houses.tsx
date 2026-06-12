"use client";
import { Ascendant } from "@/lib/api";

export function Houses({ asc }: { asc: Ascendant | null }) {
  if (!asc) return <p className="muted">Ascendant unknown — needs birth time + place. 上升未知，需時辰＋出生地。</p>;
  return (
    <div>
      <p>
        <span className="muted">Ascendant 上升{asc.sidereal ? " (sidereal)" : ""}: </span>
        <b>{asc.sign} {asc.sign_zh && asc.sign_zh !== asc.sign ? asc.sign_zh : ""} {asc.longitude.toFixed(1)}°</b>
        <span className="muted"> · {asc.house_system === "placidus" ? "Placidus 不等宮" : "whole-sign 整星座"}</span>
        {asc.mc != null && <span className="muted"> · MC {asc.mc.toFixed(1)}°</span>}
      </p>
      <div className="grid4" style={{ marginTop: 8 }}>
        {asc.houses.map((h) => (
          <div key={h.house} className="palace">
            <div className="pn">House {h.house}</div>
            <div>{h.sign || h.rashi}{h.longitude != null ? <span className="muted"> {h.longitude.toFixed(0)}°</span> : null}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
