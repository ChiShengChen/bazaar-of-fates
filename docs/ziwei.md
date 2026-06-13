# 紫微斗數圖解 · Zi Wei Dou Shu Visual Guide

把生辰換成農曆，排出一張 **12 宮命盤**，把紫微等星曜安進各宮，看人生十二個領域。
From your birth (converted to the lunar calendar) it casts a **12-palace chart** and places the stars (紫微 etc.) into the palaces — the twelve areas of life.

> 開啟 / Open: 首頁選 **Zi Wei Dou Shu · 紫微斗數**。**命宮由時辰決定**，務必填出生時刻。

## 命盤怎麼讀 / Reading the board

12 宮排在 **4×4 方盤**的外圈、按地支固定方位；中央放命主資訊：

```
 巳   午   未   申
 辰  ┌─────────┐ 酉      ← 中央：命主星/身主星/五行局/命宮/生時
 卯  │  命主資訊 │ 戌
 寅   丑   子   亥        ← 每格一宮：宮名（命宮/財帛/官祿…）+ 該宮星曜
```

- **命宮**：最重要的宮，定一生基調（由生月＋生時起）。
- 每宮裡的**星曜**（紫微、天機、太陽…）描述那個領域的特質；帶 **(祿/權/科/忌)** 的是**四化**。

## 命盤要素 / Key facts

| 欄位 | 意思 |
|---|---|
| soul_star 命主星 | 一生的主星之一 |
| body_star 身主星 | 後天、身的主星 |
| five_elements_class 五行局 | 水二局…火六局，定起運與紫微落點 |
| life_palace_branch 命宮 | 命宮所在地支 |
| 流年四化 (timeline) | 每年的祿/權/科/忌飛入哪些星 |

> 時間軸 Timeline：紫微附 **流年四化**——未來每年「化祿/化權/化科/化忌」落在哪顆星，看那年得失重點。

## 名詞速查 / Glossary

| 詞 | 白話 |
|---|---|
| 命宮 | 十二宮之首，定一生主軸 |
| 四化 祿權科忌 | 星曜的四種變化：祿=利、權=勢、科=名、忌=阻 |
| 五行局 | 命局的元素級數，影響紫微星安放 |
| 飛星 | 四化「飛」入某宮，啟動該領域 |

> 純 Python 重寫，cell-by-cell 對過 py-iztro oracle；命宮目前以生時排（流年四化以立春為界）。
