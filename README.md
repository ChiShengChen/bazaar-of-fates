# 算命 · Divination Suite

十一套傳統命理系統，寫成**確定性 Python 排盤引擎**，前面接一層 LLM 解讀，後面只吃一個輸入：**生辰**（出生日期＋時辰＋出生地）。

> 起源：本專案的排盤引擎源自一個更大的量化研究專案，原本是當作「對照組／安慰劑」（把命理當成 date-keyed 訊號，跑無未來函數回測證明它們是雜訊）。這裡把**排盤數學**單獨抽出來，去掉所有交易／回測，還原成它本來的用途——**幫人算命**。排盤數學以 `scripts/sync_from_main.sh` 從母專案同步（單一真相源），算命產品殼（生辰輸入、API、解讀、前端）是本 repo 原生。

## 十一系

| key | 系統 | 引擎核心 | 時辰敏感 | 出生地敏感 |
|---|---|---|:--:|:--:|
| `astrology` | 西洋占星 | `ephem` 黃道經度 | 月相 | 規劃中（上升/宮位）|
| `bazi` | 八字（四柱）| JDN 校準干支 | ✅ 時柱 | — |
| `ziwei` | 紫微斗數 | 純 Python 排盤 | 規劃中（命宮）| — |
| `iching` | 梅花易數 | 時間起卦 | — | — |
| `suimei` | 四柱推命（日）| 十二運星＋天中殺 | ✅ | — |
| `qizheng` | 七政四餘 | 真實天文經度 | — | 規劃中 |
| `tieban` | 鐵板神數 | 起命數 | — | — |
| `qimen` | 奇門遁甲 | 八門九宮起局 | — | — |
| `liuren` | 大六壬 | 四課三傳 | — | — |
| `taiyi` | 太乙神數 | 太乙九宮 | — | — |
| `jyotish` | Jyotiṣa 吠陀占星 | 恆星黃道＋Vimśottarī 大運 | — | 規劃中 |

> **誠實標註**：八字／四柱推命已用 `時辰` 排時柱；占星／紫微／七政等的「時辰/出生地」欄位已在輸入層備好（`BirthInput`），但對應引擎的上升星座、命宮、宮位計算是**規劃中的引擎升級**——升級寫在母專案、再 sync 過來。

## 快速開始

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,llm]"          # llm 可省略；不裝就用 mock 解讀
cp .env.example .env

# 後端 API
uvicorn fortune.api.main:app --reload

# 靜態算命頁（免 node build）：用任意靜態伺服器開 web/index.html
python -m http.server 5500 --directory web
# 開 http://localhost:5500/  填生辰 → 選命理系統 → 看命盤＋解讀
```

不接 LLM 也能跑：每個命盤都會**確定性排出**，只有解讀文字是 mock 的事實摘要。設 `LLM_BACKEND=anthropic` + `ANTHROPIC_API_KEY` 即換成真正的 AI 解讀。

## API

| method | path | 說明 |
|---|---|---|
| `GET` | `/systems` | 11 系清單＋哪些可用 |
| `POST` | `/cast/{system}` | 純命盤（不呼叫 LLM）→ `Chart` |
| `POST` | `/reading/{system}` | 命盤＋解讀 → `Reading` |

```bash
curl -s localhost:8000/cast/bazi -H 'content-type: application/json' -d '{
  "name":"小美","birth_date":"1990-06-15","birth_time":"14:30",
  "gender":"女","place":"台北","latitude":25.04,"longitude":121.56
}' | jq .summary
# "日主 辛金・身弱（喜生扶）・喜用 土、金"
```

## 架構

```
fortune/
  birth.py            生辰輸入（唯一輸入）
  schemas.py          Chart / Reading 統一封裝
  shared/             原生：config / logging / llm（mock+anthropic）
  engines/<system>/   ← sync 自母專案的純排盤數學（勿手改，會被覆蓋）
  casting/<system>.py 每系 adapter：生辰 → 引擎函式 → Chart
  casting/__init__.py 11 系註冊表（惰性 import）
  interpret.py        命盤事實 + 門派 prompt → LLM 解讀
  api/main.py         FastAPI
prompts/<system>/     ← sync 自母專案的門派解讀 prompt
web/                  靜態算命頁 + sync 來的命盤渲染元件
scripts/sync_from_main.sh   重新同步排盤數學
```

### 重新同步排盤數學

母專案改了某系的排盤邏輯後：

```bash
scripts/sync_from_main.sh                 # 預設母專案 ~/Desktop/威鯨面試_LLMEng
scripts/sync_from_main.sh /path/to/monorepo
```

只會覆蓋 `fortune/engines/*`、`prompts/*`、`web/app/_charts/*`（排盤數學與命盤視覺）；
生辰輸入、API、解讀、前端殼是原生的，**不會被動到**。

## 測試

```bash
pytest -q     # 11 系各自從同一個生辰排出非空命盤 + mock 解讀
```
