"use client";
import { useEffect, useState } from "react";

// 八字 almanac-style 排盤 sheet (the layout of a traditional 四柱八字排盤 page):
//   BaziBoard — header facts (胎元/命宮/節氣/起運/交運/農曆), the four-pillar table
//               (十神 / 天干 / 地支 / 藏干 / 納音 / 長生 / 空亡 / 神煞), 留意 relations, 稱骨
//   BaziLuck  — 大運 strip → the chosen 大運's 流年 → the chosen 流年's 流月, with
//               the 刑沖合會 notes + 神煞 for that 大運/流年 combination.
// All numbers come from fortune/bazi_ext.py; nothing is computed here.

type Hidden = { stem: string; god: string };
export interface Pillar {
  role: string; pillar: string; stem: string; branch: string; gz: string; stem_elem: string; branch_elem: string;
  zodiac: string; stem_god: string; hidden: Hidden[]; nayin: string; kong_wang: string; changsheng: string; shensha: string[];
}
interface LiuYue { gz: string; jie: string }
interface LiuNian {
  year: number; age: number; gz: string; stem_god: string; hidden: Hidden[]; nayin: string; changsheng: string;
  shensha: string[]; stem_notes: string[]; branch_notes: string[]; liuyue: LiuYue[]; nature: string; current: boolean;
}
interface DaYun {
  index: number; gz: string; stem: string; branch: string; stem_god: string; hidden: Hidden[]; nayin: string; changsheng: string;
  kong_wang: string; shensha: string[]; start_age: number; start_year: number; end_year: number;
  stem_notes: string[]; branch_notes: string[]; nature: string; current: boolean; liunian: LiuNian[];
}
export interface BaziChart {
  pillars: Pillar[]; day_master: { stem: string; elem: string; yinyang: string }; gender: string; gender_assumed: boolean;
  tai_yuan: string; tai_yuan_nayin: string; ming_gong: string; ming_gong_nayin: string;
  jie_prev: { name: string; at: string }; jie_next: { name: string; at: string };
  solar: string; time_known: boolean; lunar: { text: string; year_gz: string; zodiac: string };
  qi_yun: { forward: boolean; text: string; jiao_yun: string; huan_yun_digit: number; years: number };
  stem_notes: string[]; branch_notes: string[];
  cheng_gu: { weight: number; label: string; verdict: string };
  true_solar_time?: boolean; clock?: string;
  strength?: { label: string; ratio: number; support: number; drain: number; favourable: string[]; avoid: string[];
               yongshen: string; yongshen_why: string; tiaohou_note: string; pattern: string; pattern_note: string; lines: string[] };
  dayun: DaYun[]; xiaoyun: { age: number; year: number; gz: string; stem_god: string }[]; favourable: string[];
}

const ELEM_CLASS: Record<string, string> = { 木: "e-wood", 火: "e-fire", 土: "e-earth", 金: "e-metal", 水: "e-water" };
const STEM_ELEM: Record<string, string> = { 甲: "木", 乙: "木", 丙: "火", 丁: "火", 戊: "土", 己: "土", 庚: "金", 辛: "金", 壬: "水", 癸: "水" };
const BRANCH_ELEM: Record<string, string> = { 子: "水", 丑: "土", 寅: "木", 卯: "木", 辰: "土", 巳: "火", 午: "火", 未: "土", 申: "金", 酉: "金", 戌: "土", 亥: "水" };
const fmt = (iso: string) => iso.replace("T", " ");
const Char = ({ c, big }: { c: string; big?: boolean }) =>
  <span className={`bz-char ${ELEM_CLASS[STEM_ELEM[c] || BRANCH_ELEM[c] || c] || ""}`} style={{ fontSize: big ? 26 : 16 }}>{c}</span>;
const Notes = ({ label, xs }: { label: string; xs: string[] }) =>
  <div className="bz-note"><span className="muted">{label}：</span>{xs.length ? xs.join("；") : <span className="muted">—</span>}</div>;

export function BaziBoard({ c, name }: { c: BaziChart; name?: string }) {
  if (!c?.pillars?.length) return null;
  const dm = c.day_master;
  return (
    <div className="bz">
      <div className="bz-head">
        <div><span className="muted">姓名：</span>{name || "命主"}　<span className="muted">日主：</span><Char c={dm.stem} />（{dm.yinyang}{dm.elem}）　<span className="muted">性別：</span>{c.gender}{c.gender_assumed ? "（預設）" : ""}</div>
        <div><span className="muted">胎元：</span>{c.tai_yuan}［{c.tai_yuan_nayin}］　<span className="muted">命宮：</span>{c.ming_gong}［{c.ming_gong_nayin}］</div>
        <div><span className="muted">節氣：</span>{fmt(c.jie_prev.at)} {c.jie_prev.name}　{fmt(c.jie_next.at)} {c.jie_next.name}</div>
        <div><span className="muted">起運：</span>{c.qi_yun.text}（{c.qi_yun.forward ? "順行" : "逆行"}）{!c.time_known && <span className="muted">・時辰未知，以正午估算</span>}</div>
        <div><span className="muted">交運：</span>{fmt(c.qi_yun.jiao_yun)}　<span className="muted">換運：</span>以後每逢尾數 {c.qi_yun.huan_yun_digit} 的年份換運</div>
        <div><span className="muted">公曆：</span>{fmt(c.solar)}{c.true_solar_time && c.clock ? <span className="muted">（真太陽時；時鐘 {fmt(c.clock)}）</span> : null}　<span className="muted">農曆：</span>{c.lunar.text}</div>
        {c.strength && (
          <div><span className="muted">旺衰：</span>{c.strength.label}（得力 {Math.round(c.strength.ratio * 100)}%）　<span className="muted">格局：</span>{c.strength.pattern}　
            <span className="muted">用神：</span><Char c={c.strength.yongshen} />　<span className="muted">喜：</span>{c.strength.favourable.map((e) => <Char key={e} c={e} />)}　<span className="muted">忌：</span>{c.strength.avoid.map((e) => <Char key={e} c={e} />)}
            <div className="muted" style={{ fontSize: 12 }}>{c.strength.yongshen_why}；{c.strength.tiaohou_note}</div>
          </div>
        )}
      </div>

      <table className="bz-table">
        <thead><tr><th>四柱</th>{c.pillars.map((p) => <th key={p.role}>{p.pillar}</th>)}</tr></thead>
        <tbody>
          <tr><td className="muted">十神</td>{c.pillars.map((p) => <td key={p.role}>{p.stem_god}</td>)}</tr>
          <tr><td className="muted">天干</td>{c.pillars.map((p) => <td key={p.role}><Char c={p.stem} big /></td>)}</tr>
          <tr><td className="muted">地支</td>{c.pillars.map((p) => <td key={p.role}><Char c={p.branch} big /> <span className="muted">{p.zodiac}</span></td>)}</tr>
          <tr><td className="muted">藏干</td>{c.pillars.map((p) => <td key={p.role}>{p.hidden.map((h) => <div key={h.stem}><Char c={h.stem} />（{h.god}）</div>)}</td>)}</tr>
          <tr><td className="muted">納音</td>{c.pillars.map((p) => <td key={p.role}>{p.nayin}</td>)}</tr>
          <tr><td className="muted">長生</td>{c.pillars.map((p) => <td key={p.role}>{p.changsheng}</td>)}</tr>
          <tr><td className="muted">空亡</td>{c.pillars.map((p) => <td key={p.role}>{p.kong_wang}</td>)}</tr>
          <tr><td className="muted">神煞</td>{c.pillars.map((p) => <td key={p.role}>{p.shensha.length ? p.shensha.map((s) => <div key={s}>{s}</div>) : <span className="muted">—</span>}</td>)}</tr>
        </tbody>
      </table>

      <Notes label="天干留意" xs={c.stem_notes} />
      <Notes label="地支留意" xs={c.branch_notes} />
      <div className="bz-note"><span className="muted">稱骨重量：</span>{c.cheng_gu.label}（{c.cheng_gu.weight.toFixed(1)} 兩）</div>
      <div className="bz-note"><span className="muted">稱骨評語：</span>{c.cheng_gu.verdict}</div>
    </div>
  );
}

export function BaziLuck({ c }: { c: BaziChart }) {
  const dy = c?.dayun || [];
  const [di, setDi] = useState(() => Math.max(0, dy.findIndex((d) => d.current)));
  const [li, setLi] = useState(() => Math.max(0, (dy[Math.max(0, dy.findIndex((d) => d.current))]?.liunian || []).findIndex((l) => l.current)));
  useEffect(() => {  // a fresh cast → jump back to "now"
    const d0 = Math.max(0, dy.findIndex((d) => d.current));
    setDi(d0); setLi(Math.max(0, (dy[d0]?.liunian || []).findIndex((l) => l.current)));
  }, [c]);   // eslint-disable-line react-hooks/exhaustive-deps
  if (!dy.length) return null;
  const d = dy[Math.min(di, dy.length - 1)];
  const ln = d.liunian[Math.min(li, d.liunian.length - 1)];

  return (
    <div className="bz">
      <h3>大運 · 流年 · 流月 <span className="muted">— click to drill in 點選大運／流年</span></h3>
      {c.xiaoyun.length > 0 && (
        <div className="bz-note"><span className="muted">小運（起運前）：</span>{c.xiaoyun.map((x) => `${x.age}歲 ${x.year} ${x.gz}（${x.stem_god}）`).join("　")}</div>
      )}
      <div className="bz-strip">
        {dy.map((x, i) => (
          <div key={x.index} className={`bz-cell nat-${x.nature}${i === di ? " on" : ""}${x.current ? " now" : ""}`} onClick={() => { setDi(i); setLi(0); }}>
            <div className="muted">{x.start_age}歲 · {x.start_year}</div>
            <div className="bz-gz"><Char c={x.stem} big /><Char c={x.branch} big /></div>
            <div>{x.stem_god}</div>
            <div className="muted">{x.changsheng}</div>
          </div>
        ))}
      </div>

      <div className="bz-sub">
        <b>大運 {d.gz}</b>　{d.start_year}–{d.end_year}　十神 {d.stem_god}　藏干 {d.hidden.map((h) => `${h.stem}${h.god}`).join("、")}　納音 {d.nayin}　{d.changsheng}　空亡 {d.kong_wang}
        <Notes label="大運神煞" xs={d.shensha} />
      </div>

      <div className="bz-strip">
        {d.liunian.map((x, i) => (
          <div key={x.year} className={`bz-cell nat-${x.nature}${i === li ? " on" : ""}${x.current ? " now" : ""}`} onClick={() => setLi(i)}>
            <div className="muted">{x.age}歲 · {x.year}</div>
            <div className="bz-gz"><Char c={x.gz[0]} big /><Char c={x.gz[1]} big /></div>
            <div>{x.stem_god}</div>
            <div className="muted">{x.changsheng}</div>
          </div>
        ))}
      </div>

      <div className="bz-sub">
        <b>流年 {ln.year} {ln.gz}</b>　十神 {ln.stem_god}　藏干 {ln.hidden.map((h) => `${h.stem}${h.god}`).join("、")}　納音 {ln.nayin}　{ln.changsheng}
        <Notes label="流年神煞" xs={ln.shensha} />
        <Notes label="天干留意" xs={ln.stem_notes} />
        <Notes label="地支留意" xs={ln.branch_notes} />
      </div>

      <div className="bz-strip bz-months">
        {ln.liuyue.map((m) => (
          <div key={m.gz} className="bz-cell static">
            <div className="muted">{m.jie}</div>
            <div className="bz-gz"><Char c={m.gz[0]} /><Char c={m.gz[1]} /></div>
          </div>
        ))}
      </div>
      <div className="muted" style={{ marginTop: 6 }}>流月 by 節 (立春→寅月 … 小寒→丑月) · 綠＝喜用五行 {c.favourable.join("、")} · 紅＝忌耗</div>
    </div>
  );
}
