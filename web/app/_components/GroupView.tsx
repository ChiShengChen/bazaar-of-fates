"use client";
import { useState } from "react";
import { GroupResult } from "@/lib/api";

// net score → cell colour (green = in sync, red = tension)
function cellStyle(net: number): React.CSSProperties {
  if (net === 0) return { background: "#27272a", color: "#a1a1aa" };
  const a = Math.min(1, Math.abs(net) / 6);
  return net > 0
    ? { background: `rgba(52,211,153,${0.18 + 0.5 * a})`, color: "#bbf7d0" }
    : { background: `rgba(251,113,133,${0.18 + 0.5 * a})`, color: "#fecdd3" };
}

export function GroupView({ g }: { g: GroupResult }) {
  const [sel, setSel] = useState<number | null>(null);
  const n = g.people.length;
  return (
    <>
      <div className="card">
        <h3>團體合盤 Group dynamics · {n} people</h3>
        <div className="summary">{g.summary}</div>
        <p className="muted" style={{ marginTop: -4 }}>
          Cell = net cross-aspect score (harmonious − challenging). Click a cell for the pair's aspects.
          格子＝兩人吉凶相位淨分；點格子看該對相位。
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
                    const pair = g.pairs.find((x) => (x.i === i && x.j === j) || (x.i === j && x.j === i));
                    const net = g.matrix[i][j];
                    return (
                      <td key={j} style={{ textAlign: "center", cursor: "pointer", ...cellStyle(net) }}
                          onClick={() => setSel(g.pairs.indexOf(pair!))}>
                        {net > 0 ? `+${net}` : net}
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
    </>
  );
}
