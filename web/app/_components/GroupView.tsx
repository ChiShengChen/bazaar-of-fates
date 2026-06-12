"use client";
import { useState } from "react";
import { GroupResult } from "@/lib/api";
import { MidpointBlock } from "./MidpointBlock";

type Dim = "net" | "total" | "harmonious" | "challenging";
const DIMS: [Dim, string][] = [["net", "Net 淨分"], ["total", "Total 總相位"], ["harmonious", "Harmonious 吉"], ["challenging", "Challenging 凶"]];

function cellStyle(value: number, dim: Dim): React.CSSProperties {
  if (value === 0) return { background: "#27272a", color: "#a1a1aa" };
  const mag = Math.min(1, Math.abs(value) / (dim === "total" ? 12 : 6));
  const green = { background: `rgba(52,211,153,${0.18 + 0.5 * mag})`, color: "#bbf7d0" };
  const red = { background: `rgba(251,113,133,${0.18 + 0.5 * mag})`, color: "#fecdd3" };
  const neutral = { background: `rgba(167,139,250,${0.18 + 0.5 * mag})`, color: "#ddd6fe" };
  if (dim === "harmonious") return green;
  if (dim === "challenging") return red;
  if (dim === "total") return neutral;
  return value > 0 ? green : red;   // net
}

export function GroupView({ g }: { g: GroupResult }) {
  const [sel, setSel] = useState<number | null>(null);
  const [dim, setDim] = useState<Dim>("net");
  const n = g.people.length;
  const pairOf = (i: number, j: number) => g.pairs.find((x) => (x.i === i && x.j === j) || (x.i === j && x.j === i));
  const valueOf = (i: number, j: number) => {
    const p = pairOf(i, j); if (!p) return 0;
    return dim === "total" ? p.harmonious + p.challenging : dim === "harmonious" ? p.harmonious : dim === "challenging" ? p.challenging : p.net;
  };
  return (
    <>
      <div className="card">
        <h3>團體合盤 Group dynamics · {n} people</h3>
        <div className="summary">{g.summary}</div>
        <div className="pills" style={{ marginBottom: 8 }}>
          {DIMS.map(([d, label]) => (
            <div key={d} className={`pill${dim === d ? " on" : ""}`} onClick={() => setDim(d)}>{label}</div>
          ))}
        </div>
        <p className="muted" style={{ marginTop: -2 }}>
          Cell = {dim === "net" ? "harmonious − challenging" : dim === "total" ? "total cross-aspects" : dim} score. Click a cell for the pair's aspects.
          點格子看該對相位。
        </p>
        <div style={{ overflowX: "auto" }}>
          <table style={{ minWidth: 360 }}>
            <thead><tr><th></th>{g.people.map((p, j) => <th key={j} style={{ textAlign: "center" }}>{p.name}</th>)}</tr></thead>
            <tbody>
              {g.people.map((p, i) => (
                <tr key={i}>
                  <th>{p.name}</th>
                  {g.people.map((_, j) => {
                    if (i === j) return <td key={j} style={{ textAlign: "center", color: "#52525b" }}>—</td>;
                    const v = valueOf(i, j);
                    return (
                      <td key={j} style={{ textAlign: "center", cursor: "pointer", ...cellStyle(v, dim) }}
                          onClick={() => setSel(g.pairs.indexOf(pairOf(i, j)!))}>
                        {dim === "net" && v > 0 ? `+${v}` : v}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted" style={{ marginTop: 8 }}>
          {g.best_pair && <>most in-sync 最契合：<b style={{ color: "var(--good)" }}>{g.best_pair.a}↔{g.best_pair.b}</b> (+{g.best_pair.net})　</>}
          {g.tense_pair && <>most tension 最具張力：<b style={{ color: "var(--bad)" }}>{g.tense_pair.a}↔{g.tense_pair.b}</b> ({g.tense_pair.net})</>}
        </p>

        {sel != null && g.pairs[sel] && (
          <div style={{ marginTop: 10 }}>
            <h3>{g.pairs[sel].a} ↔ {g.pairs[sel].b} · {g.pairs[sel].harmonious} harmonious / {g.pairs[sel].challenging} challenging</h3>
            <div className="pills">
              {g.pairs[sel].aspects.map((x, k) => (
                <span key={k} className="pill static" style={{ color: ["trine", "sextile", "conjunction"].includes(x.type) ? "var(--good)" : "var(--bad)" }}>
                  {x.a} {x.type} {x.b} {x.orb}°
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <h3>Group reading 團體解讀</h3>
        <div className="interp">{g.interpretation}</div>
      </div>

      {g.composite && g.composite.planets.length > 0 && (
        <MidpointBlock title="Group composite chart 團體共同中點盤" m={g.composite}
          note="Every planet at the circular mean of all members. 全員行星取圓周平均（團體 composite）。" />
      )}
    </>
  );
}
