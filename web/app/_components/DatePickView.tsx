"use client";
import { useState } from "react";
import { ZeriResult, ZeriDay, DayOutlook } from "@/lib/api";

// 擇日: a month-by-month calendar coloured by grade, click a day for its reasons / 宜忌 / 吉時 / 吉方.
const GRADE_CLASS = ["", "g1", "g2", "g3", "g4", "g5"];
const SRC_CLASS: Record<string, string> = { 黃曆: "src-alm", 八字: "src-bz", 紫微: "src-zw", 奇門: "src-qm", 小六壬: "src-xl" };

function groupByMonth(days: ZeriDay[]) {
  const m: Record<string, ZeriDay[]> = {};
  days.forEach((d) => { const k = d.date.slice(0, 7); (m[k] ||= []).push(d); });
  return Object.entries(m);
}

export function DayDetail({ d, purpose }: { d: ZeriDay | DayOutlook; purpose?: string }) {
  const hours = (d as any).hours as ZeriDay["hours"] | undefined;
  return (
    <div className="zr-detail">
      <div className="summary">{d.date} {d.weekday} · 農曆 {d.lunar} · {d.gz.year}年 {d.gz.month}月 <b>{d.gz.day}</b>日 · {"★".repeat(d.grade)}{"☆".repeat(5 - d.grade)} {d.verdict}（{d.score > 0 ? "+" : ""}{d.score}）</div>
      {(d as DayOutlook).context && (
        <div className="bz-note muted">大運 {(d as DayOutlook).context.dayun} · 流年 {(d as DayOutlook).context.liunian} · 流月 {(d as DayOutlook).context.liuyue} · {(d as DayOutlook).context.strength}，喜 {(d as DayOutlook).context.favourable.join("、")}</div>
      )}
      <ul className="chain">
        {d.reasons.map((r, i) => <li key={i}><span className={`zr-src ${SRC_CLASS[r.src] || ""}`}>{r.src}</span> <b className={r.delta > 0 ? "pos" : r.delta < 0 ? "neg" : ""}>{r.delta > 0 ? "+" : ""}{r.delta}</b> {r.text}</li>)}
      </ul>
      <div className="cols" style={{ marginTop: 8 }}>
        <div>
          {d.almanac && (
            <>
              <div className="bz-note"><span className="muted">宜：</span>{d.almanac.yi.join("、")}</div>
              <div className="bz-note"><span className="muted">忌：</span>{d.almanac.ji.join("、")}</div>
              <div className="bz-note"><span className="muted">建除 {d.almanac.jianchu} · {d.almanac.xiu}</span></div>
              <div className="bz-note"><span className="muted">方位：</span>{Object.entries(d.almanac.positions).map(([k, v]) => `${k}${v}`).join("　")}</div>
            </>
          )}
          <div className="bz-note"><span className="muted">八字流日：</span>{d.bazi.gz}（{d.bazi.stem_god}・{d.bazi.changsheng}）神煞 {d.bazi.shensha.join("、") || "—"}；{d.bazi.notes.join("；") || "—"}</div>
          {d.ziwei && <div className="bz-note"><span className="muted">紫微流日 {d.ziwei.gz}：</span>{d.ziwei.mutagen.map((m, i) => `${m}→${Object.values(d.ziwei!.landing)[i]}`).join("　")}</div>}
          <div className="bz-note"><span className="muted">奇門 {d.qimen.ju} 值使 {d.qimen.zhishi}（{d.qimen.cls}）· 吉方：</span>{d.qimen.lucky_dirs.join("、") || "—"}{d.qimen.unlucky_dirs.length ? <span className="muted"> · 避 {d.qimen.unlucky_dirs.join("、")}</span> : null}</div>
          <div className="bz-note"><span className="muted">小六壬：</span>{d.xiaoliuren}</div>
        </div>
        <div>
          {hours && (
            <>
              <div className="muted" style={{ marginBottom: 4 }}>吉時 (12 時辰) {purpose ? `· ${purpose}` : ""}</div>
              <div className="zr-hours">
                {hours.map((h) => (
                  <div key={h.branch} className={`zr-hour${h.best ? " best" : ""}${h.score < 0 ? " bad" : ""}`} title={h.reasons.join("；")}>
                    <b>{h.branch}</b><div className="muted">{h.hours}</div><div>{h.gz}</div><div className={h.score > 0 ? "pos" : h.score < 0 ? "neg" : ""}>{h.score > 0 ? "+" : ""}{h.score}</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export function DatePickView({ z }: { z: ZeriResult }) {
  const [sel, setSel] = useState<string | null>(z.best[0] || null);
  const by: Record<string, ZeriDay> = {};
  z.days.forEach((d) => { by[d.date] = d; });
  const cur = sel ? by[sel] : null;
  return (
    <>
      <div className="card">
        <h3>擇日 Date picking · {z.purpose_label} · {z.start} → {z.end}</h3>
        <div className="pills" style={{ marginBottom: 8 }}>
          {z.best.map((d, i) => <span key={d} className={`pill${sel === d ? " on" : ""}`} onClick={() => setSel(d)}>#{i + 1} {d.slice(5)} {"★".repeat(by[d].grade)}</span>)}
        </div>
        {groupByMonth(z.days).map(([month, days]) => {
          const first = new Date(days[0].date + "T00:00:00"); const pad = (first.getDay() + 6) % 7;
          return (
            <div key={month} className="zr-month">
              <div className="muted" style={{ margin: "6px 0 4px" }}>{month}</div>
              <div className="zr-grid">
                {["一", "二", "三", "四", "五", "六", "日"].map((w) => <div key={w} className="zr-wd muted">{w}</div>)}
                {Array.from({ length: pad }).map((_, i) => <div key={"p" + i} />)}
                {days.map((d) => (
                  <div key={d.date} className={`zr-day ${GRADE_CLASS[d.grade]}${sel === d.date ? " on" : ""}${z.best.includes(d.date) ? " best" : ""}`} onClick={() => setSel(d.date)} title={`${d.verdict} ${d.score}`}>
                    <div className="zr-num">{Number(d.date.slice(8))}</div>
                    <div className="zr-gz">{d.gz.day}</div>
                    <div className="zr-sc">{d.score > 0 ? "+" : ""}{d.score}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
        <div className="muted" style={{ marginTop: 6 }}>{z.rules.join("　|　")}{!z.ziwei_available ? "　（x-iztro 未安裝：無紫微流日）" : ""}{!z.almanac_available ? "　（lunar-python 未安裝：無黃曆）" : ""}</div>
      </div>
      {cur && <div className="card"><DayDetail d={cur} purpose={z.purpose_label} /></div>}
      {z.interpretation && <div className="card"><h3>Reading 解讀</h3><div className="interp">{z.interpretation}</div></div>}
    </>
  );
}
