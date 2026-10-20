"use client";
import { useEffect, useState } from "react";

// 四柱 column order. The backend always sends 年→月→日→時; Taiwanese traditional
// sheets print them right-to-left, i.e. 時 日 月 年 reading left to right, and lay
// the 大運 / 流年 / 流月 out right-to-left as well (BaziLuck reads the same setting).
// The choice is kept in localStorage and shared by every board on the page
// (main page, report) through a window event.

export type PillarOrder = "ymdh" | "hdmy";
const KEY = "bof.pillarOrder";
const EVT = "bof:pillar-order";

const read = (): PillarOrder => {
  try { return localStorage.getItem(KEY) === "hdmy" ? "hdmy" : "ymdh"; } catch { return "ymdh"; }
};

export function usePillarOrder(): [PillarOrder, (o: PillarOrder) => void] {
  const [order, setOrder] = useState<PillarOrder>("ymdh");   // localStorage only exists after mount
  useEffect(() => {
    const sync = () => setOrder(read());
    sync();
    window.addEventListener(EVT, sync);
    window.addEventListener("storage", sync);
    return () => { window.removeEventListener(EVT, sync); window.removeEventListener("storage", sync); };
  }, []);
  const set = (o: PillarOrder) => {
    try { localStorage.setItem(KEY, o); } catch { /* private mode: still switch this page */ }
    setOrder(o);
    window.dispatchEvent(new Event(EVT));
  };
  return [order, set];
}

export const inOrder = <T,>(xs: T[], order: PillarOrder): T[] => (order === "hdmy" ? [...xs].reverse() : xs);

export function PillarOrderSwitch({ order, onChange }: { order: PillarOrder; onChange: (o: PillarOrder) => void }) {
  return (
    <div className="pills noprint" style={{ margin: "0 0 8px" }} role="group" aria-label="排列方向 pillar order">
      <span className="muted" style={{ alignSelf: "center" }}>排列方向：</span>
      <span className={`pill${order === "ymdh" ? " on" : ""}`} role="button" aria-pressed={order === "ymdh"}
            title="left to right: year, month, day, hour" onClick={() => onChange("ymdh")}>年月日時</span>
      <span className={`pill${order === "hdmy" ? " on" : ""}`} role="button" aria-pressed={order === "hdmy"}
            title="Taiwanese traditional: hour, day, month, year from left to right; 大運・流年・流月 right-to-left" onClick={() => onChange("hdmy")}>時日月年（台灣傳統）</span>
    </div>
  );
}
