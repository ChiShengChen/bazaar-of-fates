"use client";

export interface FormState {
  name: string; gender: string; date: string; time: string; place: string; lat: string; lon: string;
}

export const emptyForm = (over: Partial<FormState> = {}): FormState => ({
  name: "", gender: "", date: "1990-06-15", time: "12:00", place: "", lat: "", lon: "", ...over,
});

export function toBirth(f: FormState) {
  return {
    name: f.name || undefined, gender: f.gender || undefined,
    birth_date: f.date, birth_time: f.time || undefined, place: f.place || undefined,
    latitude: f.lat ? Number(f.lat) : undefined, longitude: f.lon ? Number(f.lon) : undefined,
  };
}

export function BirthFields({ f, set }: { f: FormState; set: (k: keyof FormState, v: string) => void }) {
  return (
    <div className="grid">
      <div><label>Name 稱呼</label><input value={f.name} onChange={(e) => set("name", e.target.value)} /></div>
      <div><label>Gender 性別</label>
        <select value={f.gender} onChange={(e) => set("gender", e.target.value)}>
          <option value="">—</option><option value="female">female 女</option><option value="male">male 男</option>
        </select>
      </div>
      <div><label>Birth date 出生日期</label><input type="date" value={f.date} onChange={(e) => set("date", e.target.value)} /></div>
      <div><label>Birth time 出生時刻</label><input type="time" value={f.time} onChange={(e) => set("time", e.target.value)} /></div>
      <div><label>Birthplace 出生地</label><input value={f.place} onChange={(e) => set("place", e.target.value)} /></div>
      <div><label>Lat 緯度</label><input value={f.lat} onChange={(e) => set("lat", e.target.value)} /></div>
      <div><label>Lon 經度</label><input value={f.lon} onChange={(e) => set("lon", e.target.value)} /></div>
    </div>
  );
}
