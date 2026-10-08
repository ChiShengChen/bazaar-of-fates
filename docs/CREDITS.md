# Credits · 引用與致謝

Bazaar of Fates is built on, cross-checked against, or informed by the open-source projects below.
Where code is imported it is an **optional** dependency (`pip install -e ".[oracles]"`), the service runs
without it, and the source is named in the chart payload (`enriched_by` / `source`). Where only rules were
consulted, no code was copied. Licences are those declared by each project at the time of writing (2026-10).

| Project | Licence | How we use it |
|---|---|---|
| [6tail/lunar-python](https://github.com/6tail/lunar-python) (and lunar-javascript / lunar-java) | MIT | **Imported (optional)** — the 黃曆 almanac block on the 八字 sheet (二十八宿, 建除, 彭祖百忌, 吉神凶煞, 宜忌, 喜財福神方位, 身宮, 胎息). **Test oracle** for our native 四柱, 節氣 instants, 胎元/命宮 and 大運 sequence. |
| [SylarLong/iztro](https://github.com/SylarLong/iztro) via [x-haose/x-iztro](https://pypi.org/project/x-iztro/) (Rust port, Python bindings) | MIT | **Imported (optional)** — star brightness 廟旺利陷, the 雜曜 (adjective stars), 格局 pattern hits and 流月 for 紫微. **Test oracle** for our native placement of the 14 主星 and 22 輔煞星, 十二長生, 博士十二神 and 大限 ranges. The engine core's 命宮/五行局/安星 algorithm was originally verified cell-by-cell against py-iztro. |
| [kentang2017/kinliuren](https://github.com/kentang2017/kinliuren) | MIT | **Test oracle** for 大六壬 四課, 三傳, 課體 and 十二天將 (our `liuren_ext` is a native implementation of the same classical rules). |
| [kentang2017/kinqimen](https://github.com/kentang2017/kinqimen) | MIT | **Test oracle** for 時家奇門 (拆補 / 置閏): 局數, 值符值使, 天盤 九星八門八神. |
| [pyswisseph](https://pypi.org/project/pyswisseph/) / Swiss Ephemeris | AGPL-3.0 (dual) | **Dev-only test oracle** (never a runtime dependency): planet longitudes at the birth instant (ours agree to < 20″ with Moshier) and the six house systems (< 0.006°). |
| [OpenCC](https://github.com/BYVoid/OpenCC) (opencc-python-reimplemented) | Apache-2.0 | **Imported (optional)** — 簡體 → 正體 conversion of the lunar-python almanac text. |
| [ephem (PyEphem)](https://rhodesmill.org/pyephem/) | MIT | **Runtime** — all planetary positions, solar terms, transits and ascendant geometry. |
| [lunardate](https://pypi.org/project/lunardate/) | GPL-3.0 (library) | **Runtime** — 公曆↔農曆 conversion (1900–2100). |
| [ChesterRa/mingpan](https://github.com/ChesterRa/mingpan) | Apache-2.0 | **Rules consulted** for the 六爻 納甲 layer (六親, 六神, 伏神) and the 奇門 轉盤 conventions. No code copied. |
| [chxb/jishiyu](https://github.com/chxb/jishiyu) | AGPL-3.0 | **Rules consulted** (小六壬 起課, 六爻 旺衰 labels, 奇門 置閏 conventions). No code copied — AGPL code is not included in this repository. |
| [Renhuai123/ziwei-doushu](https://github.com/Renhuai123/ziwei-doushu) | MIT | **Reference** for 紫微 school conventions (閏月, 晚子時, brightness schools). |
| 中央氣象署 / 台北市政府 曆象表, USNO | public data | Reference instants for 節氣 and equinox/solstice regression tests; Taiwan 日光節約時間 table. |

lunar-python returns 簡體 text for the almanac fields; it is converted to 台灣正體 with [OpenCC](https://github.com/BYVoid/OpenCC) (opencc-python-reimplemented, Apache-2.0).

All engine code lives in this repo.

## Classical texts cited in the rule comments 典籍

《淵海子平》《三命通會》《窮通寶鑑》（八字）· 《紫微斗數全書》（紫微）· 《梅花易數》（梅花）·
《增刪卜易》《卜筮正宗》（六爻）· 《六壬大全》《壬歸》（大六壬）· 《神奇之門》《奇門遁甲統宗》（奇門）·
袁天罡《稱骨歌》.
