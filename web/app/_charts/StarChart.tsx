// Circular zodiac wheel (星盤), SVG. Native to this repo (not synced) so it can carry
// 算命-specific overlays: house spokes/cusps, an optional outer ring (transit 行運 or a
// synastry partner 合盤), and cross-aspects between the two rings.
import { PlanetPosition, HouseCusp } from "@/lib/api";

const ZODIAC = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"];
const GLYPH: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂", Jupiter: "♃", Saturn: "♄",
  Rahu: "☊", Ketu: "☋",
};
const ASPECT_COLOR: Record<string, string> = {
  conjunction: "#a1a1aa", sextile: "#34d399", trine: "#34d399", square: "#fb7185", opposition: "#fb7185",
};
const ASPECT_ANGLE: Record<string, number> = { conjunction: 0, sextile: 60, square: 90, trine: 120, opposition: 180 };

export interface CrossAspect { a: string; b: string; type: string; orb?: number; phase?: string; exact_date?: string | null; }
export interface MajorTransit { transit: string; angle: string; type: string; angle_lon: number; orb: number; weight?: number; phase?: string; }
const ASPECT_GLYPH: Record<string, string> = { conjunction: "☌", opposition: "☍", square: "□" };

// tighter orb → thicker, brighter line; wide orb → thin, faint
function grade(orb: number, maxOrb = 6) {
  const t = Math.max(0, Math.min(1, orb / maxOrb));
  return { w: 2.1 - 1.6 * t, op: 0.85 - 0.55 * t };
}

const S = 360, cx = S / 2, cy = S / 2;
const rZodOut = 172, rZodIn = 150, rSignGlyph = 161;
const rOuter = 132, rNatal = 104, rHouseNum = 88, rAspect = 76;

// ecliptic longitude λ → screen point. Aries 0° at 9 o'clock, signs run counter-clockwise.
function pos(lon: number, r: number) {
  const th = ((180 - lon) * Math.PI) / 180;
  return { x: cx + r * Math.cos(th), y: cy - r * Math.sin(th) };
}

// place a ring of planets, nudging colliding glyphs inward
function place(planets: PlanetPosition[], rBase: number) {
  const sorted = [...planets].sort((a, b) => a.ecliptic_lon - b.ecliptic_lon);
  const out: Record<string, { x: number; y: number; r: number; lon: number }> = {};
  let prev = -99, alt = false;
  for (const p of sorted) {
    const close = Math.abs(p.ecliptic_lon - prev) < 9;
    const r = close ? (alt ? rBase - 22 : rBase) : rBase;
    alt = close ? !alt : false;
    out[p.body] = { ...pos(p.ecliptic_lon, r), r, lon: p.ecliptic_lon };
    prev = p.ecliptic_lon;
  }
  return out;
}

export function StarChart({
  chart, aspects = [], aspectsDetail, cusps = [], outer = [], outerCusps = [],
  crossAspects = [], majorTransits = [], outerLabel,
}: {
  chart: PlanetPosition[]; aspects?: string[]; aspectsDetail?: CrossAspect[]; cusps?: HouseCusp[];
  outer?: PlanetPosition[]; outerCusps?: HouseCusp[]; crossAspects?: CrossAspect[];
  majorTransits?: MajorTransit[]; outerLabel?: string;
}) {
  const natal = place(chart, rNatal);
  const outerP = place(outer, rOuter);
  const withLon = cusps.filter((c) => typeof c.longitude === "number") as Required<HouseCusp>[];

  // intra-chart aspects: prefer structured (with orb) for grading, else parse the strings
  const detail: CrossAspect[] = aspectsDetail ?? aspects.map((a) => {
    const t = a.split(/\s+/); const m = a.match(/([\d.]+)°/);
    const sep = m ? parseFloat(m[1]) : null, ang = ASPECT_ANGLE[t[1]];
    return { a: t[0], b: t[2], type: t[1], orb: sep != null && ang != null ? Math.abs(sep - ang) : 3 };
  });
  const natalLines = detail.map((x) => {
    const A = natal[x.a], B = natal[x.b]; if (!A || !B) return null;
    return { pa: pos(A.lon, rAspect), pb: pos(B.lon, rAspect), color: ASPECT_COLOR[x.type] || "#52525b", dash: "", ...grade(x.orb ?? 3) };
  }).filter(Boolean) as any[];

  const crossLines = crossAspects.map((x) => {
    const A = natal[x.a], B = outerP[x.b]; if (!A || !B) return null;
    const dash = x.phase ? (x.phase === "applying" ? "" : "4 3") : "3 2";   // applying solid, separating dashed
    return { pa: pos(A.lon, rAspect), pb: pos(B.lon, rAspect), color: ASPECT_COLOR[x.type] || "#52525b", dash, ...grade(x.orb ?? 3) };
  }).filter(Boolean) as any[];

  return (
    <svg viewBox={`0 0 ${S} ${S}`} style={{ width: "100%", maxWidth: 360, margin: "0 auto", display: "block" }}
         role="img" aria-label="star chart">
      <circle cx={cx} cy={cy} r={rZodOut} fill="none" stroke="#3f3f46" />
      <circle cx={cx} cy={cy} r={rZodIn} fill="none" stroke="#3f3f46" />
      {outer.length > 0 && <circle cx={cx} cy={cy} r={rOuter + 14} fill="none" stroke="#27272a" />}
      <circle cx={cx} cy={cy} r={rNatal + 14} fill="none" stroke="#27272a" />

      {/* zodiac sign boundaries + glyphs */}
      {ZODIAC.map((g, i) => {
        const b0 = pos(i * 30, rZodOut), b1 = pos(i * 30, rZodIn), gp = pos(i * 30 + 15, rSignGlyph);
        return (
          <g key={i}>
            <line x1={b1.x} y1={b1.y} x2={b0.x} y2={b0.y} stroke="#3f3f46" strokeWidth={0.75} />
            <text x={gp.x} y={gp.y} fontSize={13} fill="#a78bfa" textAnchor="middle" dominantBaseline="central">{g}</text>
          </g>
        );
      })}

      {/* house cusps: spokes + house numbers; ASC (1) & MC (10) emphasised */}
      {withLon.map((c, i) => {
        const next = withLon[(i + 1) % withLon.length];
        const s0 = pos(c.longitude, rAspect), s1 = pos(c.longitude, rZodIn);
        const angular = c.house === 1 || c.house === 10;
        const span = ((next.longitude - c.longitude) % 360 + 360) % 360;
        const mid = pos(c.longitude + span / 2, rHouseNum);
        return (
          <g key={`h${c.house}`}>
            <line x1={s0.x} y1={s0.y} x2={s1.x} y2={s1.y}
                  stroke={angular ? "#a78bfa" : "#3f3f46"} strokeWidth={angular ? 1.2 : 0.5}
                  strokeDasharray={angular ? "" : "2 3"} />
            <text x={mid.x} y={mid.y} fontSize={9} fill="#71717a" textAnchor="middle" dominantBaseline="central">{c.house}</text>
            {c.house === 1 && <text x={s1.x} y={s1.y} fontSize={8} fill="#a78bfa" textAnchor="middle" dx={4}>ASC</text>}
            {c.house === 10 && <text x={s1.x} y={s1.y} fontSize={8} fill="#a78bfa" textAnchor="middle" dy={-3}>MC</text>}
          </g>
        );
      })}

      {/* outer overlay: a double tick-ring on the outer band + the outer chart's own house cusps */}
      {outer.length > 0 && Array.from({ length: 72 }, (_, k) => {
        const r0 = rOuter + 12, r1 = rOuter + (k % 6 === 0 ? 18 : 15);
        const a = pos(k * 5, r0), b = pos(k * 5, r1);
        return <line key={`tk${k}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#3b5a82" strokeWidth={k % 6 === 0 ? 0.8 : 0.4} />;
      })}
      {outerCusps.filter((c) => typeof c.longitude === "number").map((c) => {
        const s0 = pos(c.longitude!, rOuter + 2), s1 = pos(c.longitude!, rOuter + 12);
        const angular = c.house === 1 || c.house === 10;
        return (
          <g key={`oc${c.house}`}>
            <line x1={s0.x} y1={s0.y} x2={s1.x} y2={s1.y} stroke="#60a5fa"
                  strokeWidth={angular ? 1 : 0.5} opacity={0.7} strokeDasharray={angular ? "" : "2 2"} />
            {angular && <text {...pos(c.longitude!, rOuter + 20)} fontSize={7} fill="#60a5fa" textAnchor="middle">{c.house === 1 ? "asc" : "mc"}</text>}
          </g>
        );
      })}

      {natalLines.concat(crossLines).map((l, i) => (
        <line key={i} x1={l.pa.x} y1={l.pa.y} x2={l.pb.x} y2={l.pb.y}
              stroke={l.color} strokeWidth={l.w} opacity={l.op} strokeDasharray={l.dash} />
      ))}

      {/* natal planets (inner) */}
      {chart.map((p) => {
        const pl = natal[p.body]; if (!pl) return null;
        return (
          <g key={p.body}>
            <line x1={pos(p.ecliptic_lon, rZodIn).x} y1={pos(p.ecliptic_lon, rZodIn).y}
                  x2={pos(p.ecliptic_lon, pl.r + 9).x} y2={pos(p.ecliptic_lon, pl.r + 9).y} stroke="#3f3f46" strokeWidth={0.5} />
            <text x={pl.x} y={pl.y} fontSize={15} fill={p.retrograde ? "#fbbf24" : "#6ee7b7"} textAnchor="middle" dominantBaseline="central">{GLYPH[p.body] || "•"}</text>
            {p.retrograde && <text x={pl.x + 9} y={pl.y - 7} fontSize={7} fill="#f87171" textAnchor="middle">℞</text>}
          </g>
        );
      })}

      {/* outer ring: transit / synastry partner */}
      {outer.map((p) => {
        const pl = outerP[p.body]; if (!pl) return null;
        return (
          <text key={`o${p.body}`} x={pl.x} y={pl.y} fontSize={14}
                fill={p.retrograde ? "#fbbf24" : "#60a5fa"} textAnchor="middle" dominantBaseline="central">{GLYPH[p.body] || "•"}</text>
        );
      })}

      {/* major transits: slow planet on a natal angle — graded by potency (conjunction > square) */}
      {majorTransits.map((m, i) => {
        const tp = outerP[m.transit]; if (!tp) return null;
        const ap = pos(m.angle_lon, rZodIn);
        const w = m.weight ?? 0.7;                          // 0..1 strength
        const haloR = 8 + 6 * w, lineW = 1 + 2.2 * w, op = 0.45 + 0.45 * w;
        const applying = m.phase !== "separating";          // applying = building, separating = fading
        const mid = { x: (tp.x + ap.x) / 2, y: (tp.y + ap.y) / 2 };
        return (
          <g key={`mt${i}`}>
            {/* applying = solid (building), separating = dashed (fading) */}
            <line x1={tp.x} y1={tp.y} x2={ap.x} y2={ap.y} stroke="#fbbf24" strokeWidth={lineW} opacity={op}
                  strokeDasharray={applying ? "" : "3 3"} />
            <circle cx={tp.x} cy={tp.y} r={haloR} fill="none" stroke="#fbbf24" strokeWidth={1 + 0.8 * w} opacity={op} />
            {w >= 0.8 && <circle cx={tp.x} cy={tp.y} r={haloR + 3} fill="none" stroke="#fbbf24" strokeWidth={0.6} opacity={0.5} />}
            {/* arrow toward the angle (applying) or away (separating) */}
            <text x={mid.x} y={mid.y} fontSize={9} fill="#fbbf24" textAnchor="middle" dominantBaseline="central">{applying ? "▸" : "▹"}</text>
            <text x={ap.x} y={ap.y} dy={-3} fontSize={8} fill="#fbbf24" textAnchor="middle">{ASPECT_GLYPH[m.type] || ""}{m.angle}</text>
          </g>
        );
      })}

      {outerLabel && <text x={cx} y={14} fontSize={9} fill="#60a5fa" textAnchor="middle">{outerLabel}</text>}
      <circle cx={cx} cy={cy} r={2} fill="#52525b" />
    </svg>
  );
}
