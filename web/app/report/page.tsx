"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getAnnual, getReading, AnnualReport, Reading, Timeline, getTimeline } from "@/lib/api";
import { ChartView } from "../_components/ChartView";
import { Houses } from "../_components/Houses";
import { TimelineView } from "../_components/TimelineView";
import { BaziLuck } from "../_components/BaziBoard";
import { ZiweiLuck } from "../_components/ZiweiLuck";
import { AnnualView } from "../_components/AnnualView";
import { formFromQuery, toBirth } from "../_components/BirthFields";

// One-page full report: all 11 systems (chart + reading) + this year's annual report. Print → PDF.
const ORDER = ["bazi", "ziwei", "astrology", "jyotish", "qizheng", "iching", "suimei", "qimen", "liuren", "taiyi", "tieban"];

function ReportInner() {
  const q = useSearchParams();
  const f = formFromQuery(q);
  const [readings, setReadings] = useState<Record<string, Reading>>({});
  const [timelines, setTimelines] = useState<Record<string, Timeline>>({});
  const [annual, setAnnual] = useState<AnnualReport | null>(null);
  const [errs, setErrs] = useState<string[]>([]);
  const started = useRef(false);
  const done = Object.keys(readings).length;

  useEffect(() => {
    if (started.current) return;                 // React strict-mode double-invokes effects in dev
    started.current = true;
    const b = toBirth(f);
    const focus = q.get("focus") || null;
    ORDER.forEach((s) => {
      getReading(s, b, focus, "whole_sign").then((r) => setReadings((m) => ({ ...m, [s]: r })))
        .catch((e) => setErrs((x) => [...x, `${s}: ${e.message || e}`]));
      if (["bazi", "ziwei", "jyotish", "astrology"].includes(s))
        getTimeline(s, b).then((t) => setTimelines((m) => ({ ...m, [s]: t }))).catch(() => {});
    });
    getAnnual(b, new Date().getFullYear(), focus).then(setAnnual).catch((e) => setErrs((x) => [...x, `annual: ${e.message || e}`]));
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const subject = Object.values(readings)[0]?.subject || `${f.name || "命主"} · ${f.date} ${f.time}`;
  return (
    <div className="wrap report">
      <div className="noprint" style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12 }}>
        <button onClick={() => window.print()}>Print / Save PDF 列印・存 PDF</button>
        <span className="muted">{done}/{ORDER.length} systems ready 已完成</span>
      </div>
      <h1>Bazaar of Fates · 完整命盤報告</h1>
      <div className="sub">{subject}{f.tst === "1" ? " · 真太陽時" : ""} · generated {new Date().toISOString().slice(0, 10)}</div>
      {errs.map((e, i) => <div key={i} className="card err">{e}</div>)}

      {ORDER.map((s) => {
        const r = readings[s];
        if (!r) return <div key={s} className="card muted">{s}… casting 排盤中</div>;
        const t = timelines[s];
        return (
          <section key={s} className="rp-section">
            <div className="card">
              <h2>{r.system_en} · {r.system_zh}</h2>
              <div className="summary">{r.summary}</div>
              <div className={s === "bazi" ? "" : "cols"}>
                <div><ChartView r={r} /></div>
                <div><h3>Casting steps 排盤步驟</h3><ul className="chain">{r.reasoning_chain.map((c, i) => <li key={i}>{c}</li>)}</ul></div>
              </div>
              {["astrology", "qizheng", "jyotish"].includes(s) && r.ascendant && <div style={{ marginTop: 10 }}><Houses asc={r.ascendant} /></div>}
            </div>
            {s === "bazi" && r.chart?.dayun && <div className="card"><BaziLuck c={r.chart as any} /></div>}
            {s === "ziwei" && r.chart?.luck && <div className="card"><ZiweiLuck luck={r.chart.luck} palaces={r.chart.palaces || []} /></div>}
            {t && t.kind !== "none" && <div className="card"><TimelineView t={t} /></div>}
            <div className="card"><h3>Reading 解讀</h3><div className="interp">{r.interpretation}</div></div>
          </section>
        );
      })}

      {annual && <section className="rp-section"><AnnualView a={annual} /></section>}
    </div>
  );
}

export default function ReportPage() {
  return <Suspense fallback={<div className="wrap muted">loading…</div>}><ReportInner /></Suspense>;
}
