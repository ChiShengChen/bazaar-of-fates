# 西洋占星圖解指南 · A Visual Guide to the Astrology Suite

給非工程的人看的說明：怎麼讀這套占星功能。每一節先一句白話，再一張小圖。
A plain-language tour of the astrology features — what each thing means and how to read it. No maths required.

> 開啟方式 / How to open: 在首頁選 **西洋占星 Western Astrology**，填生辰按 **Cast + Read**。
> Pick *Western Astrology*, enter a birth moment, press **Cast + Read**.

---

## 1. 你要輸入什麼 / What you enter — 生辰 the birth moment

| 欄位 Field | 說明 | 一定要嗎？ |
|---|---|---|
| 出生日期 date | 哪一天出生 | ✅ 必填 |
| 出生時刻 time | 幾點幾分（決定上升與宮位、月亮）| 強烈建議（沒有就只看星座，沒有宮位）|
| 出生地 place + 緯經度 lat/lon | 在地球哪裡（決定上升與宮位）| 上升/宮位需要 |

> 沒有時刻或地點時，系統會**誠實退回「只看星座」**並標註「上升未知」，不會亂編。
> Without a time/place it gracefully shows a planets-only chart and says so.

---

## 2. 怎麼讀星盤 / Reading the wheel 🜨

星盤是一個圓，分成你會看到三層：
The wheel has three layers, from outside in:

```
        ♋ ♌ ♍            ← 外圈：12 星座 the 12 signs (each 30°)
      ╱─────────╲
   ♊ │  ·10· ·11·│ ♎       ← 細輻線 + 數字：12 宮 the 12 houses
     │ ☉   ☽    │          ← 裡面的符號：你的行星 your planets
   ♉ │ ·    ·   │ ♏        ← 中間連線：相位 aspects between planets
      ╲─────────╱
        ♓ ♒ ♑
```

- **星座 signs**（牡羊…雙魚）：行星落在哪個星座 → 那顆星的「風格」。
- **行星 planets**：☉日 ☽月 ☿水 ♀金 ♂火 ♃木 ♄土（℞＝逆行 retrograde，黃色）。
- **宮位 houses**：人生的 12 個領域（1=自我、7=關係、10=事業…）。**ASC（上升）** 與 **MC（天頂）** 用紫色粗線標。
- **相位線 aspects**：行星之間的角度關係。**線越粗越亮＝角度越準（容許度越小）＝影響越強**。綠＝和諧、紅＝張力、灰＝合相。

---

## 3. 宮位制 / House systems — 六種切法 six ways to slice the houses

宮位就是把圓分成 12 塊的方法。不同流派切法不同。在 **Houses 宮位制** 下拉選：
Houses divide the wheel into 12 sectors; schools differ on *how*. Pick under **Houses**:

| 選項 | 白話 |
|---|---|
| **whole-sign 整星座**（預設）| 一個星座＝一宮。最古老、最簡單。|
| **equal 等宮** | 從上升起，每 30° 一宮。|
| **placidus** | 西洋最流行的「不等宮」，按時間分。|
| **koch / regiomontanus / campanus** | 其他不等宮流派（不同的空間/時間分法）。|

> 這四種「不等宮」都跟專業軟體 Swiss Ephemeris **對到小數點後兩位以內**（<0.01°），可放心。
> The four quadrant systems match Swiss Ephemeris to <0.01°.

---

## 4. 解讀 / The reading 解讀 📜

按下後，**命盤先秒出**，下面的 AI 解讀**逐字打字**出現（雙語，先英文後中文）。
The chart appears instantly; the bilingual reading then types itself in.

解讀會用到命盤的真實結構：**命主星**（上升星座的主星）、**四正宮行星**（落在 1/4/7/10 宮的星）、**相位**——不是孤立地講單顆星。
It weaves in your chart ruler, angular planets, and aspects — not planets in isolation.

> 不接 AI 金鑰也能用：命盤照排，解讀顯示「事實摘要」。
> Works with no AI key (the chart still casts; the reading shows a facts digest).

---

## 5. 行運 / Transits 行運 — 「現在的天空」疊上你的命盤

**Overlay 疊加** 選 **transits 行運**：外圈多一圈**藍色的「現在行星」**，疊在你的本命盤上。拖 **時間滑桿** 可看任何一天（±5 年），即時更新。
Pick *transits*: a blue outer ring shows today's (or any day's) planets over your natal chart; drag the slider to any date.

```
   natal ☉ (inner, green)      ← 你的本命太陽
        ╲  applying ▸ (solid)  ← 入相：正在靠近、能量在「成形」
   transit ♄ (outer, blue)     ← 現在的土星
```

**重要行運 Major transits**：當慢星（木星/土星）走到你的**四角點**（上升/天頂…）3° 內，會用**金色光環**標出：
- **越亮越粗＝越關鍵**（合相 > 四分相；角度越準越亮）。
- **實線 ▸＝入相 applying（正在靠近、醞釀中）**；**虛線 ▹＝出相 separating（已過、在消退）**。
- 還會算出**精確觸發日 exact date**：那顆星正好壓上角點是哪一天。

**所有行運相位**（不只對角點）現在也都標**入相/出相＋精確日**（看下方「命盤要素」列表）。

---

## 6. 推運 / Progressions 推運 — 「你內在的成長時鐘」

行運是「外面的天空」；**推運是把你的命盤往前推，看內在演化**。**Overlay 選 progressions**，再選 **Method 推運法**：

- **secondary 二次推運**：規則是 **「一天＝一年」**。出生後第 30 天的天空 ＝ 你 30 歲的「內在盤」。推運太陽約 **1°/年** 緩慢移動。
- **solar arc 太陽弧**：把整張命盤（行星＋宮位）**整體旋轉**，旋轉量＝推運太陽走過的弧。

**重要推運 Major progressions**（自動標出）：
- 推運**月亮**在哪個星座、落哪一宮，以及**下次換星座的日期**（月亮是內在情緒的時鐘，約 2.5 年換一座）。
- 推運**太陽是否已換星座**（一生約換 1–3 次，是重大的人生基調轉變）。

**太陽弧 директ 到角點 Solar-arc directions**（太陽弧模式下）：列出**每顆星被推到上升/天頂…的年齡與年份**——這是太陽弧派看「大事發生在幾歲」的方法。

```
  SA ☉ → MC  at age 37.9 (2028)   ← 38 歲那年，太陽弧推到天頂：事業高峰時刻
```

> 外圈也會畫**推運盤自己的宮位刻度**（藍色），加一圈**細刻度尺**，方便讀外圈位置。

---

## 7. 合盤 / Synastry 合盤 — 兩個人的盤怎麼互動

切到 **Synastry 合盤**，填兩個人的生辰，按 **Compare**。你會得到**三張盤**，每張都有解讀：

1. **雙輪盤 bi-wheel**：A 在內、B 在外，中間虛線＝**跨盤相位**（綠＝契合、紅＝張力）。
2. **組合中點盤 composite**：把兩人每顆星取**中點**，合成「這段關係本身」的一張盤。
3. **Davison 時空中點盤**：用兩人**生時與生地的中點**，排一張**真實天象盤**（跟 composite 不同，這是某個真實時刻的天空）。Davison 還附**土星/木星回歸時間軸**＝這段關係的人生里程碑。

---

## 8. 團體合盤 / Group 團體 — 三人以上的默契地圖

切到 **Group 團體**，加 2–8 人，按 **Compare group**：

```
        Mei   Ken   Lin
  Mei    —    +4    +1     ← 綠＝契合 in-sync
  Ken   +4     —    -2     ← 紅＝張力 tension
  Lin   +1    -2     —
```

- 每格＝兩人的**吉凶相位淨分**；**點格子**展開那一對的相位。
- 上方可切換 **Net / Total / 吉 / 凶** 四種看法；可**依契合度排序**把最合的人群聚，或用 **▲▼** 手動調順序。
- 另附**團體共同中點盤**（全員行星的平均）＋團體解讀。

---

## 9. 分享 / Export 匯出

- **下載星盤 PNG**：把圓盤存成圖片。
- **列印・存 PDF**：把整份命盤＋解讀印出或存成 PDF（會自動隱藏輸入框）。

---

## 名詞速查 / Quick glossary

| 詞 | 白話 |
|---|---|
| 上升 ASC | 出生那一刻東方地平線上升的星座；「你給人的第一印象／人生起點」|
| 天頂 MC | 盤的最高點；「事業、名聲、人生方向」|
| 相位 aspect | 兩顆星之間的角度（0/60/90/120/180°），決定它們「合作或拉扯」|
| 容許度 orb | 相位離「正準」差幾度；越小越強 |
| 入相 applying | 角度正在靠近正準 → 能量在醞釀 |
| 出相 separating | 角度已過正準 → 能量在消退 |
| 行運 transit | 此刻天上的行星 vs 你的本命 |
| 推運 progression | 把命盤往前推，看內在成長（一天＝一年）|

> ⚠️ 僅供文化、教育與娛樂用途。命理不是財務、醫療或法律決策的依據。
> For cultural / educational / entertainment use only. Not a basis for real-world decisions.
