<div align="center">

# 🔮 Bazaar of Fates · 算命

### 十三套传统命理＋姓名学，一个生辰，确定性排盘、专科命理师、可选语言的 AI 解读

*西洋占星 · 八字 · 紫微斗数 · 梅花易数 · 六爻 · 小六壬 · 四柱推命 · 七政四余 · 铁板神数 · 奇门遁甲 · 大六壬 · 太乙神数 · Jyotiṣa · 姓名学*

[English](README.md) · [繁體中文](README.zh-TW.md) · **简体中文**

### 👉 [在线试玩 / Try it online](https://ms57rd-bazaar-of-fates.hf.space) — 免安装、免密钥 · `pip install bazaar-of-fates`

![Python](https://img.shields.io/badge/Python-3.10–3.13-3776AB?logo=python&logoColor=white)
![systems](https://img.shields.io/badge/命理系统-13%20%2B%20姓名学-a78bfa)
![CI](https://github.com/ChiShengChen/bazaar-of-fates/actions/workflows/ci.yml/badge.svg)
![tests](https://img.shields.io/badge/tests-379%20passing-3fb950)
![license](https://img.shields.io/badge/license-MIT-green)

<table>
  <tr>
    <td align="center"><img src="docs/img/natal-wheel.png" width="260"/><br/><sub>西洋星盘</sub></td>
    <td align="center"><img src="docs/img/ziwei-chart.png" width="260"/><br/><sub>紫微斗数命盘</sub></td>
    <td align="center"><img src="docs/img/bazi-chart.png" width="260"/><br/><sub>八字完整排盘</sub></td>
  </tr>
</table>

</div>

## ⚡ 十秒上手

```bash
pip install bazaar-of-fates
bazaar bazi 1990-06-15 14:30 --place 台北 --gender female        # 终端机直接排八字，不用密钥
bazaar ziwei 1990-06-15 14:30 --place 台北 --gender female       # 紫微 4×4 命盘
bazaar synthesis 1990-06-15 14:30 --gender female --ask "明年事业"   # 十三套对同一个问题的判断
bazaar zeri 1990-06-15 14:30 --purpose wedding --from 2026-11-01 --to 2026-12-31   # 择日
bazaar today 1990-06-15 14:30                                    # 今日运势
bazaar love 1990-06-15 14:30 --gender female --ask "何时有正缘"      # 感情专科（加 --partner-date 合婚）
bazaar career 1990-06-15 14:30 --gender female --ask "该不该转职"    # 专科：career | wealth | health | study | family
bazaar ask qimen "明天面试会顺利吗"                              # 问事：qimen | liuren | iching（--numbers／--text）| liuyao（--coins）| xiaoliuren
bazaar xingming 1990-06-15 14:30 --full-name 陈美玲 --gender female   # 姓名学：五格、三才、配八字
```

完整网页版（Next.js）：

```bash
git clone https://github.com/ChiShengChen/bazaar-of-fates && cd bazaar-of-fates
python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev,llm,oracles]"
uvicorn fortune.api.main:app --reload            # API → :8000（同时提供免 build 的静态页）
cd web && npm install && npm run dev             # 完整 UI → :3000
```

不填 LLM 密钥也能跑：所有命盘都是确定性计算，解读会退回忠实的事实摘要。设置 `LLM_BACKEND=anthropic` 与 `ANTHROPIC_API_KEY` 即得真正的 AI 解读；解读语言可选中文、英文或双语。

## ✨ 特色

| | |
|---|---|
| 🌏 **十三套系统＋姓名学，一个输入** | 一个出生时刻排出全部命盘（填中文姓名另得姓名学）；输入地名自动带入经纬度与时区（台湾历史日光节约时间会自动处理），可选**真太阳时**。 |
| 🎯 **真实天文、精确到分** | 行星取出生当下、当日真春分点黄道；24 节气精确到分；六种宫位制对 Swiss Ephemeris 验证到 0.006° 以内。 |
| 🔍 **每张盘都可核对** | 排盘步骤逐条列出：八字旺衰每一项计分、六壬课体所用规则、奇门遁元局的来源、择日每一分的加减。 |
| 🧾 **八字完整排盘** | 十神、藏干、纳音、空亡、神煞、十二长生、胎元命宫、起运交运、刑冲合会、称骨、旺衰／用神／调候／格局，大运→流年→流月点击展开，黄历区块。 |
| 🌟 **紫微** | 36 颗星＋x-iztro 亮度与杂曜、格局；闰月与晚子时惯例；大限→流年（四化落宫、流曜、岁前将前）。 |
| 🧑‍⚖️ **综合会诊** | 一个问题，十三套各给依自家规则的判断与依据，统计一致与相左，再由 AI 解释各门派为何不同。 |
| 📅 **择日・今日运势** | 黄历宜忌＋八字流日（冲日柱、岁破、月破、空亡、神煞）＋紫微流日四化＋奇门值使吉方＋小六壬，逐日打分、月历呈现、每日吉时。 |
| 💞 **合盘与预测** | 西占合盘双轮、组合盘、Davison、团体矩阵；跨系统年度报告与多年热力图。 |
| 💘 **感情专科** | 专看感情的命理师：命（八字配偶星与夫妻宫、紫微夫妻宫、西洋金星七宫、Jyotiṣa 七宫）、运（逐年**桃花年／婚缘年**评分，每一分列依据）、合（填对方生辰即**合婚**：八字日柱干支关系＋西占合盘），解读先回答子题（何时有缘／合不合／复合／该不该分开／婚姻／第三者）。规则见 [docs/love.md](docs/love.md)。 |
| 🩺 **五科专科** | 同一骨架再开五科：**事业**（官杀与提纲、官禄宫、十宫土星、第十 bhāva＋事业方向表）、**财运**（财星与财库、流年冲库、财帛宫、二宫木星＋财性表）、**健康**（五行分布→脏腑、疾厄宫、六宫＋体质表；明说非医疗建议）、**学业**（印星文昌学堂、父母宫昌曲、九宫水星＋学习型态与科系表）、**家庭**（年柱父母宫、时柱子女宫与子女星、田宅宫、四宫月亮＋六亲表）。每科：命、今年、逐年评分（每一分列依据）、先答子题。规则：[docs/specialists.md](docs/specialists.md)。 |
| 🎲 **问事** | 不用生辰：奇门／六壬／梅花／六爻／小六壬以问事的那一刻起局——奇门时盘看日干宫（人）、时干宫（事）、依题用神、门迫空亡三奇、吉方；六壬时课看类神入传、末传与日干、课体；梅花**数字起卦**（1–3 数）与**字占**；六爻**金钱卦**（六次掷钱）；每一分列依据，附应期。规则：[docs/ask.md](docs/ask.md)。 |
| 🈷️ **姓名学** | 熊崎式五格：康熙笔画（每字标部首与 Unihan 出处）、天人地外总五格、81 数理、三才生克，再把每格五行对到本人八字喜用；没有生辰也能排。`POST /name`、`bazaar xingming`、MCP `name`。说明：[docs/xingming.md](docs/xingming.md)。 |
| 🤖 **CLI・API・MCP** | `bazaar` 指令列、FastAPI、`bazaar-mcp` 让 Claude／Cursor 直接排盘，附 Claude Code skill。 |
| 🗃️ **数据集** | 一行指令穷举紫微全部 518,400 张命盘（含七个主题的规则判断），八字依日期区间产出。 |

## 🧭 十三套系统（＋姓名学）

| key | 系统 | 排盘内核 | 时辰 | 出生地 |
|---|---|---|:--:|:--:|
| `astrology` | 西洋占星 | ephem 当日黄道、六种宫位制、行运推运回归 | ✅ | ✅ |
| `bazi` | 八字（四柱） | 精确节气干支、完整排盘表 | ✅ | — |
| `ziwei` | 紫微斗数 | 原生安星＋x-iztro；亮度流派 全书／中州／三级 | ✅ | — |
| `iching` | 梅花易数 | 年月日时起卦（农历） | ✅ | — |
| `liuyao` | 六爻（纳甲） | 京房纳甲、八宫世应、六亲六神、伏神、旺衰 | ✅ | — |
| `xiaoliuren` | 小六壬 | 月日时六宫 | ✅ | — |
| `suimei` | 四柱推命（日） | 十二运星、天中杀 | ✅ | — |
| `qizheng` | 七政四余 | 真实黄经、命度起宫 | ✅ | ✅ |
| `tieban` | 铁板神数 | 太玄数起命数（替代模型） | ✅ | — |
| `qimen` | 奇门遁甲 | 时家转盘，拆补／置闰 | ✅ | — |
| `liuren` | 大六壬 | 月将加时、四课三传、九宗门（8,640 课与 kinliuren 比对）、十二天将 | ✅ | — |
| `taiyi` | 太乙神数 | 年计：统宗积年、七十二局、太乙／文昌／始击／计神、主客算与大将参将、十六神、八门、断例（与 kintaiyi 对照） | — | — |
| `xingming` | 姓名学 | 熊崎式五格、康熙笔画（Unihan）、81 数理、三才、配八字喜用（需中文姓名） | — | — |
| `jyotish` | Jyotiṣa 吠陀占星 | 恒星黄道、Vimśottarī daśā | ✅ | ✅ |

> 时辰或出生地缺漏时，依赖上升的系统会自动退回只看日期并标注。

## 🔌 API

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/systems` · `/geo?q=` | 系统清单（姓名学标 `needs_name`）；地名→经纬度时区 |
| `POST` | `/cast/{system}` | 确定性命盘（不用 LLM） |
| `POST` | `/reading/{system}` `[/stream]` | 命盘＋解读（`focus` 问题导向，`lang` 语言） |
| `POST` | `/synthesis` | 综合会诊 |
| `POST` | `/zeri` · `/day` | 择日・今日运势 |
| `POST` | `/love` | 感情专科：命・今年・桃花年婚缘年・合婚・解读 |
| `POST` | `/consult/{topic}` · `GET /consult` | 五科专科（career／wealth／health／study／family，`auto` 依问题分科）：命・今年・逐年・专科表・解读 |
| `POST` | `/ask/{system}` | 问事：奇门／六壬／梅花／六爻／小六壬以问事时刻（或数字／字句／掷钱）起局，判断与依据、应期 |
| `POST` | `/name` | 姓名学：五格、81 数理、三才、配八字（`birth` 可省） |
| `POST` | `/timeline/{system}` · `/synastry` · `/group` · `/annual-report` · `/annual-overview` | 时间轴、合盘、团体、年度、多年 |

## 🤖 MCP server

```bash
pip install "bazaar-of-fates[mcp]"
# Claude Desktop / Claude Code / Cursor 设置：
# {"mcpServers": {"bazaar-of-fates": {"command": "bazaar-mcp"}}}
```

工具：`list_systems`、`geo_lookup`、`cast`、`reading`、`synthesis`、`zeri`、`day`、`synastry`、`love`、`consult`、`ask`、`name`。Skill 在 [`skills/bazaar-of-fates/SKILL.md`](skills/bazaar-of-fates/SKILL.md)。

## 🐳 部署

- **在线版**：[Hugging Face Space](https://ms57rd-bazaar-of-fates.hf.space)（Gradio，文件在 [deploy/hf-space/](deploy/hf-space/)），API 在 `/docs`、静态页在 `/web/`。
- **Docker**：`docker build -t bazaar . && docker run -p 7860:7860 bazaar` → API 与静态页同一容器（port 7860），免密钥；见 [deploy/hf-space-README.md](deploy/hf-space-README.md)。。

- **内置防线**：确定性端点的回应会缓存（`CACHE_TTL_SECONDS`，回应标头 `X-Cache`）；每个 IP 分两层限流（`RATE_LIMIT_PER_MINUTE` 一般、`LLM_RATE_LIMIT_PER_MINUTE` 会调用 LLM 的端点 → `429` 与 `Retry-After`）；LLM 同时调用数全站上限（`LLM_MAX_CONCURRENCY`；报告页一次只排两个解读）。`GET /health` 可看计数。设置见 [.env.example](.env.example)。

## 📖 文档

每套系统一篇图解指南（[docs/](docs/README.md)，含[姓名学](docs/xingming.md)），另有[择日规则](docs/zeri.md)、[感情专科](docs/love.md)、[五科专科](docs/specialists.md)、[问事](docs/ask.md)、[引用与致谢](docs/CREDITS.md)（x-iztro、lunar-python、kinliuren、kinqimen、kintaiyi、Swiss Ephemeris、Unihan 等来源与授权）、[发布素材](docs/LAUNCH.md)。

## ✅ 测试

```bash
pytest -q     # 379 tests：节气／行星／宫位对 Swiss Ephemeris、紫微对 x-iztro（全空间 518,400 盘）、六壬对 kinliuren（8,640 课）、奇门对 kinqimen、太乙对 kintaiyi、姓名学 166 字康熙笔画；交叉验证在未安装 oracles extra 时自动略过
```

## 📜 授权

[MIT](LICENSE)。仅供文化、教育与娱乐用途；命理不应作为财务、医疗或法律决策的依据。
