"""太乙神數 年計 / the annual Tai Yi board — native.

Follows the 太乙統宗 convention: 積年 = 10153917 + 農曆年 (金鏡式經 1936557 and 淘金歌 10154193 selectable), 七十二局 陽遁 for the
年計, 太乙 three years per 宮 through 乾一 離二 艮三 震四 兌六 坤七 坎八 巽九 (never 中五), 天目 (文昌) through the 十六神, 始擊, 計神
(寅逆行 by 太歲), 合神 (丑逆行), 定目, then 主算 / 客算 / 定算 counted from 文昌 / 始擊 / 定目 to the 太乙 宮 (間辰 +1), 大將 = 算 mod 10,
參將 = 大將 × 3 mod 10, the 四神 / 天乙 / 地乙 / 直符 / 君基 / 臣基 / 民基 / 五福 / 帝符 / 太尊 / 飛鳥 / 三風 / 五風 / 八風 / 大游 / 小游 /
陽九 / 百六 cycles, 八門值事與分佈, and the classical judgements (三門具不具, 五將發不發, 主客相關, 多少占勝負, 太乙助主／客).
Cross-checked against kintaiyi (a reference implementation of the same 統宗 tables) in tests.
"""

from __future__ import annotations

from datetime import date

from fortune import bazi_ext as X

B = X.BRANCHES
ACC_BASE = {"tongzong": 10153917, "jinjing": 1936557, "taojinge": 10154193}
ACC_NAME = {"tongzong": "太乙統宗", "jinjing": "太乙金鏡式經", "taojinge": "太乙淘金歌"}
GONG16 = "子丑艮寅卯辰巽巳午未坤申酉戌乾亥"
GONG16_NUM = dict(zip("亥子丑艮寅卯辰巽巳午未坤申酉戌乾", [8, 8, 3, 3, 4, 4, 9, 9, 2, 2, 7, 7, 6, 6, 1, 1]))   # 太乙宮數 of each 十六神 cell
NUM2GONG = {1: "乾", 2: "離", 3: "艮", 4: "震", 5: "中", 6: "兌", 7: "坤", 8: "坎", 9: "巽"}
NUM2CELL = {1: "乾", 2: "午", 3: "艮", 4: "卯", 5: "中", 6: "酉", 7: "坤", 8: "子", 9: "巽"}
RING = [8, 3, 4, 9, 2, 7, 6, 1]                                     # 太乙 八宮 順行 (坎 艮 震 巽 離 坤 兌 乾)
JIANCHEN = set("丑寅辰巳未申戌亥")                                     # 間辰
SIWEI = set("巽艮坤乾")                                                # 四維
DOORS = "開休生傷杜景死驚"
SIXTEEN_GOD = {"子": "地主", "丑": "陽德", "艮": "和德", "寅": "呂申", "卯": "高叢", "辰": "太陽", "巽": "大炅", "巳": "大神", "午": "大威", "未": "天道",
               "坤": "大武", "申": "武德", "酉": "太簇", "戌": "陰主", "乾": "陰德", "亥": "大義"}
ELEM16 = {"子": "水", "丑": "土", "艮": "土", "寅": "木", "卯": "木", "辰": "土", "巽": "木", "巳": "火", "午": "火", "未": "土", "坤": "土", "申": "金",
          "酉": "金", "戌": "土", "乾": "金", "亥": "水"}
# 七十二局 tables (局 1…72), 陽遁
TAIYI_PAI = "乾乾乾離離離艮艮艮震震震兌兌兌坤坤坤坎坎坎巽巽巽" * 3
SKYEYES = "申酉戌乾乾亥子丑艮寅卯辰巽巳午未坤坤" * 4
SF_LIST = "坤戌亥丑寅辰巳坤酉乾丑寅辰午坤酉亥子艮辰巳未申戌亥艮卯巽未丑戌子艮卯巳午" * 2
FOUR_GOD = "乾乾乾離離離艮艮艮震震震中中中兌兌兌坤坤坤坎坎坎巽巽巽巳巳巳申申申寅寅寅"
SKY_YI = "兌兌兌坤坤坤坎坎坎巽巽巽巳巳巳申申申寅寅寅乾乾乾離離離艮艮艮震震震中中中"
EARTH_YI = "巽巽巽巳巳巳申申申寅寅寅乾乾乾離離離艮艮艮震震震中中中兌兌兌坤坤坤坎坎坎"
ZHI_FU = "中中中兌兌兌坤坤坤坎坎坎巽巽巽巳巳巳申申申寅寅寅乾乾乾離離離艮艮艮震震震"
OFFICER_BASE = "巳巳午午午未未未申申申酉酉酉戌戌戌亥亥亥子子子丑丑丑寅寅寅卯卯卯辰辰辰巳"
SKY_SUMMARY = ['', '始擊擊', '', '內迫', '', '', '辰迫', '', '囚', '', '囚', '', '', '', '', '', '囚', '囚', '客挾', '', '', '', '', '', '', '', '囚', '囚', '始擊擊', '', '',
               '始擊擊', '始擊掩', '始擊掩', '', '', '', '囚', '辰迫', '', '客挾', '客挾', '囚', '客挾', '宮迫', '', '主挾，宮迫', '辰迫', '', '', '', '主挾，辰迫', '宮迫',
               '宮迫', '始擊掩', '', '', '', '客挾', '', '', '', '', '', '主挾', '辰擊', '', '始擊掩', '始擊擊', '始擊擊', '囚', '始擊擊']
NUM_DESC = {1: '雜陰', 2: '純陰', 3: '純陽', 4: '雜陽', 6: '純陰', 7: '雜陰', 8: '雜陽', 9: '純陽', 11: '陰中重陽', 12: '下和', 13: '雜重陽', 14: '上和', 16: '下和',
            17: '陰中重陽', 18: '上和', 19: '雜重陽', 22: '純陰', 23: '次和', 24: '雜重陰', 26: '純陰', 27: '下和', 28: '雜重陰', 29: '次和', 31: '雜重陽', 32: '次和',
            33: '純陽', 34: '下和', 37: '雜重陽', 38: '下和', 39: '純陽'}
_KE = {"金": "木", "木": "土", "土": "水", "水": "火", "火": "金"}
_SHENG = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}


def _rot(seq, start):
    seq = list(seq)
    i = seq.index(start)
    return seq[i:] + seq[:i]


def _relation(me: str, other: str) -> str:
    if me == other:
        return "比和"
    if _KE[me] == other:
        return "我尅"
    if _KE[other] == me:
        return "尅我"
    if _SHENG[me] == other:
        return "我生"
    return "生我"


def jinian(lunar_year: int, method: str = "tongzong") -> int:
    """太乙積年 for the 年計 (上元甲子 to this 農曆年)."""
    base = ACC_BASE[method]
    return base + lunar_year if lunar_year >= 0 else base + lunar_year + 1


def _count(target: str, taiyi_num: int, *, set_mode: bool = False) -> int:
    """算: from the target 神's 宮 along the 八宮 ring to the 宮 before 太乙, summing 宮數; a 間辰 adds one."""
    tnum = GONG16_NUM[target]
    order = _rot(RING, tnum)
    base = sum(order[: order.index(taiyi_num)])
    if target in JIANCHEN:
        return base + 1
    if target in SIWEI:
        return 1 if (set_mode and base == 0 and taiyi_num in (1, 3, 7, 9)) else base
    if set_mode:
        return base                                             # 定算: 正位同宮不以太乙宮數計
    return taiyi_num if taiyi_num == tnum else base


def _general(cal: int, *, home_taiyi: int | None = None, first_is_taiyi: bool = True) -> int:
    if cal == 1 and first_is_taiyi:
        return home_taiyi if home_taiyi else 1
    r = cal % 10
    return 5 if r == 0 else r


def _cal_desc(n: int) -> list[str]:
    out = []
    if n > 10 and n % 10 > 5:
        out.append("三才足數")
    if n < 10:
        out.append("無天：二曜虛蝕、五緯失度、慧孛飛流、霜雹為害")
    if n % 10 < 5:
        out.append("無地：崩地震、川竭蝗蝻之象")
    if n % 10 == 0:
        out.append("無人：口舌妖言更相殘賊、疾疫遷移流亡")
    if n in NUM_DESC:
        out.append(NUM_DESC[n])
    return out


def year_board(d: date, *, method: str = "tongzong", year_nayin_elem: str | None = None) -> dict:
    """The 年計 board for the 農曆 year containing `d`."""
    lunar = X.lunar_info(d, 0)
    ly = lunar["year"]
    acc = jinian(ly, method)
    k = acc % 72 or 72
    taisui = B[(ly - 4) % 12]
    ti = B.index(taisui)
    jigod = B[(2 - ti) % 12]                                   # 計神：寅宮逆行十二辰
    hegod = B[(1 - ti) % 12]                                   # 合神：丑宮逆行
    ty_cell = TAIYI_PAI[k - 1]
    ty_num = {"乾": 1, "離": 2, "艮": 3, "震": 4, "兌": 6, "坤": 7, "坎": 8, "巽": 9}[ty_cell]
    wenchang = SKYEYES[k - 1]
    shiji = SF_LIST[k - 1]
    start = _rot(GONG16, hegod)
    steps = start.index(taisui) + 1
    dingmu = _rot(GONG16, wenchang)[steps - 1]
    home_cal = _count(wenchang, ty_num)
    away_cal = _count(shiji, ty_num)
    set_cal = _count(dingmu, ty_num, set_mode=True)
    home_gen = _general(home_cal, home_taiyi=ty_num)
    away_gen = _general(away_cal)
    set_gen = 5 if set_cal % 10 == 0 else set_cal % 10
    vg = lambda g: (g * 3 % 10) or 5  # noqa: E731
    i36 = (k - 1) % 36
    kingbase = _rot(B, "午")[int(((acc + 250) % 360) / 30) % 12]
    wufu_n = int(((acc + 250) % 225) / 45)
    wufu = {1: "乾", 2: "艮", 3: "巽", 4: "坤", 5: "中"}.get(wufu_n, "中")
    n = acc % 20
    n = n - 16 if n > 16 else n
    kingfu = _rot(GONG16, "戌")[n - 1] if 1 <= n <= 16 else "中"
    taijun = {1: "子", 2: "午", 3: "卯", 4: "酉"}.get(acc % 4, "中")
    def _cyc(mod, table, adjust=None):
        v = acc % mod
        if adjust:
            v = adjust(v)
        return table[v - 1] if 1 <= v <= len(table) else 5
    flybird = _cyc(9, [1, 8, 3, 4, 9, 2, 7, 6])
    threewind = _cyc(9, [7, 2, 6, 1, 5, 9, 4, 8])
    fivewind = _cyc(29, [1, 3, 5, 7, 9, 2, 4, 6, 8], lambda v: v - 9 if v > 10 else v)
    eightwind = _cyc(9, [2, 3, 5, 6, 7, 8, 9, 1])
    by = (acc + 34) % 388
    by = by // 36 if by > 36 else by
    bigyo = {7: 1, 8: 2, 9: 3, 1: 4, 2: 5, 3: 6, 4: 7, 6: 8}.get(int(by), 5)
    sy = acc % 360
    sy = sy % 3 if sy < 24 else (sy % 24)
    sy = sy % 3 if sy > 3 else sy
    smallyo = {1: 1, 2: 2, 3: 3, 4: 4, 6: 5, 7: 6, 8: 7, 9: 8}.get(sy, 5)
    yj = (ly + 12607) % 4560 % 456 % 12 or 12
    yangjiu = _rot(B, "寅")[yj - 1]
    bl = (ly + 12607) % 4320 % 288 % 24
    baliu = _rot(B, "卯")[((bl - 12) % 12 or 12) - 1] if bl > 12 else _rot(B, "酉")[(bl or 12) - 1]
    a240 = acc % 240 or 120
    door_idx = a240 // 30 + 1
    door_on_duty = DOORS[door_idx - 1]
    doors = dict(zip(_rot(RING, ty_num), _rot(DOORS, door_on_duty)))
    three_doors = "三門不具" if doors[ty_num] in "休生開" else "三門具"
    summary = SKY_SUMMARY[k - 1]
    if home_gen == 5:
        five_gen = "主將主參不出中門，杜塞無門"
    elif away_gen == 5:
        five_gen = "客將客參不出中門，杜塞無門"
    elif summary == "":
        five_gen = "五將發"
    else:
        five_gen = f"{summary}，五將不發"
    wc_e, sj_e = ELEM16[wenchang], ELEM16[shiji]
    guan = "主關" if year_nayin_elem == wc_e else "客關" if year_nayin_elem == sj_e else "關"
    rel = _relation(wc_e, sj_e)
    if rel == "我尅":
        host_guest = "主將囚，不利主" if ty_num == home_gen else "主尅客，主勝"
    elif rel == "尅我":
        host_guest = f"{guan}得主人，客勝"
    else:
        host_guest = f"{guan}{rel}，和"
    if away_cal < home_cal:
        count_verdict = "客以少算臨多，主人勝" if home_gen != 5 else "雖客以少算臨多，惟主人不出中門，主客俱不利，和"
    elif away_cal > home_cal:
        count_verdict = "客以多算臨少，主人敗" if away_gen != 5 else "雖客以多算臨少，惟客人不出中門，主客俱不利，和"
    else:
        count_verdict = "主客旗鼓相當"
    verdict = "主勝" if "主人勝" in count_verdict or "主勝" in host_guest and "主人敗" not in count_verdict else "客勝" if "主人敗" in count_verdict or "客勝" in host_guest else "和"
    assist = "助主" if ty_num in (1, 8, 3, 4) else "助客"
    cells = {g: [] for g in GONG16}
    cells["中"] = []
    def put(cell, name):
        cells.setdefault(cell, []).append(name)
    for cell, name in ((wenchang, "文昌"), (taisui, "太歲"), (hegod, "合神"), (jigod, "計神"), (shiji, "始擊"), (dingmu, "定目"), (kingbase, "君基"),
                       (OFFICER_BASE[i36], "臣基"), (_rot(B, "申")[(k - 1) % 12], "民基"), (FOUR_GOD[i36], "四神"), (SKY_YI[i36], "天乙"), (EARTH_YI[i36], "地乙"),
                       (ZHI_FU[i36], "直符"), (kingfu, "帝符"), (taijun, "太尊"), (wufu, "五福"), (NUM2CELL[ty_num], "太乙"), (NUM2CELL[home_gen], "主將"),
                       (NUM2CELL[vg(home_gen)], "主參"), (NUM2CELL[away_gen], "客將"), (NUM2CELL[vg(away_gen)], "客參"), (yangjiu, "陽九"), (baliu, "百六")):
        put(cell if cell in cells else "中", name)
    return {
        "method": ACC_NAME[method], "lunar_year": ly, "accumulated": acc, "ju": k, "ju_label": f"陽遁{k}局", "li": "理天理地理人"[((k - 1) % 3) * 2:((k - 1) % 3) * 2 + 2],
        "taisui": taisui, "jigod": jigod, "hegod": hegod,
        "taiyi": NUM2GONG[ty_num], "taiyi_num": ty_num, "taiyi_assist": assist,
        "wenchang": wenchang, "wenchang_god": SIXTEEN_GOD.get(wenchang, ""), "shiji": shiji, "shiji_god": SIXTEEN_GOD.get(shiji, ""), "dingmu": dingmu,
        "home_cal": home_cal, "home_cal_desc": _cal_desc(home_cal), "home_general": home_gen, "home_vgen": vg(home_gen),
        "away_cal": away_cal, "away_cal_desc": _cal_desc(away_cal), "away_general": away_gen, "away_vgen": vg(away_gen),
        "set_cal": set_cal, "set_general": set_gen, "set_vgen": vg(set_gen),
        "four_god": FOUR_GOD[i36], "sky_yi": SKY_YI[i36], "earth_yi": EARTH_YI[i36], "zhi_fu": ZHI_FU[i36],
        "king_base": kingbase, "officer_base": OFFICER_BASE[i36], "people_base": _rot(B, "申")[(k - 1) % 12], "wufu": wufu, "kingfu": kingfu, "taijun": taijun,
        "flybird": flybird, "threewind": threewind, "fivewind": fivewind, "eightwind": eightwind, "bigyo": bigyo, "smallyo": smallyo, "yangjiu": yangjiu, "baliu": baliu,
        "door_on_duty": door_on_duty, "doors": {NUM2GONG[n]: dr for n, dr in doors.items()}, "three_doors": three_doors, "five_generals": five_gen,
        "host_guest_relation": host_guest, "count_verdict": count_verdict, "verdict": verdict, "sixteen": {c: v for c, v in cells.items() if v},
    }
