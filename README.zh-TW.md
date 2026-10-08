<div align="center">

# 🔮 Bazaar of Fates · 算命

### 十三套傳統命理，一個生辰，確定性排盤＋可選語言的 AI 解讀

*西洋占星 · 八字 · 紫微斗數 · 梅花易數 · 六爻 · 小六壬 · 四柱推命 · 七政四餘 · 鐵板神數 · 奇門遁甲 · 大六壬 · 太乙神數 · Jyotiṣa*

[English](README.md) · **繁體中文** · [简体中文](README.zh-CN.md)

### 👉 [線上試玩 / Try it online](https://ms57rd-bazaar-of-fates.hf.space) — 免安裝、免金鑰 · `pip install bazaar-of-fates`

![Python](https://img.shields.io/badge/Python-3.10–3.13-3776AB?logo=python&logoColor=white)
![systems](https://img.shields.io/badge/命理系統-13-a78bfa)
![tests](https://img.shields.io/badge/tests-165%20passing-3fb950)
![license](https://img.shields.io/badge/license-MIT-green)

<table>
  <tr>
    <td align="center"><img src="docs/img/natal-wheel.png" width="260"/><br/><sub>西洋星盤</sub></td>
    <td align="center"><img src="docs/img/ziwei-chart.png" width="260"/><br/><sub>紫微斗數命盤</sub></td>
    <td align="center"><img src="docs/img/bazi-chart.png" width="260"/><br/><sub>八字完整排盤</sub></td>
  </tr>
</table>

</div>

## ⚡ 十秒上手

```bash
pip install bazaar-of-fates
bazaar bazi 1990-06-15 14:30 --place 台北 --gender female        # 終端機直接排八字，不用金鑰
bazaar ziwei 1990-06-15 14:30 --place 台北 --gender female       # 紫微 4×4 命盤
bazaar synthesis 1990-06-15 14:30 --gender female --ask "明年事業"   # 十三套對同一個問題的判斷
bazaar zeri 1990-06-15 14:30 --purpose wedding --from 2026-11-01 --to 2026-12-31   # 擇日
bazaar today 1990-06-15 14:30                                    # 今日運勢
bazaar love 1990-06-15 14:30 --gender female --ask "何時有正緣"      # 感情專科（加 --partner-date 合婚）
bazaar career 1990-06-15 14:30 --gender female --ask "該不該轉職"    # 專科：career | wealth | health | study | family
```

完整網頁版（Next.js）：

```bash
git clone https://github.com/ChiShengChen/bazaar-of-fates && cd bazaar-of-fates
python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev,llm,oracles]"
uvicorn fortune.api.main:app --reload            # API → :8000（同時提供免 build 的靜態頁）
cd web && npm install && npm run dev             # 完整 UI → :3000
```

不填 LLM 金鑰也能跑：所有命盤都是確定性計算，解讀會退回忠實的事實摘要。設定 `LLM_BACKEND=anthropic` 與 `ANTHROPIC_API_KEY` 即得真正的 AI 解讀；解讀語言可選中文、英文或雙語。

## ✨ 特色

| | |
|---|---|
| 🌏 **十三套系統，一個輸入** | 一個出生時刻排出全部命盤；輸入地名自動帶入經緯度與時區（台灣歷史日光節約時間會自動處理），可選**真太陽時**。 |
| 🎯 **真實天文、精確到分** | 行星取出生當下、當日真春分點黃道；24 節氣精確到分；六種宮位制對 Swiss Ephemeris 驗證到 0.006° 以內。 |
| 🔍 **每張盤都可核對** | 排盤步驟逐條列出：八字旺衰每一項計分、六壬課體所用規則、奇門遁元局的來源、擇日每一分的加減。 |
| 🧾 **八字完整排盤** | 十神、藏干、納音、空亡、神煞、十二長生、胎元命宮、起運交運、刑沖合會、稱骨、旺衰／用神／調候／格局，大運→流年→流月點選展開，黃曆區塊。 |
| 🌟 **紫微** | 36 顆星＋x-iztro 亮度與雜曜、格局；閏月與晚子時慣例；大限→流年（四化落宮、流曜、歲前將前）。 |
| 🧑‍⚖️ **綜合會診** | 一個問題，十三套各給依自家規則的判斷與依據，統計一致與相左，再由 AI 解釋各門派為何不同。 |
| 📅 **擇日・今日運勢** | 黃曆宜忌＋八字流日（沖日柱、歲破、月破、空亡、神煞）＋紫微流日四化＋奇門值使吉方＋小六壬，逐日打分、月曆呈現、每日吉時。 |
| 💞 **合盤與預測** | 西占合盤雙輪、組合盤、Davison、團體矩陣；跨系統年度報告與多年熱力圖。 |
| 💘 **感情專科** | 專看感情的命理師：命（八字配偶星與夫妻宮、紫微夫妻宮、西洋金星七宮、Jyotiṣa 七宮）、運（逐年**桃花年／婚緣年**評分，每一分列依據）、合（填對方生辰即**合婚**：八字日柱干支關係＋西占合盤），解讀先回答子題（何時有緣／合不合／復合／該不該分開／婚姻／第三者）。規則見 [docs/love.md](docs/love.md)。 |
| 🩺 **五科專科** | 同一骨架再開五科：**事業**（官殺與提綱、官祿宮、十宮土星、第十 bhāva＋事業方向表）、**財運**（財星與財庫、流年沖庫、財帛宮、二宮木星＋財性表）、**健康**（五行分布→臟腑、疾厄宮、六宮＋體質表；明說非醫療建議）、**學業**（印星文昌學堂、父母宮昌曲、九宮水星＋學習型態與科系表）、**家庭**（年柱父母宮、時柱子女宮與子女星、田宅宮、四宮月亮＋六親表）。每科：命、今年、逐年評分（每一分列依據）、先答子題。規則：[docs/specialists.md](docs/specialists.md)。 |
| 🤖 **CLI・API・MCP** | `bazaar` 指令列、FastAPI、`bazaar-mcp` 讓 Claude／Cursor 直接排盤，附 Claude Code skill。 |
| 🗃️ **資料集** | 一行指令窮舉紫微全部 518,400 張命盤（含七個主題的規則判斷），八字依日期區間產出。 |

## 🧭 十三套系統

| key | 系統 | 排盤核心 | 時辰 | 出生地 |
|---|---|---|:--:|:--:|
| `astrology` | 西洋占星 | ephem 當日黃道、六種宮位制、行運推運回歸 | ✅ | ✅ |
| `bazi` | 八字（四柱） | 精確節氣干支、完整排盤表 | ✅ | — |
| `ziwei` | 紫微斗數 | 原生安星＋x-iztro | ✅ | — |
| `iching` | 梅花易數 | 年月日時起卦（農曆） | ✅ | — |
| `liuyao` | 六爻（納甲） | 京房納甲、八宮世應、六親六神、伏神、旺衰 | ✅ | — |
| `xiaoliuren` | 小六壬 | 月日時六宮 | ✅ | — |
| `suimei` | 四柱推命（日） | 十二運星、天中殺 | ✅ | — |
| `qizheng` | 七政四餘 | 真實黃經、命度起宮 | ✅ | ✅ |
| `tieban` | 鐵板神數 | 太玄數起命數（替代模型） | ✅ | — |
| `qimen` | 奇門遁甲 | 時家轉盤，拆補／置閏 | ✅ | — |
| `liuren` | 大六壬 | 月將加時、四課三傳、九宗門、十二天將 | ✅ | — |
| `taiyi` | 太乙神數 | 太乙八宮（簡化） | — | — |
| `jyotish` | Jyotiṣa 吠陀占星 | 恆星黃道、Vimśottarī daśā | ✅ | ✅ |

> 時辰或出生地缺漏時，依賴上升的系統會自動退回只看日期並標註。

## 🔌 API

| 方法 | 路徑 | 說明 |
|---|---|---|
| `GET` | `/systems` · `/geo?q=` | 系統清單；地名→經緯度時區 |
| `POST` | `/cast/{system}` | 確定性命盤（不用 LLM） |
| `POST` | `/reading/{system}` `[/stream]` | 命盤＋解讀（`focus` 問題導向，`lang` 語言） |
| `POST` | `/synthesis` | 綜合會診 |
| `POST` | `/zeri` · `/day` | 擇日・今日運勢 |
| `POST` | `/love` | 感情專科：命・今年・桃花年婚緣年・合婚・解讀 |
| `POST` | `/consult/{topic}` · `GET /consult` | 五科專科（career／wealth／health／study／family，`auto` 依問題分科）：命・今年・逐年・專科表・解讀 |
| `POST` | `/timeline/{system}` · `/synastry` · `/group` · `/annual-report` · `/annual-overview` | 時間軸、合盤、團體、年度、多年 |

## 🤖 MCP server

```bash
pip install "bazaar-of-fates[mcp]"
# Claude Desktop / Claude Code / Cursor 設定：
# {"mcpServers": {"bazaar-of-fates": {"command": "bazaar-mcp"}}}
```

工具：`list_systems`、`geo_lookup`、`cast`、`reading`、`synthesis`、`zeri`、`day`、`synastry`。Skill 在 [`skills/bazaar-of-fates/SKILL.md`](skills/bazaar-of-fates/SKILL.md)。

## 🐳 部署

`Dockerfile` 一個容器同時提供 API 與靜態頁（port 7860），可直接放 Hugging Face Docker Space，免金鑰即可試玩；見 [deploy/hf-space-README.md](deploy/hf-space-README.md)。

## 📖 文件

每套系統一篇圖解指南（[docs/](docs/README.md)），另有[擇日規則](docs/zeri.md)、[引用與致謝](docs/CREDITS.md)（x-iztro、lunar-python、kinliuren、kinqimen、Swiss Ephemeris 等交叉驗證來源與授權）、[發布素材](docs/LAUNCH.md)。

## ✅ 測試

```bash
pytest -q     # 165 tests，其中多個對外部引擎交叉驗證（安裝 oracles extra 時啟用）
```

## 📜 授權

[MIT](LICENSE)。僅供文化、教育與娛樂用途；命理不應作為財務、醫療或法律決策的依據。
