# Bazaar of Fates · 算命 Divination Suite

**Eleven traditional divination systems as deterministic Python engines**, behind one input — your **birth moment** (date + time + place) — each producing a reproducible chart plus an optional bilingual (English + 中文) AI reading. Plus a full **Western-astrology stack**: six house systems, transits, life timelines, and relationship charts (synastry / composite / Davison / group).

**十一套傳統命理系統**，寫成確定性 Python 排盤引擎，只吃一個輸入：**生辰**（日期＋時辰＋出生地），各自排出可重現的命盤＋可選的雙語 AI 解讀；外加完整的西洋占星套件（六種宮位制、行運、大運時間軸、關係合盤）。

> **Origin / 起源.** These engines began life as *placebo controls* in a larger quant project — divination cast as date-keyed trading signals, run through a lookahead-free backtest to prove they were noise. Here the **chart math is lifted out**, all trading/backtest stripped, and restored to its real purpose: **telling fortunes**. The 排盤 math is synced from the parent monorepo (single source of truth) via `scripts/sync_from_main.sh`; everything else — birth input, ascendant/house geometry, API, readings, web — is native to this repo.
> 這些引擎原本是某量化專案的「對照組／安慰劑」（把命理當訊號跑無未來函數回測，證明它們是雜訊）。這裡把排盤數學抽出、去掉交易回測，還原它本來的用途——算命。

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

> The synced engines compute planetary longitudes from the *date* alone (a stock has no hour or birthplace). The native `fortune/astro_ext.py` adds the **ascendant** and **houses** (needs time + place); `fortune/ziwei_ext.py` threads the real 時辰 into 紫微. When birth time or place is missing, ascendant-based systems gracefully degrade to date-only and flag it. / 缺時辰或出生地時自動退回只看日期並標註。

## Quickstart / 快速開始

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,llm]"          # drop "llm" to stay on the mock reader / 省略 llm 即用 mock
cp .env.example .env

uvicorn fortune.api.main:app --reload         # backend API / 後端

# Front end — choose one / 前端二選一：
cd web && npm install && npm run dev          # (a) Next.js, full UI (node ≥ 20) → :3000
python -m http.server 5500 --directory web    # (b) static page, no build → :5500/index.html
```

Runs with **no LLM key**: every chart casts deterministically; only the prose reading is a mocked facts digest. Set `LLM_BACKEND=anthropic` + `ANTHROPIC_API_KEY` for a real bilingual AI reading. Point the web app at a non-default backend with `NEXT_PUBLIC_API_BASE`.
不接 LLM 也能跑：命盤照排，解讀走 mock；設金鑰即得真正的雙語 AI 解讀。

```bash
curl -s localhost:8000/cast/bazi -H 'content-type: application/json' -d '{
  "name":"Mei","birth_date":"1990-06-15","birth_time":"14:30",
  "gender":"female","place":"Taipei","latitude":25.04,"longitude":121.56
}' | jq .summary
# "日主 辛金・身弱（喜生扶）・喜用 土、金"
```

> 📖 **Non-engineer's visual guide to the astrology stack: [docs/astrology.md](docs/astrology.md)** — what the wheel, houses, transits, progressions, synastry and group features mean and how to read them. / 給非工程的占星圖解指南。

## Features / 功能

**Charts & houses 命盤與宮位.** Each system renders its own visual: the circular 星盤 (astrology), 南印度 rāśi chart (Jyotiṣa), 七政星盤, the traditional 4×4 紫微 命盤, 四柱 pillars, hexagram lines. Astrology takes six **house systems** via `house_system`: `whole_sign` (default), `equal`, `placidus`, `koch`, `regiomontanus`, `campanus`. The four quadrant systems are **validated against Swiss Ephemeris to <0.006°** across five charts incl. high-latitude (Reykjavik 64°N) and southern-hemisphere (Sydney) — swisseph is a **dev-only oracle, not a runtime dependency** — and fall back to whole-sign past the polar circle. The star wheel draws house cusps as spokes (ASC/MC emphasised, house numbers), planets on an inner ring, and aspect lines **graded by orb** (tight = thick & bright).

**Readings 解讀.** Every chart gets a bilingual (English-then-中文) interpretation that reads only the deterministic facts. The astrology reading also folds in the chart ruler (命主星), angular planets, and the aspect list. Readings **stream** token-by-token over SSE (real Anthropic stream when keyed, chunked stub on mock).

**Timelines 時間軸.** Jyotiṣa Vimśottarī Mahādaśā (120-yr), BaZi 大運 (10-yr luck pillars, direction by 年干陰陽 × gender), 紫微 流年四化 — rendered as a dated bar timeline.

**Transits & progressions 行運與推運.** An **Overlay** selector adds an outer ring of either *transits* (today's/any-day sky) or *progressions* — switchable between **secondary** (1 day = 1 year) and **solar-arc** (the natal chart rotated rigidly by the progressed-Sun's arc). A **time slider** scrubs ±5 years and live-refreshes the ring via the LLM-free `/cast` (instant). The overlay also draws a **double tick-ring** and the overlay chart's **own house cusps** on the outer band. **Major transits 重要行運**: a slow planet (Jupiter/Saturn) within 3° of a natal angle (ASC/MC/DSC/IC) is highlighted with a gold halo + line, **graded by potency** (conjunction > square; tighter orbs glow stronger) and **phase** (solid ▸ *applying* vs dashed ▹ *separating*), and carries the **exact-trigger date** (zero-crossing search, retrograde-aware). **Major progressions 重要推運**: the progressed Moon's sign & house and its next sign-ingress date, plus a flag when the progressed Sun has changed sign. **Every transit & progression aspect** also carries applying ▸ / separating ▹ and an **exact date** (linear extrapolation of the moving body); solar-arc mode additionally lists the **ages each natal planet is directed to an angle** (e.g. SA Sun → MC at age 38).

**Relationships 合盤.** `POST /synastry` returns three charts, each with its own reading: the **bi-wheel** with cross-aspects (harmonious vs challenging), the **composite 組合中點盤** (longitude midpoints), and the **Davison 時空中點盤** (a real ephemeris chart for the midpoint moment in UT and midpoint location — distinct from the composite, with a Saturn/Jupiter-return timeline). `POST /group` (2–8 people) scores every pair into a clickable **matrix** — switchable between net / total / harmonious / challenging, and **reorderable** (sort by average compatibility to cluster the most in-sync, or nudge rows ▲▼) — flags the standout pairs, writes a group reading, and casts the **group composite** (circular mean of all members).

**Export 匯出.** Download any star/rāśi/七政 wheel as PNG (SVG→canvas, dependency-free) or print the whole reading to PDF.

## API

| method | path | |
|---|---|---|
| `GET` | `/systems` | the 11 systems + which cast cleanly / 11 系清單＋可用狀態 |
| `POST` | `/cast/{system}` | deterministic chart, no LLM → `Chart`（query: `house_system`, `transits`, `transit_date`）|
| `POST` | `/reading/{system}` | chart + bilingual reading → `Reading`（body: `focus`, `house_system`, `transits`）|
| `POST` | `/reading/{system}/stream` | SSE: a `chart` event then `delta` text events → progressive 解讀 |
| `POST` | `/timeline/{system}` | 大運 / Mahādaśā / 流年 → `Timeline` (kind=`none` if N/A) |
| `POST` | `/synastry` | two births → bi-wheel + composite + Davison (+ returns) + readings → `Synastry` |
| `POST` | `/group` | 2–8 births → pairwise cross-aspect matrix + group composite + reading → `Group` |

## Architecture / 架構

```
fortune/
  birth.py            BirthInput — the single input / 生辰輸入
  schemas.py          Chart / Reading / Timeline / Synastry / Group envelopes
  shared/             native: config / logging / llm (mock + anthropic, streaming)
  engines/<system>/   ← SYNCED 排盤 math from the monorepo (do NOT hand-edit)
  astro_ext.py        native: ascendant + 6 house systems (swisseph-validated)
  ziwei_ext.py        native: 紫微 with the real birth 時辰
  timeline.py         native: 大運 / Mahādaśā / 流年 sequences
  casting/<system>.py per-system adapter: birth → engine fns → Chart (+ transits, aspects)
  casting/__init__.py registry of the 11 systems (lazy import)
  synastry.py         native: synastry + composite + Davison (+ returns)
  group.py            native: group matrix + group composite
  interpret.py        chart facts + tradition prompt → bilingual reading (sync + stream)
  api/main.py         FastAPI (/systems /cast /reading[/stream] /timeline /synastry /group)
prompts/<system>/     ← SYNCED reading prompts from the monorepo
web/                  Next.js app (app/page.tsx, lib/api.ts, app/_components/, app/_charts/)
                      + static index.html (no-build fallback)
scripts/sync_from_main.sh   re-sync the 排盤 math
```

### Re-syncing the engine math / 重新同步排盤數學

```bash
scripts/sync_from_main.sh                 # default monorepo ~/Desktop/威鯨面試_LLMEng
scripts/sync_from_main.sh /path/to/monorepo
```

Sync overwrites **only** `fortune/engines/*` and `prompts/*` (the 排盤 math + author prompts). Everything native — birth input, ascendant/house geometry, transits, synastry/group, API, readings, the web app **including the chart renderers** (they carry house/transit/synastry overlays the monorepo's trading charts don't) — is never touched.
sync 只覆蓋排盤數學與門派 prompt；其餘原生檔（含星盤渲染器）不會被動到。

## Tests / 測試

```bash
pytest -q     # 52 tests: every system casts; house systems vs swisseph; transits;
              # timelines; synastry / composite / Davison; group matrix & composite
```

## License

For cultural, educational, and entertainment purposes. Divination is not a basis for financial, medical, or legal decisions.
僅供文化、教育與娛樂用途；命理不應作為財務、醫療或法律決策的依據。
