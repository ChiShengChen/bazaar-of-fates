"use client";
import { useState } from "react";
import { SynthesisResult } from "@/lib/api";

// 綜合 / cross-tradition synthesis: one question, every system's rule-based verdict side by side,
// agreement vs conflict highlighted, then the panel reading.
const V_CLASS: Record<string, string> = { favourable: "nat-favourable", neutral: "nat-neutral", unfavourable: "nat-unfavourable" };

export function SynthesisView({ s }: { s: SynthesisResult }) {
  const [open, setOpen] = useState<string | null>(null);
  const lean = s.lean;
  return (
    <>
      <div className="card">
        <h3>Synthesis 綜合 · {s.topic_label}{s.focus ? <span className="muted"> · 「{s.focus}」</span> : null}</h3>
        <div className="summary">{s.summary}</div>
        <div className="pills" style={{ marginBottom: 10 }}>
          <span className={`pill static ${V_CLASS[lean]}`}>overall 整體：{s.lean_zh}</span>
          <span className="pill static">利 {s.tally.favourable}</span>
          <span className="pill static">平 {s.tally.neutral}</span>
          <span className="pill static">不利 {s.tally.unfavourable}</span>
        </div>
        {s.consensus.length > 0 && <div className="bz-note"><span className="muted">agree 一致：</span>{s.consensus.join("、")}</div>}
        {s.conflicts.length > 0 && <div className="bz-note"><span className="muted">conflict 相左：</span>{s.conflicts.join("、")}</div>}
        <table style={{ marginTop: 10 }}>
          <thead><tr><th>System 系統</th><th>Verdict 判斷</th><th>Why 依據（該門派規則）</th><th></th></tr></thead>
          <tbody>
            {s.systems.map((r) => (
              <>
                <tr key={r.system} className={r.verdict !== "neutral" && r.verdict !== lean ? "syn-conflict" : ""}>
                  <td><b>{r.system_zh}</b><div className="muted">{r.system_en}</div></td>
                  <td><span className={`tl-bar ${V_CLASS[r.verdict]}`} style={{ display: "inline-flex", height: 22 }}>{r.verdict_zh}</span></td>
                  <td style={{ fontSize: 13 }}>{r.reason}</td>
                  <td><span className="muted" style={{ cursor: "pointer" }} onClick={() => setOpen(open === r.system ? null : r.system)}>{open === r.system ? "▲" : "facts ▼"}</span></td>
                </tr>
                {open === r.system && (
                  <tr key={r.system + "-facts"}><td colSpan={4}>
                    <div className="muted" style={{ marginBottom: 4 }}>{r.summary}</div>
                    <div className="kv">
                      {Object.entries(r.facts || {}).map(([k, v]) => (
                        <div key={k} style={{ display: "contents" }}>
                          <div className="k">{k}</div><div>{typeof v === "string" ? v : Array.isArray(v) ? v.join("、") : JSON.stringify(v)}</div>
                        </div>
                      ))}
                    </div>
                  </td></tr>
                )}
              </>
            ))}
          </tbody>
        </table>
        {Object.keys(s.errors || {}).length > 0 && <div className="muted" style={{ marginTop: 6 }}>failed 失敗：{Object.entries(s.errors).map(([k, e]) => `${k}: ${e}`).join("；")}</div>}
      </div>
      <div className="card">
        <h3>Panel reading 會診解讀</h3>
        <div className="interp">{s.interpretation}</div>
      </div>
    </>
  );
}
