# Jyotiṣa（吠陀占星）圖解 · Jyotiṣa Visual Guide

印度占星：用**恆星黃道**（熱帶經度減去 Lahiri 歲差）排盤，看月亮的**星宿**與一生的 **Vimśottarī 大運**。
Vedic astrology: charts use the **sidereal** zodiac (tropical − Lahiri ayanāṃśa); the spine is the Moon's **nakṣatra** and the lifelong **Vimśottarī Mahādaśā**.

> 開啟 / Open: 首頁選 **Jyotiṣa · 吠陀占星**。**Lagna（上升）需要時辰＋出生地**。

![jyotish rāśi 盤](img/jyotish-chart.png)

## 命盤怎麼讀 / Reading the chart

南印度式 **rāśi 盤**（方格），9 個 graha（含 Rahu/Ketu）落在 12 個 rāśi（星座）：

```
 月宿 Shatabhisha · 月 rāśi Kumbha · Lagna Tula · 大運 Saturn (malefic)
```

- **graha**：太陽、月、火、水、木、金、土＋ **Rahu/Ketu**（月交點，吉凶要角）。
- **rāśi**：恆星黃道的十二星座（與西洋約差一個星座）。
- **Lagna（上升）**：恆星上升點＝命宮起點（需時辰＋地點）。
- **Mahādaśā 大運**：以出生月宿定起，120 年九曜輪值；當下走哪一顆星的大運，定人生階段吉凶。

## 命盤要素 / Key facts

| 欄位 | 意思 |
|---|---|
| moon_nakshatra 月宿 | 月亮所在的 27 星宿之一（定大運起點）|
| moon_rashi | 月亮所在 rāśi |
| lagna_rashi | 恆星上升星座（需時辰＋地點）|
| mahadasha_lord 大運主星 | 當下當值的大運星 |
| dasha_nature | benefic（吉）/ malefic（凶）|

> 時間軸 Timeline：Jyotiṣa 附 **Vimśottarī Mahādaśā**（120 年九曜大運），每段標起訖年與吉凶。

## 名詞速查 / Glossary

| 詞 | 白話 |
|---|---|
| 恆星黃道 sidereal | 以恆星為準的黃道（扣掉歲差）|
| nakṣatra 星宿 | 27 個月站，定大運 |
| Lagna 上升 | 出生東方地平的恆星星座 |
| Vimśottarī Daśā | 120 年九曜輪值的人生分段 |

> 恆星經度＝熱帶（`ephem`）− Lahiri 歲差；大運由月宿起算的 Vimśottarī 系統。

## 排盤精度 / How positions are computed

- 九曜取**出生精確時刻**的當日黃道位置，再減 Lahiri 歲差（J2000 ≈ 23.853°，每年 +50.27″）。
- **月宿 nakṣatra**（寬 13°20′）與月亮一天的行程相當，所以用時刻而非日期算；Vimśottarī daśā 的起始主星與餘量都由此而來。
- 羅睺／計都用平均交點；Lagna ＝ 回歸上升 − 歲差。
