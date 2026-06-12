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
    return <StarChart chart={c.planets || []} aspects={c.aspects || []} />;

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
  if (r.system === "ziwei") return <PalaceGrid palaces={c.palaces || []} />;
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

function PalaceGrid({ palaces }: { palaces: any[] }) {
  // 紫微 12 palaces laid out around a 4×4 ring (corners + edges); simple 4-col grid here.
  if (!palaces.length) return null;
  return (
    <div className="grid4">
      {palaces.map((p, i) => (
        <div key={i} className={`palace${p.is_body ? " body" : ""}`}>
          <div className="pn">{p.name} <span className="muted">{p.branch}</span></div>
          <div>{(p.stars || []).join(" ")}</div>
        </div>
      ))}
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
