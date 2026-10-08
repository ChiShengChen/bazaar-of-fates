"use client";
import { useEffect, useState } from "react";

// 紫微 大限 → 流年 drill-down: the 12 大限 (五行局起運, 陽男陰女順/逆) and, for the chosen 大限,
// its ten 流年 (太歲宮, 流年四化 + landing palaces, 流祿/羊/陀/魁/鉞/昌/馬, 歲前/將前十二神).
interface LiuNian {
  year: number; age: number; gz: string; taisui_palace: string; branch: string;
  sihua: string[]; sihua_landing: Record<string, string>; flow_stars: Record<string, string>;
  suiqian: Record<string, string>; jiangqian: Record<string, string>; current: boolean;
}
interface DaXian {
  index: number; palace: string; branch: string; stem: string; gz: string; ages: [number, number]; years: [number, number];
  changsheng: string; sihua: string[]; sihua_landing: Record<string, string>; current: boolean; liunian: LiuNian[];
}
export interface ZiweiLuckData { start_age: number; forward: boolean; age_now: number; daxian: DaXian[] }

const BR = "子丑寅卯辰巳午未申酉戌亥".split("");

export function ZiweiLuck({ luck, palaces }: { luck: ZiweiLuckData; palaces: { name: string; branch: string }[] }) {
  const dx = luck?.daxian || [];
  const cur = Math.max(0, dx.findIndex((d) => d.current));
  const [di, setDi] = useState(cur);
  const [li, setLi] = useState(() => Math.max(0, (dx[cur]?.liunian || []).findIndex((l) => l.current)));
  useEffect(() => { const c = Math.max(0, dx.findIndex((d) => d.current)); setDi(c); setLi(Math.max(0, (dx[c]?.liunian || []).findIndex((l) => l.current))); }, [luck]);  // eslint-disable-line react-hooks/exhaustive-deps
  if (!dx.length) return null;
  const d = dx[Math.min(di, dx.length - 1)];
  const ln = d.liunian[Math.min(li, d.liunian.length - 1)];
  const nameOf: Record<string, string> = {};
  palaces.forEach((p) => { nameOf[p.branch] = p.name; });

  return (
    <div className="bz">
      <h3>大限 · 流年 <span className="muted">— {luck.start_age} 虛歲起運・{luck.forward ? "順行" : "逆行"}・今年虛歲 {luck.age_now}</span></h3>
      <div className="bz-strip">
        {dx.map((x, i) => (
          <div key={x.index} className={`bz-cell nat-neutral${i === di ? " on" : ""}${x.current ? " now" : ""}`} onClick={() => { setDi(i); setLi(0); }}>
            <div className="muted">{x.ages[0]}–{x.ages[1]}歲</div>
            <div className="bz-gz" style={{ fontSize: 15 }}><b>{x.palace}</b></div>
            <div>{x.gz}</div>
            <div className="muted">{x.changsheng}</div>
          </div>
        ))}
      </div>
      <div className="bz-sub">
        <b>第{d.index + 1}大限 {d.palace}宮（{d.gz}）</b>　{d.years[0]}–{d.years[1]}　大限四化：{d.sihua.map((s, i) => <span key={s} style={{ marginRight: 8 }}>{s}→{d.sihua_landing[["祿", "權", "科", "忌"][i]]}</span>)}
      </div>
      <div className="bz-strip">
        {d.liunian.map((x, i) => (
          <div key={x.year} className={`bz-cell nat-neutral${i === li ? " on" : ""}${x.current ? " now" : ""}`} onClick={() => setLi(i)}>
            <div className="muted">{x.age}歲 · {x.year}</div>
            <div className="bz-gz"><b>{x.gz}</b></div>
            <div style={{ fontSize: 11 }}>太歲 {x.taisui_palace}</div>
          </div>
        ))}
      </div>
      <div className="bz-sub">
        <b>流年 {ln.year} {ln.gz}</b>　虛歲 {ln.age}　太歲在 {ln.taisui_palace}宮（{ln.branch}）
        <div className="bz-note"><span className="muted">流年四化：</span>{ln.sihua.map((s, i) => <span key={s} style={{ marginRight: 8 }}>{s}→{ln.sihua_landing[["祿", "權", "科", "忌"][i]]}</span>)}</div>
        <div className="bz-note"><span className="muted">流曜：</span>{Object.entries(ln.flow_stars).map(([k, v]) => `${k}${v}（${nameOf[v] || ""}）`).join("　")}</div>
        <table style={{ marginTop: 8, fontSize: 12 }}>
          <thead><tr><th>宮</th>{BR.map((b) => <th key={b} style={{ textAlign: "center" }}>{b}<div className="muted">{nameOf[b]}</div></th>)}</tr></thead>
          <tbody>
            <tr><td className="muted">歲前</td>{BR.map((b) => <td key={b} style={{ textAlign: "center" }} className={ln.suiqian[b] === "太歲" ? "qm-shi" : ""}>{ln.suiqian[b]}</td>)}</tr>
            <tr><td className="muted">將前</td>{BR.map((b) => <td key={b} style={{ textAlign: "center" }}>{ln.jiangqian[b]}</td>)}</tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
