"use client";
import { useEffect, useState } from "react";
import { apiBase } from "@/lib/api";

export interface FormState {
  name: string; gender: string; date: string; time: string; place: string; lat: string; lon: string;
  tz: string; tst: string;   // tz = UTC offset hours; tst = "1" → cast 干支 systems on true solar time
}

export const emptyForm = (over: Partial<FormState> = {}): FormState => ({
  name: "", gender: "", date: "1990-06-15", time: "12:00", place: "", lat: "", lon: "", tz: "8", tst: "", ...over,
});

export function toBirth(f: FormState) {
  return {
    name: f.name || undefined, gender: f.gender || undefined,
    birth_date: f.date, birth_time: f.time || undefined, place: f.place || undefined,
    latitude: f.lat ? Number(f.lat) : undefined, longitude: f.lon ? Number(f.lon) : undefined,
    tz_offset_hours: f.tz ? Number(f.tz) : 8, true_solar_time: f.tst === "1",
  };
}

// query-string round trip (used by the /report page)
export function formToQuery(f: FormState): string {
  const q = new URLSearchParams();
  (Object.keys(f) as (keyof FormState)[]).forEach((k) => { if (f[k]) q.set(k, f[k]); });
  return q.toString();
}
export function formFromQuery(q: URLSearchParams): FormState {
  const f = emptyForm();
  (Object.keys(f) as (keyof FormState)[]).forEach((k) => { const v = q.get(k); if (v != null) f[k] = v; });
  return f;
}

let CITIES: { name: string; aliases: string[] }[] | null = null;

export function BirthFields({ f, set }: { f: FormState; set: (k: keyof FormState, v: string) => void }) {
  const [note, setNote] = useState("");
  const [cities, setCities] = useState<{ name: string; aliases: string[] }[]>(CITIES || []);
  useEffect(() => {
    if (CITIES) return;
    fetch(`${apiBase()}/cities`).then((r) => r.json()).then((c) => { CITIES = c; setCities(c); }).catch(() => {});
  }, []);

  // birthplace → lat / lon / tz from the offline city table (Taiwan historical DST applied by date)
  async function lookup() {
    if (!f.place) return;
    try {
      const r = await fetch(`${apiBase()}/geo?q=${encodeURIComponent(f.place)}&on=${f.date}`);
      const g = await r.json();
      if (g && g.name) {
        set("lat", String(g.latitude)); set("lon", String(g.longitude)); set("tz", String(g.tz_offset_hours));
        setNote(`${g.name} · UTC${g.tz_offset_hours >= 0 ? "+" : ""}${g.tz_offset_hours}${g.note ? " · " + g.note : ""}`);
      } else setNote(g?.note || "unknown place 查無此地，請手動填經緯度");
    } catch { setNote(""); }
  }

  return (
    <div>
      <div className="grid">
        <div><label>Name 稱呼</label><input value={f.name} onChange={(e) => set("name", e.target.value)} /></div>
        <div><label>Gender 性別</label>
          <select value={f.gender} onChange={(e) => set("gender", e.target.value)}>
            <option value="">—</option><option value="female">female 女</option><option value="male">male 男</option>
          </select>
        </div>
        <div><label>Birth date 出生日期</label><input type="date" value={f.date} onChange={(e) => set("date", e.target.value)} /></div>
        <div><label>Birth time 出生時刻</label><input type="time" value={f.time} onChange={(e) => set("time", e.target.value)} /></div>
        <div><label>Birthplace 出生地</label>
          <input value={f.place} list="bf-cities" placeholder="台北 / Tokyo / New York…" onChange={(e) => set("place", e.target.value)} onBlur={lookup} />
          <datalist id="bf-cities">{cities.map((c) => <option key={c.name} value={c.name}>{c.aliases.slice(0, 2).join(" · ")}</option>)}</datalist>
        </div>
        <div><label>Lat 緯度</label><input value={f.lat} onChange={(e) => set("lat", e.target.value)} /></div>
        <div><label>Lon 經度</label><input value={f.lon} onChange={(e) => set("lon", e.target.value)} /></div>
        <div><label>UTC offset 時區</label><input value={f.tz} onChange={(e) => set("tz", e.target.value)} placeholder="8" /></div>
        <div><label>&nbsp;</label>
          <label style={{ display: "flex", gap: 6, alignItems: "center", cursor: "pointer", fontSize: 13 }}>
            <input type="checkbox" checked={f.tst === "1"} onChange={(e) => set("tst", e.target.checked ? "1" : "")} style={{ width: "auto" }} />
            true solar time 真太陽時（干支）
          </label>
        </div>
      </div>
      {note && <div className="muted" style={{ marginTop: 4 }}>{note}</div>}
    </div>
  );
}
