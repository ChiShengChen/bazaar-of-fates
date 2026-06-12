"use client";
import { Chart } from "@/lib/api";
import { StarChart } from "../_charts/StarChart";
import { RashiChart } from "../_charts/RashiChart";
import { QizhengChart } from "../_charts/QizhengChart";

// Dispatch each system to its richest available renderer; fall back to a clean
// reasoning panel for the text-only divinations.
export function ChartView({ r }: { r: Chart }) {
  const c = r.chart || {};

  if (r.system === "astrology")
    return (
      <StarChart chart={c.planets || []} aspects={c.aspects || []} aspectsDetail={c.aspects_detail}
                 cusps={r.ascendant?.houses || []}
                 outer={c.transits || []} crossAspects={c.transit_aspects || []} majorTransits={c.major_transits || []}
                 outerLabel={c.transits?.length ? `transits 行運 ${r.readings?.transit_date || ""}` : undefined} />
    );

  if (r.system === "jyotish") {
    const grahas = (c.grahas || []).map((g: any) => ({ name: g.graha, sidereal_lon: g.sidereal_lon, rashi: g.rashi }));
    return <RashiChart grahas={grahas} moonRashi={r.readings?.moon_rashi || ""}
                       dashaLord={r.readings?.mahadasha_lord || ""} />;
  }

  if (r.system === "qizheng") {
    const b = (c.bodies || []).map((x: any) => ({ name: x.body, ecliptic_lon: x.ecliptic_lon, sign: x.sign }));
    return <QizhengChart seven={b.slice(0, 7)} siyu={b.slice(7)}
                         mingZhuSign={r.readings?.ming_zhu_sign || ""} />;
  }

  if (r.system === "bazi" || r.system === "suimei") return <PillarsTable pillars={c.pillars || []} />;
  if (r.system === "ziwei") return <ZiweiBoard palaces={c.palaces || []} readings={r.readings || {}} subject={r.subject} />;
  if (r.system === "iching") return <HexagramView hex={c.hexagram} diagram={c.diagram || []} />;

  return <p className="muted">See the casting steps & elements below. / 詳見下方排盤步驟與命盤要素。</p>;
}

function PillarsTable({ pillars }: { pillars: any[] }) {
  if (!pillars.length) return null;
  const cols = pillars.map((p) => p.pillar || p.role || "");
  return (
    <table><thead><tr>{cols.map((c, i) => <th key={i}>{c}</th>)}</tr></thead>
      <tbody>
        <tr>{pillars.map((p, i) => <td key={i} style={{ fontSize: 22 }}>{p.gz}</td>)}</tr>
        <tr>{pillars.map((p, i) => <td key={i} className="muted">{p.stem_elem || ""}{p.branch_elem || ""} {p.zodiac || ""}{p.twelve_fortune ? `· ${p.twelve_fortune}` : ""}</td>)}</tr>
      </tbody>
    </table>
  );
}

// Traditional 紫微 命盤: the 12 palaces sit on the perimeter of a 4×4 grid, keyed by
// their 地支 (子…亥 in fixed geomantic cells); the centre 2×2 holds the natal summary.
const BRANCHES = "子丑寅卯辰巳午未申酉戌亥";
// branch index → [row, col] (1-indexed for CSS grid) on the 4×4 board
const CELL: Record<number, [number, number]> = {
  5: [1, 1], 6: [1, 2], 7: [1, 3], 8: [1, 4],   // 巳 午 未 申  (top)
  4: [2, 1],                       9: [2, 4],    // 辰 … 酉
  3: [3, 1],                       10: [3, 4],   // 卯 … 戌
  2: [4, 1], 1: [4, 2], 0: [4, 3], 11: [4, 4],   // 寅 丑 子 亥 (bottom)
};

function ZiweiBoard({ palaces, readings, subject }: { palaces: any[]; readings: any; subject: string }) {
  if (!palaces.length) return null;
  return (
    <div className="ziwei-board">
      {palaces.map((p, i) => {
        const bi = BRANCHES.indexOf(p.branch);
        const [row, col] = CELL[bi] || [1, 1];
        return (
          <div key={i} className={`zw-cell${p.is_body ? " body" : ""}`} style={{ gridRow: row, gridColumn: col }}>
            <div className="zw-stars">{(p.stars || []).join(" ")}</div>
            <div className="zw-name"><b>{p.name}</b> <span className="muted">{p.branch}</span></div>
          </div>
        );
      })}
      <div className="zw-center">
        <div className="muted" style={{ fontSize: 11 }}>{subject}</div>
        <div>命主 <b>{readings.soul_star || "?"}</b>・身主 {readings.body_star || "?"}</div>
        <div>{readings.five_elements_class || ""}・命宮 {readings.life_palace_branch || ""}</div>
        <div className="muted">生時 {readings.hour_branch || ""}・流年 {readings.ziwei_regime || ""}</div>
      </div>
    </div>
  );
}

function HexagramView({ hex, diagram }: { hex: any; diagram: string[] }) {
  if (!hex) return null;
  return (
    <div>
      <div className="hex">{diagram.map((l, i) => <div key={i}>{l}</div>)}</div>
      <p style={{ marginTop: 8 }}>本卦 <b>{hex.ben_name}</b> · 互卦 {hex.hu_name} · 變卦 {hex.bian_name}</p>
      <p className="muted">體 {hex.ti}（{hex.ti_wuxing}）· 用 {hex.yong}（{hex.yong_wuxing}）→ {hex.relation} {hex.verdict}</p>
    </div>
  );
}
