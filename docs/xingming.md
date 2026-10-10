# 姓名學圖解 · Name Numerology (熊崎式五格剖象法)

以中文姓名的**筆畫**排出天、人、地、外、總五格，看五格的 81 數理吉凶、三才（天人地）五行生剋，再把每一格的五行對到同一個人**八字的喜用**。
From the stroke counts of a Chinese name: the five grids (天格 人格 地格 外格 總格), their 81-number fortunes, the 三才 element relations, and each grid's element against the person's 八字 favourable elements.

> 開啟 / Open: 首頁 System 選 **姓名學 · Xing Ming**，在 Name 欄填中文全名（複姓或冠夫姓以空白分隔：歐陽 娜娜）。API `POST /name`、CLI `bazaar xingming 1990-06-15 14:30 --full-name 陳美玲`、MCP `name`。沒有生辰也能排（只論姓名）。

引擎來自課程版（bazaar-of-fates-course）的 `fortune/xingming`，原封移植。

## 怎麼算 / How it is cast

1. **筆畫**：康熙筆畫＝部首「原形」的筆畫＋部首以外的筆畫（氵算水 4、扌算手 4、艹算艸 6、左阝算阜 8、右阝算邑 7…）。資料來自 Unicode 官方 **Unihan** 的 `kRSUnicode`（部首號．其餘筆畫）與 `kTotalStrokes`（台灣筆畫），約 2.8 萬字，`python -m fortune.tools.build_strokes` 產生 `fortune/xingming/strokes.tsv`；每個字的排盤步驟都寫出部首與 Unihan 編號。簡化字以正體計並提醒。
2. **分姓名**：有空白照空白切；三、四字開頭是常見複姓當複姓；否則第一字是姓。
3. **五格**：天格＝姓（單姓＋假數 1）；人格＝姓末字＋名首字；地格＝名（單名＋假數 1）；外格＝天＋地－人；總格＝全部筆畫（不含假數）。
4. **五行**：尾數 1、2 木，3、4 火，5、6 土，7、8 金，9、0 水；奇數陽、偶數陰。
5. **81 數理**：超過 81 減 80 循環；吉／半吉／凶採熊崎式通行分類（各家在半吉數上有出入，表在 `engine.py` 頂端可改）。
6. **三才**：天格、人格、地格的五行；成功運（天對人）、基礎運（人對地）、社交運（人對外）各看相生／比和／相剋。
7. **配八字**：有生辰時，用八字排盤同一套旺衰規則取喜用／忌，每格五行標「喜用／忌／閒」；論命以**人格**為主。姓名不隨年份變，所以沒有流年。

## 流派開關 / Switches

| 參數 | 選項 | 說明 |
|---|---|---|
| `stroke_basis` | kangxi（預設）／ modern | 康熙筆畫或現代（台灣）筆畫 |
| `numeral_strokes` | value（預設）／ shape | 一～十照數值（四算 4、九算 9）或照字形 |
| `jiashu` | on（預設）／ off | 單姓天格、單名地格加不加假數 1 |

## 命盤要素 / Key facts

| 欄位 | 意思 |
|---|---|
| 筆畫 | 每字筆畫與算法 |
| 天格／人格／地格／外格／總格 | 數・五行・數理（吉／半吉／凶） |
| 三才 | 天人地五行；成功運／基礎運／社交運 |
| 八字喜用／人格對八字 | 喜用五行、每格對喜用的關係 |

> 姓名學是輔助性的參考，各派筆畫與數理分類不一；本盤把每一步算法列出，方便對照自己的師承。
