# Bazaar of Fates · 算命 Divination Suite

**Eleven traditional divination systems as deterministic Python engines**, behind one input — your **birth moment** (date + time + place) — each producing a reproducible chart plus an optional bilingual AI reading.

**十一套傳統命理系統**，寫成確定性 Python 排盤引擎，只吃一個輸入：**生辰**（出生日期＋時辰＋出生地），各自排出可重現的命盤＋可選的雙語 AI 解讀。

> **Origin / 起源.** These engines began life as *placebo controls* in a larger quant project — divination cast as date-keyed trading signals, run through a lookahead-free backtest to prove they were noise. Here the **chart math is lifted out**, all trading/backtest stripped, and restored to its real purpose: **telling fortunes**. The 排盤 math is synced from the parent monorepo (single source of truth) via `scripts/sync_from_main.sh`; the product shell (birth input, API, readings, web) is native to this repo.
> 這些引擎原本是某量化專案裡的「對照組／安慰劑」（把命理當訊號跑無未來函數回測，證明它們是雜訊）。這裡把排盤數學抽出、去掉交易回測，還原它本來的用途——算命。

## The eleven systems / 十一系

| key | System | 系統 | engine core | time-aware 時辰 | place-aware 出生地 |
|---|---|---|---|:--:|:--:|
| `astrology` | Western Astrology | 西洋占星 | `ephem` ecliptic longitudes | ✅ asc + houses | ✅ ascendant |
| `bazi` | BaZi · Four Pillars | 八字（四柱）| JDN-anchored 干支 | ✅ hour pillar | — |
| `ziwei` | Zi Wei Dou Shu | 紫微斗數 | pure-Python 排盤 | ✅ 命宮/身宮/局 | — |
| `iching` | Plum-Blossom I Ching | 梅花易數 | time-cast hexagram | — | — |
| `suimei` | Shichū-Suimei (JP) | 四柱推命（日）| 十二運星 + 天中殺 | ✅ | — |
| `qizheng` | Seven Luminaries | 七政四餘 | real astronomical longitudes | ✅ 命宮 | ✅ 命度/命宮 |
| `tieban` | Iron Plate | 鐵板神數 | 起命數 | — | — |
| `qimen` | Qi Men Dun Jia | 奇門遁甲 | 八門九宮起局 | — | — |
| `liuren` | Da Liu Ren | 大六壬 | 四課三傳 | — | — |
| `taiyi` | Tai Yi Shen Shu | 太乙神數 | 太乙九宮 | — | — |
| `jyotish` | Jyotiṣa (Vedic) | 吠陀占星 | sidereal + Vimśottarī daśā | ✅ Lagna + bhāva | ✅ Lagna |

> **Ascendant & houses / 上升與宮位.** The synced engines compute planetary longitudes from the *date* alone (a stock has no birth hour or birthplace). The native `fortune/astro_ext.py` adds the **ascendant** (rising degree, validated so that at sunrise the Sun sits on the ascendant) and **whole-sign houses**, shared by astrology · qizheng · jyotish; `fortune/ziwei_ext.py` threads the real 時辰 into 紫微's 命宮/身宮/五行局/星位. These live natively (not in the monorepo) because they are meaningless for the trading placebo, and `sync_from_main.sh` never touches them. **House system is whole-sign** (Vedic default; Placidus is a planned Western option). When birth time or place is missing, ascendant-based systems gracefully degrade to date-only and flag it. / 缺時辰或出生地時自動退回只看日期並標註。

## Quickstart / 快速開始

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,llm]"          # drop "llm" to stay on the mock reader / 省略 llm 即用 mock
cp .env.example .env

# Backend API / 後端
uvicorn fortune.api.main:app --reload

# Front end — choose one / 前端二選一：

# (a) Next.js app with SVG charts + timelines / 含星盤命盤與大運時間軸（需 node ≥ 20）
cd web && npm install && npm run dev      # http://localhost:3000
# build check: npm run build

# (b) Static page, no node build / 靜態頁，免 node build
python -m http.server 5500 --directory web   # http://localhost:5500/index.html
```

The Next.js app draws the **circular 星盤** (astrology), **南印度 rāśi chart** (Jyotiṣa), **七政星盤**, 四柱/紫微 grids, ascendant + houses, the bilingual reading, and a **大運/流年 timeline**. Point it at a non-default API with `NEXT_PUBLIC_API_BASE`.

Runs with **no LLM key**: every chart casts deterministically; only the prose reading is a mocked facts digest. Set `LLM_BACKEND=anthropic` + `ANTHROPIC_API_KEY` for a real **bilingual (English + 中文)** AI reading.
不接 LLM 也能跑：命盤照排，只有解讀走 mock。設金鑰後即得真正的雙語 AI 解讀。

## API

| method | path | |
|---|---|---|
| `GET` | `/systems` | the 11 systems + which cast cleanly / 11 系清單＋可用狀態 |
| `POST` | `/cast/{system}?house_system=placidus` | deterministic chart, no LLM → `Chart` / 純命盤 |
| `POST` | `/reading/{system}` | chart + bilingual reading (`house_system` in body) → `Reading` |
| `POST` | `/reading/{system}/stream` | SSE: a `chart` event then `delta` text events → progressive 解讀 |
| `POST` | `/timeline/{system}` | 大運 / Mahādaśā / 流年 sequence → `Timeline` (kind=`none` if N/A) |
| `POST` | `/synastry` | two births → both charts + cross-aspects + 合盤 reading → `Synastry` |

**Star wheel 星盤** — the astrology SVG draws the 12 house cusps as spokes (ASC/MC emphasised, house numbers), natal planets on an inner ring, and aspect lines **graded by orb** (tight aspects thicker & brighter, wide ones thin & faint). **Transits 行運** — an outer ring overlays the sky on any date; the UI has a **time slider** that scrubs ±5 years and live-refreshes the ring via the LLM-free `/cast` (so dragging is instant). **Synastry 合盤** (`/synastry`) — two charts in one bi-wheel with their cross-aspects (harmonious vs challenging) **plus the composite 組合中點盤** (each planet at the midpoint of the two natal positions, with its own ascendant).

**Houses 宮位制** — astrology takes `house_system`: `whole_sign` (default), `equal`, `placidus`, `koch`, `regiomontanus`, or `campanus`. The four quadrant systems are **validated against Swiss Ephemeris to <0.006°** across five charts incl. high-latitude (Reykjavik 64°N) and southern-hemisphere (Sydney); swisseph is a **dev-only oracle, not a runtime dependency**. Quadrant systems fall back to whole-sign past the polar circle. **Deeper reading** — the astrology 解讀 also gets the chart ruler (命主星), angular planets, and aspect list folded into the prompt. **Streaming 串流** — `/reading/.../stream` streams the reading token-by-token (real Anthropic stream when keyed, chunked stub on mock). **Export 匯出** — the web app downloads the star/rāśi/七政 chart as PNG and prints the whole reading to PDF. **Timelines 時間軸** — Jyotiṣa Vimśottarī Mahādaśā (120-yr), BaZi 大運 (10-yr luck pillars, direction by 年干陰陽 × gender), 紫微 流年四化.

```bash
curl -s localhost:8000/cast/bazi -H 'content-type: application/json' -d '{
  "name":"Mei","birth_date":"1990-06-15","birth_time":"14:30",
  "gender":"female","place":"Taipei","latitude":25.04,"longitude":121.56
}' | jq .summary
# "日主 辛金・身弱（喜生扶）・喜用 土、金"
```

## Architecture / 架構

```
fortune/
  birth.py            BirthInput — the single input / 生辰輸入
  schemas.py          Chart / Reading envelope
  shared/             native: config / logging / llm (mock + anthropic)
  engines/<system>/   ← synced 排盤 math from the monorepo (do NOT hand-edit)
  astro_ext.py        native: ascendant + whole-sign + Placidus houses (astrology/qizheng/jyotish)
  ziwei_ext.py        native: 紫微 with the real birth 時辰 (reuses ziwei_core primitives)
  timeline.py         native: 大運 / Mahādaśā / 流年 sequences
  casting/<system>.py per-system adapter: birth → engine fns → Chart
  casting/__init__.py registry of the 11 systems (lazy import)
  interpret.py        chart facts + tradition prompt → bilingual reading
  api/main.py         FastAPI (/systems /cast /reading /timeline)
prompts/<system>/     ← synced reading prompts from the monorepo
web/                  Next.js app (app/page.tsx, lib/api.ts, _components/) + static index.html
  app/_charts/        ← synced SVG chart renderers (StarChart/RashiChart/QizhengChart)
scripts/sync_from_main.sh   re-sync the 排盤 math
```

### Re-syncing the engine math / 重新同步排盤數學

After the parent monorepo changes a system's casting logic:

```bash
scripts/sync_from_main.sh                 # default monorepo ~/Desktop/威鯨面試_LLMEng
scripts/sync_from_main.sh /path/to/monorepo
```

Only `fortune/engines/*`, `prompts/*`, `web/app/_charts/*` are overwritten (the 排盤 math + chart visuals). The birth input, API, readings, and web shell are native and **untouched**.
只覆蓋排盤數學與命盤視覺；生辰輸入、API、解讀、前端殼不會被動到。

## Tests / 測試

```bash
pytest -q     # all 11 systems cast a non-empty chart from one birth + a mock reading
```

## License

For cultural, educational, and entertainment purposes. Divination is not a basis for financial, medical, or legal decisions.
僅供文化、教育與娛樂用途；命理不應作為財務、醫療或法律決策的依據。
