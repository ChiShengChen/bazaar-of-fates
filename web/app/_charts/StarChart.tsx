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

export interface CrossAspect { a: string; b: string; type: string; }

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
  chart, aspects = [], cusps = [], outer = [], crossAspects = [], outerLabel,
}: {
  chart: PlanetPosition[]; aspects?: string[]; cusps?: HouseCusp[];
  outer?: PlanetPosition[]; crossAspects?: CrossAspect[]; outerLabel?: string;
}) {
  const natal = place(chart, rNatal);
  const outerP = place(outer, rOuter);
  const withLon = cusps.filter((c) => typeof c.longitude === "number") as Required<HouseCusp>[];

  const natalLines = aspects.map((a) => {
    const t = a.split(/\s+/); const A = natal[t[0]], B = natal[t[2]];
    if (!A || !B) return null;
    return { pa: pos(A.lon, rAspect), pb: pos(B.lon, rAspect), color: ASPECT_COLOR[t[1]] || "#52525b", dash: "" };
  }).filter(Boolean) as any[];

  const crossLines = crossAspects.map((x) => {
    const A = natal[x.a], B = outerP[x.b];
    if (!A || !B) return null;
    return { pa: pos(A.lon, rAspect), pb: pos(B.lon, rAspect), color: ASPECT_COLOR[x.type] || "#52525b", dash: "3 2" };
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

      {natalLines.concat(crossLines).map((l, i) => (
        <line key={i} x1={l.pa.x} y1={l.pa.y} x2={l.pb.x} y2={l.pb.y}
              stroke={l.color} strokeWidth={0.75} opacity={0.5} strokeDasharray={l.dash} />
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

      {outerLabel && <text x={cx} y={14} fontSize={9} fill="#60a5fa" textAnchor="middle">{outerLabel}</text>}
      <circle cx={cx} cy={cy} r={2} fill="#52525b" />
    </svg>
  );
}
