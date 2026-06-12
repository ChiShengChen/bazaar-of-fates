// Typed client for the Bazaar of Fates 算命 API.
const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// --- chart payload types (match fortune/casting/*.py) -------------------------
export interface PlanetPosition { body: string; ecliptic_lon: number; sign: string; sign_zh?: string; retrograde?: boolean; house?: number; }
// the synced SVG renderers read `.name`; ChartView maps the API rows (body/graha) onto these.
export interface Graha { name: string; sidereal_lon: number; rashi: string; }
export interface QizhengStar { name: string; ecliptic_lon: number; sign?: string; }

export interface HouseCusp { house: number; sign?: string; sign_zh?: string; rashi?: string; longitude?: number; }
export interface Ascendant {
  longitude: number; sign: string; sign_zh?: string;
  house_system: string; sidereal?: boolean; mc?: number; houses: HouseCusp[];
}

export interface SystemInfo { key: string; en: string; zh: string; available: boolean; }

export interface Chart {
  system: string; system_en: string; system_zh: string; subject: string; cast_at: string;
  chart: Record<string, any>; reasoning_chain: string[]; readings: Record<string, any>;
  summary: string; ascendant: Ascendant | null;
}
export interface Reading extends Chart { interpretation: string; cost_usd: number; }

export interface Period {
  index: number; label: string; detail: string; start: string; end: string;
  start_age: number | null; nature: string; current: boolean;
}
export interface Timeline {
  system: string; system_en: string; system_zh: string;
  kind: string; kind_label: string; periods: Period[]; note: string;
}

export interface BirthInput {
  name?: string; birth_date: string; birth_time?: string; gender?: string;
  place?: string; latitude?: number; longitude?: number; tz_offset_hours?: number;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}

export const apiBase = () => BASE;
export async function getSystems(): Promise<SystemInfo[]> {
  const r = await fetch(`${BASE}/systems`); if (!r.ok) throw new Error(r.statusText); return r.json();
}
export const getReading = (system: string, birth: BirthInput, focus: string | null, house_system: string) =>
  post<Reading>(`/reading/${system}`, { birth, focus, house_system });
export const getTimeline = (system: string, birth: BirthInput) =>
  post<Timeline>(`/timeline/${system}`, birth);
