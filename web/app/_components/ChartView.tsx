"use client";
import { Chart } from "@/lib/api";
import { StarChart } from "../_charts/StarChart";
import { RashiChart } from "../_charts/RashiChart";
import { QizhengChart } from "../_charts/QizhengChart";
import { BaziBoard } from "./BaziBoard";

// Dispatch each system to its richest available renderer; fall back to a clean
// reasoning panel for the text-only divinations.
export function ChartView({ r, tightOnly = false }: { r: Chart; tightOnly?: boolean }) {
  const c = r.chart || {};
  const tight = <T extends { orb?: number }>(xs?: T[]) =>
    (xs || []).filter((x) => !tightOnly || (x.orb ?? 0) <= 3);

  if (r.system === "astrology") {
    // pick whichever overlay is present for the outer ring
    let outer = [], outerCusps = [], crossA, label, majorT = c.major_transits || [];
    if ((c.progressions || []).length) {
      outer = c.progressions; outerCusps = c.progression_houses || []; crossA = c.progression_aspects;
      label = `progressions 推運 (age ${r.readings?.progressed_age ?? ""})`; majorT = [];
    } else if ((c.solar_return || []).length) {
      outer = c.solar_return; outerCusps = c.solar_return_houses || []; crossA = c.solar_return_aspects;
      label = `solar return 太陽回歸 ${r.readings?.solar_return_year ?? ""}`; majorT = [];
    } else if ((c.lunar_return || []).length) {
      outer = c.lunar_return; outerCusps = c.lunar_return_houses || []; crossA = c.lunar_return_aspects;
      label = `lunar return 月亮回歸 ${(r.readings?.lunar_return_moment ?? "").slice(0, 10)}`; majorT = [];
    } else if ((c.transits || []).length) {
      outer = c.transits; crossA = c.transit_aspects; label = `transits 行運 ${r.readings?.transit_date || ""}`;
    }
    return (
      <StarChart chart={c.planets || []} aspects={c.aspects || []} aspectsDetail={tight(c.aspects_detail)}
                 cusps={r.ascendant?.houses || []}
                 outer={outer} outerCusps={outerCusps} crossAspects={tight(crossA)} majorTransits={majorT}
                 outerLabel={label} />
    );
  }

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

  if (r.system === "bazi" && c.dayun) return <BaziBoard c={c as any} name={r.subject.split(" · ")[0]} />;
  if (r.system === "bazi" || r.system === "suimei") return <PillarsTable pillars={c.pillars || []} />;
  if (r.system === "ziwei") return <ZiweiBoard palaces={c.palaces || []} readings={r.readings || {}} subject={r.subject} />;
  if (r.system === "iching") return <HexagramView hex={c.hexagram} diagram={c.diagram || []} />;
  if (r.system === "qimen" && c.palaces) return <QimenBoard palaces={c.palaces} ju={c.ju} zhifu={c.zhifu} zhishi={c.zhishi} />;
  if (r.system === "liuren" && c.courses) return <LiurenView c={c} />;

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
const MAJOR = new Set(["紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府", "太陰", "貪狼", "巨門", "天相", "天梁", "七殺", "破軍"]);
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
            <div className="zw-stars">
              {(p.stars || []).map((s: string) => {
                const major = MAJOR.has(s.replace(/\(.*\)/, ""));
                return <span key={s} className={major ? "zw-major" : "zw-minor"}>{s} </span>;
              })}
            </div>
            <div className="zw-name"><b>{p.name}</b> <span className="muted">{p.stem}{p.branch}</span>{p.changsheng ? <span className="muted" style={{ float: "right" }}>{p.changsheng}·{p.boshi}</span> : null}</div>
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

// 奇門 九宮 (Lo Shu layout: 巽4 離9 坤2 / 震3 中5 兌7 / 艮8 坎1 乾6), each cell: 八神 · 九星 · 八門 · 天盤干/地盤干
const LOSHU = [[4, 9, 2], [3, 5, 7], [8, 1, 6]];
function QimenBoard({ palaces, ju, zhifu, zhishi }: { palaces: any[]; ju: string; zhifu: string; zhishi: string }) {
  const by: Record<number, any> = {};
  palaces.forEach((p) => { by[p.palace] = p; });
  return (
    <div>
      <div className="muted" style={{ marginBottom: 6 }}>{ju} · 值符 {zhifu} · 值使 {zhishi}</div>
      <div className="qm-board">
        {LOSHU.flat().map((n) => {
          const p = by[n] || {};
          const cls = p.gate_cls === "吉" ? "good" : p.gate_cls === "凶" ? "bad" : "";
          return (
            <div key={n} className={`qm-cell ${cls}${p.god === "值符" ? " fu" : ""}`}>
              <div className="qm-top"><span>{p.god}</span><span className="muted">{p.name}</span></div>
              <div className="qm-mid"><b>{p.star}</b><span className="qm-stem">{p.sky_stem}</span></div>
              <div className="qm-mid"><span className={p.gate === zhishi ? "qm-shi" : ""}>{p.gate}</span><span className="qm-stem muted">{p.earth_stem}</span></div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// 大六壬: 天地盤 + 四課 + 三傳
function LiurenView({ c }: { c: any }) {
  return (
    <div>
      <div className="muted" style={{ marginBottom: 6 }}>{c.yue_jiang}將加{c.occupy}時 · 天盤／地盤</div>
      <div className="lr-plate">
        {(c.heaven_plate || []).map((x: any) => (
          <div key={x.ground} className="lr-cell"><b>{x.sky}</b><span className="muted">{x.ground}</span></div>
        ))}
      </div>
      <table style={{ marginTop: 10 }}>
        <thead><tr>{(c.courses || []).map((k: any) => <th key={k.name}>{k.name}</th>)}</tr></thead>
        <tbody>
          <tr>{(c.courses || []).map((k: any) => <td key={k.name} style={{ fontSize: 20 }}>{k.upper}</td>)}</tr>
          <tr>{(c.courses || []).map((k: any) => <td key={k.name} className="muted">{k.lower}</td>)}</tr>
        </tbody>
      </table>
      <p style={{ marginTop: 8 }}>{c.kind ? <span className="muted">{c.kind} · </span> : null}三傳：{(c.transmissions || []).map((t: string, i: number) => <b key={i} style={{ marginRight: 10 }}>{["初", "中", "末"][i]} {t}</b>)}</p>
    </div>
  );
}
