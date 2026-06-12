"use client";
import { useEffect, useState } from "react";
import {
  apiBase, getSystems, getReading, getTimeline,
  SystemInfo, Reading, Timeline, BirthInput,
} from "@/lib/api";
import { ChartView } from "./_components/ChartView";
import { Houses } from "./_components/Houses";
import { TimelineView } from "./_components/TimelineView";

export default function Page() {
  const [systems, setSystems] = useState<SystemInfo[]>([]);
  const [sys, setSys] = useState("bazi");
  const [houseSystem, setHouseSystem] = useState("whole_sign");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reading, setReading] = useState<Reading | null>(null);
  const [timeline, setTimeline] = useState<Timeline | null>(null);

  const [form, setForm] = useState({
    name: "Mei 小美", gender: "female", date: "1990-06-15", time: "14:30", place: "Taipei 台北",
    lat: "25.04", lon: "121.56", focus: "",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => { getSystems().then(setSystems).catch((e) => setErr(String(e.message || e))); }, []);

  function birth(): BirthInput {
    return {
      name: form.name || undefined, gender: form.gender || undefined,
      birth_date: form.date, birth_time: form.time || undefined, place: form.place || undefined,
      latitude: form.lat ? Number(form.lat) : undefined, longitude: form.lon ? Number(form.lon) : undefined,
    };
  }

  async function cast() {
    setBusy(true); setErr(null); setReading(null); setTimeline(null);
    try {
      const b = birth();
      const [r, t] = await Promise.all([
        getReading(sys, b, form.focus || null, houseSystem),
        getTimeline(sys, b).catch(() => null),
      ]);
      setReading(r); setTimeline(t);
    } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  }

  return (
    <div className="wrap">
      <h1>Bazaar of Fates · 算命</h1>
      <div className="sub">
        Eleven divination engines · one birth input · deterministic chart + bilingual AI reading<br />
        十一套傳統命理排盤引擎 · 一個生辰 · 確定性命盤 + 雙語 AI 解讀
      </div>

      <div className="card">
        <div className="grid">
          <div><label>Name 稱呼</label><input value={form.name} onChange={(e) => set("name", e.target.value)} /></div>
          <div><label>Gender 性別</label>
            <select value={form.gender} onChange={(e) => set("gender", e.target.value)}>
              <option value="">—</option><option value="female">female 女</option><option value="male">male 男</option>
            </select>
          </div>
          <div><label>Birth date 出生日期</label><input type="date" value={form.date} onChange={(e) => set("date", e.target.value)} /></div>
          <div><label>Birth time 出生時刻</label><input type="time" value={form.time} onChange={(e) => set("time", e.target.value)} /></div>
          <div><label>Birthplace 出生地</label><input value={form.place} onChange={(e) => set("place", e.target.value)} /></div>
          <div><label>Lat 緯度</label><input value={form.lat} onChange={(e) => set("lat", e.target.value)} /></div>
          <div><label>Lon 經度</label><input value={form.lon} onChange={(e) => set("lon", e.target.value)} /></div>
        </div>

        <div className="pills">
          {systems.map((s) => (
            <div key={s.key} className={`pill${s.key === sys ? " on" : ""}`} title={s.en}
                 onClick={() => setSys(s.key)}>{s.en} · {s.zh}{s.available ? "" : " ⚠"}</div>
          ))}
        </div>

        <div className="row">
          <div><label>Ask about (optional) 想問</label><input value={form.focus} onChange={(e) => set("focus", e.target.value)} placeholder="career / love / health 事業 / 感情 / 健康" /></div>
          {sys === "astrology" && (
            <div style={{ flex: 0, minWidth: 160 }}><label>Houses 宮位制</label>
              <select value={houseSystem} onChange={(e) => setHouseSystem(e.target.value)}>
                <option value="whole_sign">whole-sign 整星座</option>
                <option value="placidus">Placidus 不等宮</option>
              </select>
            </div>
          )}
          <div style={{ flex: 0 }}><button onClick={cast} disabled={busy}>{busy ? "Casting… 排盤中" : "Cast + Read 排盤＋解讀"}</button></div>
        </div>
        <div className="muted" style={{ marginTop: 10 }}>API: {apiBase()}</div>
      </div>

      {err && <div className="card err">{err}</div>}

      {reading && (
        <>
          <div className="card">
            <h3>{reading.system_en} · {reading.system_zh} · {reading.subject}</h3>
            <div className="summary">{reading.summary}</div>
            <div className="cols">
              <div><ChartView r={reading} /></div>
              <div>
                <h3>Casting steps 排盤步驟</h3>
                <ul className="chain">{reading.reasoning_chain.map((c, i) => <li key={i}>{c}</li>)}</ul>
              </div>
            </div>
          </div>

          {(reading.system === "astrology" || reading.system === "qizheng" || reading.system === "jyotish") && (
            <div className="card"><h3>Ascendant & Houses 上升與宮位</h3><Houses asc={reading.ascendant} /></div>
          )}

          {timeline && timeline.kind !== "none" && (
            <div className="card"><TimelineView t={timeline} /></div>
          )}

          <div className="card">
            <h3>Reading 解讀</h3>
            <div className="interp">{reading.interpretation}</div>
          </div>

          <div className="card">
            <h3>Chart elements 命盤要素</h3>
            <div className="kv">
              {Object.entries(reading.readings).map(([k, v]) => (
                <div key={k} style={{ display: "contents" }}>
                  <div className="k">{k}</div><div>{Array.isArray(v) ? v.join("、") : String(v)}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
