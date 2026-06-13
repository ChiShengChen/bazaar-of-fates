"use client";
import { AnnualReport } from "@/lib/api";

export function AnnualView({ a }: { a: AnnualReport }) {
  const s = a.sections || {};
  return (
    <>
      <div className="card">
        <h3>年度報告 Annual Report · {a.subject} · {a.year}</h3>
        <div className="summary">{a.summary}</div>
        <div className="kv">
          {s.solar_return?.ascendant && <><div className="k">Solar Return 上升</div><div>{s.solar_return.ascendant} · {s.solar_return.moment}</div></>}
          {s.bazi && <><div className="k">八字流年</div><div>{s.bazi.liunian_element}（{s.bazi.verdict}）· 大運 {s.bazi.dayun} · 喜用 {(s.bazi.favourable || []).join("、")}</div></>}
          {s.ziwei && <><div className="k">紫微四化</div><div>{s.ziwei.year_stem}年：{(s.ziwei.sihua || []).join("、")}</div></>}
          {s.jyotish && <><div className="k">Jyotiṣa 大運</div><div>{s.jyotish.mahadasha_lord}（{s.jyotish.nature}）</div></>}
        </div>
        {(s.solar_return?.highlights?.length ?? 0) > 0 && (
          <>
            <h3 style={{ marginTop: 14 }}>Solar Return highlights 流年重點</h3>
            <ul className="chain">{s.solar_return!.highlights!.map((h, i) => <li key={i}>{h}</li>)}</ul>
          </>
        )}
        {(s.solar_return?.key_transits?.length ?? 0) > 0 && (
          <>
            <h3 style={{ marginTop: 14 }}>Key transits this year 今年關鍵行運</h3>
            <ul className="chain">{s.solar_return!.key_transits!.map((t: any, i: number) =>
              <li key={i}>{t.label} — {t.start}</li>)}</ul>
          </>
        )}
      </div>
      <div className="card">
        <h3>Reading 年度解讀</h3>
        <div className="interp">{a.interpretation}</div>
      </div>
    </>
  );
}
