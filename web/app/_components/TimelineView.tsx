"use client";
import { Timeline } from "@/lib/api";

export function TimelineView({ t }: { t: Timeline }) {
  if (!t || t.kind === "none" || !t.periods.length)
    return <p className="muted">{t?.kind_label || "No timeline for this system. 此系統無大運/流年。"}</p>;

  const span = t.periods.map((p) => p.start_age ?? 0);
  const max = Math.max(...t.periods.map((p) => (p.start_age ?? 0)), 1) + 12;
  return (
    <div>
      <h3>{t.kind_label}{t.note ? <span className="muted"> · {t.note}</span> : null}</h3>
      <div className="tl">
        {t.periods.map((p) => {
          const w = Math.max(8, Math.min(100, (((p.start_age ?? 0)) / max) * 100 + 10));
          return (
            <div className="tl-row" key={p.index}>
              <div className="muted">
                {p.start_age != null ? `age ${p.start_age.toFixed(0)}` : ""} · {p.start.slice(0, 4)}
              </div>
              <div className={`tl-bar nat-${p.nature} ${p.current ? "tl-now" : ""}`} style={{ width: `${w}%` }}>
                <b>{p.label}</b>&nbsp;<span style={{ opacity: 0.8 }}>{p.detail}</span>{p.current ? " ← now" : ""}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
