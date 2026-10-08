"""Birthplace lookup / 出生地查詢 — offline city table → (lat, lon, tz), plus historical DST.

No network: a small table of the cities people actually type, with aliases in 中文 / English /
日本語. Taiwan's 日光節約時間 (1946–1961, 1974–75, 1979 — the 中央氣象署 table) is applied
when the birth falls inside one of those windows, because an hour shifts the 時柱 and the
ascendant. Other countries' historical DST is NOT modelled; the UI shows the offset so the
user can correct it.
"""

from __future__ import annotations

from datetime import date

# name → (lat, lon, standard UTC offset). First alias is the display name.
_CITIES: list[tuple[tuple[str, ...], float, float, float]] = [
    (("Taipei", "台北", "臺北", "台北市", "新北", "新北市", "Taipei City", "New Taipei"), 25.04, 121.56, 8),
    (("Taoyuan", "桃園", "桃園市"), 24.99, 121.30, 8),
    (("Hsinchu", "新竹", "新竹市", "新竹縣"), 24.80, 120.97, 8),
    (("Taichung", "台中", "臺中", "台中市"), 24.15, 120.67, 8),
    (("Changhua", "彰化"), 24.08, 120.54, 8),
    (("Chiayi", "嘉義"), 23.48, 120.45, 8),
    (("Tainan", "台南", "臺南", "台南市"), 22.99, 120.21, 8),
    (("Kaohsiung", "高雄", "高雄市"), 22.63, 120.30, 8),
    (("Pingtung", "屏東"), 22.67, 120.49, 8),
    (("Yilan", "宜蘭"), 24.76, 121.75, 8),
    (("Hualien", "花蓮"), 23.99, 121.60, 8),
    (("Taitung", "台東", "臺東"), 22.76, 121.14, 8),
    (("Keelung", "基隆"), 25.13, 121.74, 8),
    (("Hong Kong", "香港", "HK"), 22.30, 114.17, 8),
    (("Macau", "澳門"), 22.20, 113.54, 8),
    (("Beijing", "北京"), 39.90, 116.40, 8),
    (("Shanghai", "上海"), 31.23, 121.47, 8),
    (("Guangzhou", "廣州", "广州"), 23.13, 113.26, 8),
    (("Shenzhen", "深圳"), 22.54, 114.06, 8),
    (("Chengdu", "成都"), 30.57, 104.07, 8),
    (("Chongqing", "重慶", "重庆"), 29.56, 106.55, 8),
    (("Wuhan", "武漢", "武汉"), 30.59, 114.31, 8),
    (("Xi'an", "Xian", "西安"), 34.34, 108.94, 8),
    (("Hangzhou", "杭州"), 30.27, 120.15, 8),
    (("Nanjing", "南京"), 32.06, 118.80, 8),
    (("Xiamen", "廈門", "厦门"), 24.48, 118.09, 8),
    (("Fuzhou", "福州"), 26.07, 119.30, 8),
    (("Harbin", "哈爾濱", "哈尔滨"), 45.80, 126.53, 8),
    (("Urumqi", "烏魯木齊", "乌鲁木齐"), 43.83, 87.62, 8),
    (("Lhasa", "拉薩", "拉萨"), 29.65, 91.11, 8),
    (("Singapore", "新加坡"), 1.35, 103.82, 8),
    (("Kuala Lumpur", "吉隆坡"), 3.14, 101.69, 8),
    (("Manila", "馬尼拉", "马尼拉"), 14.60, 120.98, 8),
    (("Tokyo", "東京", "东京"), 35.68, 139.69, 9),
    (("Osaka", "大阪"), 34.69, 135.50, 9),
    (("Kyoto", "京都"), 35.01, 135.77, 9),
    (("Nagoya", "名古屋"), 35.18, 136.91, 9),
    (("Sapporo", "札幌"), 43.06, 141.35, 9),
    (("Fukuoka", "福岡", "福冈"), 33.59, 130.40, 9),
    (("Seoul", "首爾", "首尔", "서울"), 37.57, 126.98, 9),
    (("Busan", "釜山", "부산"), 35.18, 129.08, 9),
    (("Bangkok", "曼谷"), 13.76, 100.50, 7),
    (("Hanoi", "河內", "河内"), 21.03, 105.85, 7),
    (("Ho Chi Minh City", "Saigon", "胡志明市", "西貢"), 10.82, 106.63, 7),
    (("Jakarta", "雅加達", "雅加达"), -6.21, 106.85, 7),
    (("Yangon", "仰光"), 16.87, 96.20, 6.5),
    (("Kolkata", "Calcutta", "加爾各答"), 22.57, 88.36, 5.5),
    (("Mumbai", "Bombay", "孟買"), 19.08, 72.88, 5.5),
    (("New Delhi", "Delhi", "新德里"), 28.61, 77.21, 5.5),
    (("Bangalore", "Bengaluru", "班加羅爾"), 12.97, 77.59, 5.5),
    (("Chennai", "Madras", "清奈"), 13.08, 80.27, 5.5),
    (("Dubai", "杜拜", "迪拜"), 25.20, 55.27, 4),
    (("Moscow", "莫斯科"), 55.76, 37.62, 3),
    (("Istanbul", "伊斯坦堡"), 41.01, 28.98, 3),
    (("Athens", "雅典"), 37.98, 23.73, 2),
    (("Cairo", "開羅"), 30.04, 31.24, 2),
    (("Berlin", "柏林"), 52.52, 13.41, 1),
    (("Munich", "München", "慕尼黑"), 48.14, 11.58, 1),
    (("Vienna", "Wien", "維也納"), 48.21, 16.37, 1),
    (("Zurich", "Zürich", "蘇黎世"), 47.38, 8.54, 1),
    (("Paris", "巴黎"), 48.86, 2.35, 1),
    (("Amsterdam", "阿姆斯特丹"), 52.37, 4.90, 1),
    (("Brussels", "布魯塞爾"), 50.85, 4.35, 1),
    (("Rome", "Roma", "羅馬"), 41.90, 12.50, 1),
    (("Milan", "Milano", "米蘭"), 45.46, 9.19, 1),
    (("Madrid", "馬德里"), 40.42, -3.70, 1),
    (("Barcelona", "巴塞隆納"), 41.39, 2.17, 1),
    (("Stockholm", "斯德哥爾摩"), 59.33, 18.07, 1),
    (("Copenhagen", "哥本哈根"), 55.68, 12.57, 1),
    (("Warsaw", "華沙"), 52.23, 21.01, 1),
    (("London", "倫敦", "伦敦"), 51.51, -0.13, 0),
    (("Manchester", "曼徹斯特"), 53.48, -2.24, 0),
    (("Edinburgh", "愛丁堡"), 55.95, -3.19, 0),
    (("Dublin", "都柏林"), 53.35, -6.26, 0),
    (("Lisbon", "里斯本"), 38.72, -9.14, 0),
    (("São Paulo", "Sao Paulo", "聖保羅"), -23.55, -46.63, -3),
    (("Buenos Aires", "布宜諾斯艾利斯"), -34.60, -58.38, -3),
    (("Rio de Janeiro", "里約"), -22.91, -43.17, -3),
    (("New York", "NYC", "紐約", "纽约"), 40.71, -74.01, -5),
    (("Boston", "波士頓"), 42.36, -71.06, -5),
    (("Washington", "Washington DC", "華盛頓"), 38.91, -77.04, -5),
    (("Toronto", "多倫多"), 43.65, -79.38, -5),
    (("Montreal", "蒙特婁"), 45.50, -73.57, -5),
    (("Miami", "邁阿密"), 25.76, -80.19, -5),
    (("Chicago", "芝加哥"), 41.88, -87.63, -6),
    (("Houston", "休士頓"), 29.76, -95.37, -6),
    (("Dallas", "達拉斯"), 32.78, -96.80, -6),
    (("Mexico City", "墨西哥城"), 19.43, -99.13, -6),
    (("Denver", "丹佛"), 39.74, -104.99, -7),
    (("Phoenix", "鳳凰城"), 33.45, -112.07, -7),
    (("Los Angeles", "LA", "洛杉磯", "洛杉矶"), 34.05, -118.24, -8),
    (("San Francisco", "SF", "舊金山", "三藩市"), 37.77, -122.42, -8),
    (("San Jose", "聖荷西"), 37.34, -121.89, -8),
    (("Seattle", "西雅圖"), 47.61, -122.33, -8),
    (("Vancouver", "溫哥華"), 49.28, -123.12, -8),
    (("Honolulu", "檀香山"), 21.31, -157.86, -10),
    (("Sydney", "雪梨", "悉尼"), -33.87, 151.21, 10),
    (("Melbourne", "墨爾本"), -37.81, 144.96, 10),
    (("Brisbane", "布里斯本"), -27.47, 153.03, 10),
    (("Perth", "伯斯"), -31.95, 115.86, 8),
    (("Auckland", "奧克蘭"), -36.85, 174.76, 12),
]
_INDEX: dict[str, int] = {}
for i, (names, _la, _lo, _tz) in enumerate(_CITIES):
    for n in names:
        _INDEX[n.lower()] = i

# 台灣日光節約時間 (中央氣象署): (year, (m, d) start, (m, d) end), clocks +1h
TAIWAN_DST = {
    1946: ((5, 15), (9, 30)), 1947: ((4, 15), (10, 31)), 1948: ((5, 1), (9, 30)), 1949: ((5, 1), (9, 30)),
    1950: ((5, 1), (9, 30)), 1951: ((5, 1), (9, 30)), 1952: ((3, 1), (10, 31)), 1953: ((4, 1), (10, 31)),
    1954: ((4, 1), (10, 31)), 1955: ((4, 1), (9, 30)), 1956: ((4, 1), (9, 30)), 1957: ((4, 1), (9, 30)),
    1958: ((4, 1), (9, 30)), 1959: ((4, 1), (9, 30)), 1960: ((6, 1), (9, 30)), 1961: ((6, 1), (9, 30)),
    1974: ((4, 1), (9, 30)), 1975: ((4, 1), (9, 30)), 1979: ((7, 1), (9, 30)),
}
_TAIWAN_IDX = {i for i, (names, _la, _lo, _tz) in enumerate(_CITIES[:13])}


def taiwan_dst(d: date) -> bool:
    w = TAIWAN_DST.get(d.year)
    return bool(w) and (w[0] <= (d.month, d.day) <= w[1])


def lookup(place: str | None, on: date | None = None) -> dict | None:
    """{name, latitude, longitude, tz_offset_hours, dst} for a known city, else None.
    Matching is case-insensitive on the whole string, then on any alias contained in it."""
    if not place:
        return None
    import re
    q = place.strip().lower()
    i = _INDEX.get(q)
    if i is None:
        def _hit(n: str) -> bool:                       # CJK aliases: substring; ASCII: whole word, ≥3 chars
            if n.isascii():
                return len(n) >= 3 and re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", q) is not None
            return len(n) >= 2 and n in q
        hits = {j: max(len(n) for n in _CITIES[j][0] if _hit(n.lower())) for n, j in _INDEX.items() if _hit(n)}
        i = max(hits, key=hits.get) if hits else None
    if i is None:
        return None
    names, lat, lon, tz = _CITIES[i]
    dst = bool(on) and i in _TAIWAN_IDX and taiwan_dst(on)
    return {"name": names[0], "latitude": lat, "longitude": lon,
            "tz_offset_hours": tz + (1 if dst else 0), "dst": dst,
            "note": f"台灣日光節約時間 {on.year}（{TAIWAN_DST[on.year][0][0]}/{TAIWAN_DST[on.year][0][1]}–{TAIWAN_DST[on.year][1][0]}/{TAIWAN_DST[on.year][1][1]}）時鐘撥快 1 小時 → UTC+9" if dst else ""}


def cities() -> list[dict]:
    return [{"name": n[0], "aliases": list(n[1:]), "latitude": la, "longitude": lo, "tz": tz} for n, la, lo, tz in _CITIES]
