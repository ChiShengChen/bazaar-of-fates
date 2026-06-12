# Bazaar of Fates · 算命 Divination Suite

**Eleven traditional divination systems as deterministic Python engines**, behind one input — your **birth moment** (date + time + place) — each producing a reproducible chart plus an optional bilingual AI reading.

**十一套傳統命理系統**，寫成確定性 Python 排盤引擎，只吃一個輸入：**生辰**（出生日期＋時辰＋出生地），各自排出可重現的命盤＋可選的雙語 AI 解讀。

> **Origin / 起源.** These engines began life as *placebo controls* in a larger quant project — divination cast as date-keyed trading signals, run through a lookahead-free backtest to prove they were noise. Here the **chart math is lifted out**, all trading/backtest stripped, and restored to its real purpose: **telling fortunes**. The 排盤 math is synced from the parent monorepo (single source of truth) via `scripts/sync_from_main.sh`; the product shell (birth input, API, readings, web) is native to this repo.
> 這些引擎原本是某量化專案裡的「對照組／安慰劑」（把命理當訊號跑無未來函數回測，證明它們是雜訊）。這裡把排盤數學抽出、去掉交易回測，還原它本來的用途——算命。

## The eleven systems / 十一系

| key | System | 系統 | engine core | time-aware 時辰 | place-aware 出生地 |
|---|---|---|---|:--:|:--:|
| `astrology` | Western Astrology | 西洋占星 | `ephem` ecliptic longitudes | moon phase | planned 規劃中 |
| `bazi` | BaZi · Four Pillars | 八字（四柱）| JDN-anchored 干支 | ✅ hour pillar | — |
| `ziwei` | Zi Wei Dou Shu | 紫微斗數 | pure-Python 排盤 | planned 規劃中 | — |
| `iching` | Plum-Blossom I Ching | 梅花易數 | time-cast hexagram | — | — |
| `suimei` | Shichū-Suimei (JP) | 四柱推命（日）| 十二運星 + 天中殺 | ✅ | — |
| `qizheng` | Seven Luminaries | 七政四餘 | real astronomical longitudes | — | planned 規劃中 |
| `tieban` | Iron Plate | 鐵板神數 | 起命數 | — | — |
| `qimen` | Qi Men Dun Jia | 奇門遁甲 | 八門九宮起局 | — | — |
| `liuren` | Da Liu Ren | 大六壬 | 四課三傳 | — | — |
| `taiyi` | Tai Yi Shen Shu | 太乙神數 | 太乙九宮 | — | — |
| `jyotish` | Jyotiṣa (Vedic) | 吠陀占星 | sidereal + Vimśottarī daśā | — | planned 規劃中 |

> **Honest note / 誠實標註.** BaZi and Suimei already use `time` for the hour pillar; the time/place fields are carried on `BirthInput` for every system, but ascendant/house/命宮 computation in astrology · ziwei · qizheng · jyotish is a **planned engine upgrade** — to be written in the parent monorepo and synced over, not hand-patched here.

## Quickstart / 快速開始

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,llm]"          # drop "llm" to stay on the mock reader / 省略 llm 即用 mock
cp .env.example .env

# Backend API / 後端
uvicorn fortune.api.main:app --reload

# Static fortune page, no node build / 靜態算命頁，免 node build
python -m http.server 5500 --directory web
# open http://localhost:5500/ → fill birth → pick a system → see chart + reading
```

Runs with **no LLM key**: every chart casts deterministically; only the prose reading is a mocked facts digest. Set `LLM_BACKEND=anthropic` + `ANTHROPIC_API_KEY` for a real **bilingual (English + 中文)** AI reading.
不接 LLM 也能跑：命盤照排，只有解讀走 mock。設金鑰後即得真正的雙語 AI 解讀。

## API

| method | path | |
|---|---|---|
| `GET` | `/systems` | the 11 systems + which cast cleanly / 11 系清單＋可用狀態 |
| `POST` | `/cast/{system}` | deterministic chart, no LLM → `Chart` / 純命盤 |
| `POST` | `/reading/{system}` | chart + bilingual reading → `Reading` / 命盤＋解讀 |

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
  casting/<system>.py per-system adapter: birth → engine fns → Chart
  casting/__init__.py registry of the 11 systems (lazy import)
  interpret.py        chart facts + tradition prompt → bilingual reading
  api/main.py         FastAPI
prompts/<system>/     ← synced reading prompts from the monorepo
web/index.html        static fortune page + synced chart renderers
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
