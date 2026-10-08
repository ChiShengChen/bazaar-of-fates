"""八字 full 排盤 extension / 完整八字命盤擴充 — the almanac-grade detail the synced
engine core deliberately leaves out (it only needs 四柱 + 喜用神 for its trading signal).

Native module (NOT synced). Everything a traditional 排盤 sheet shows, in the style of
周易大學堂-type online 排盤:
  • exact 節氣 (sun's apparent ecliptic longitude via ephem → minute-accurate 交節)
  • 四柱 with precise 年/月 boundaries (立春 / 12 節), 十神, 藏干(+十神), 納音, 空亡, 十二長生
  • 胎元, 命宮, 農曆日期 + 生肖 + 時辰
  • 起運 (三日折一年, 陽男陰女順 / 陰男陽女逆, to the minute) + 交運日期 + 換運尾數
  • 大運 ×9 (each with its 流年 ×10, each with 流月 ×12 + 神煞 + 刑沖合會留意), 小運
  • 神煞 (common set), 天干/地支 relations (五合・相沖 / 六沖・六合・三合・三會・刑・破・害・暗合)
  • 稱骨 (袁天罡) weight + verdict
Built on the engine's day-pillar anchor and 五虎遁/五鼠遁 helpers so day/hour pillars agree
with the synced core; year/month pillars here are exact-節氣 (the core uses ±1-day tables).
"""

from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta
from functools import lru_cache

import ephem

from fortune.birth import BirthInput
from fortune.engines.bazi import bazi as BZ

STEMS, BRANCHES = BZ.STEMS, BZ.BRANCHES
STEM_ELEM, BRANCH_ELEM = BZ.STEM_ELEM, BZ.BRANCH_ELEM
ZODIAC = BZ.BRANCH_ZODIAC
SHENG, KE = BZ.SHENG, BZ.KE

# --- static tables ------------------------------------------------------------

HIDDEN = ["癸", "己癸辛", "甲丙戊", "乙", "戊乙癸", "丙庚戊", "丁己", "己丁乙", "庚壬戊", "辛", "戊辛丁", "壬甲"]  # 藏干 (本氣 first)

NAYIN = ["海中金", "爐中火", "大林木", "路旁土", "劍鋒金", "山頭火", "澗下水", "城頭土", "白蠟金", "楊柳木",
         "泉中水", "屋上土", "霹靂火", "松柏木", "長流水", "沙中金", "山下火", "平地木", "壁上土", "金箔金",
         "覆燈火", "天河水", "大驛土", "釵釧金", "桑柘木", "大溪水", "沙中土", "天上火", "石榴木", "大海水"]

CHANGSHENG = ["長生", "沐浴", "冠帶", "臨官", "帝旺", "衰", "病", "死", "墓", "絕", "胎", "養"]
_CS_START = [11, 6, 2, 9, 2, 9, 5, 0, 8, 3]      # 長生 branch for 甲…癸 (陽順陰逆)

JIE = [  # the 12 節 (month boundaries): (sun longitude, name, month branch idx)
    (315, "立春", 2), (345, "驚蟄", 3), (15, "清明", 4), (45, "立夏", 5), (75, "芒種", 6), (105, "小暑", 7),
    (135, "立秋", 8), (165, "白露", 9), (195, "寒露", 10), (225, "立冬", 11), (255, "大雪", 0), (285, "小寒", 1),
]
_JIE_APPROX_DOY = {315: 35, 345: 64, 15: 95, 45: 125, 75: 156, 105: 188, 135: 219, 165: 250, 195: 281, 225: 311, 255: 341, 285: 5}

LUNAR_MONTH = ["正月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "冬月", "臘月"]
LUNAR_DAY = (["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
              "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
              "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"])

# --- 十神 ---------------------------------------------------------------------

def ten_god(dm: int, other: int) -> str:
    """十神 of stem `other` relative to the day master stem `dm` (both 0–9)."""
    de, oe = STEM_ELEM[dm], STEM_ELEM[other]
    same = (dm % 2) == (other % 2)
    if oe == de:
        return "比肩" if same else "劫財"
    if SHENG[oe] == de:
        return "偏印" if same else "正印"
    if SHENG[de] == oe:
        return "食神" if same else "傷官"
    if KE[de] == oe:
        return "偏財" if same else "正財"
    return "七殺" if same else "正官"


def hidden_gods(dm: int, branch: int) -> list[dict]:
    return [{"stem": s, "god": ten_god(dm, STEMS.index(s))} for s in HIDDEN[branch]]


def changsheng(dm: int, branch: int) -> str:
    """十二長生 of the day master on `branch`."""
    step = (branch - _CS_START[dm]) % 12 if dm % 2 == 0 else (_CS_START[dm] - branch) % 12
    return CHANGSHENG[step]


def gz_index(stem: int, branch: int) -> int:
    """0–59 index in the 六十甲子 cycle."""
    return (6 * stem - 5 * branch) % 60


def nayin(stem: int, branch: int) -> str:
    return NAYIN[gz_index(stem, branch) // 2]


def kong_wang(stem: int, branch: int) -> str:
    """旬空 of the 旬 this pillar belongs to."""
    head = gz_index(stem, branch) // 10 * 10
    hb = head % 12
    return BRANCHES[(hb + 10) % 12] + BRANCHES[(hb + 11) % 12]


# --- exact 節氣 -----------------------------------------------------------------

def _sun_lon(dt_utc: datetime) -> float:
    s = ephem.Sun(ephem.Date(dt_utc))
    eq = ephem.Equatorial(s.ra, s.dec, epoch=ephem.Date(dt_utc))
    return math.degrees(ephem.Ecliptic(eq).lon) % 360.0


def _signed(a: float, target: float) -> float:
    return ((a - target + 180.0) % 360.0) - 180.0


@lru_cache(maxsize=512)
def _term_utc(year: int, lon: int) -> datetime:
    """UTC instant when the sun reaches ecliptic longitude `lon` in (Gregorian) `year`."""
    lo = datetime(year, 1, 1) + timedelta(days=_JIE_APPROX_DOY[lon] - 6)
    hi = lo + timedelta(days=12)
    for _ in range(26):                              # 12 days → ~0.2 s
        mid = lo + (hi - lo) / 2
        if _signed(_sun_lon(mid), lon) < 0:
            lo = mid
        else:
            hi = mid
    return lo + (hi - lo) / 2


def jie_terms(year: int, tz: float) -> list[tuple[datetime, str, int]]:
    """The 12 節 of `year` in local time: [(local datetime, name, month branch idx)]."""
    off = timedelta(hours=tz)
    return sorted((_term_utc(year, lon) + off, name, mb) for lon, name, mb in JIE)


def surrounding_jie(dt: datetime, tz: float) -> tuple[tuple[datetime, str, int], tuple[datetime, str, int]]:
    """(previous 節, next 節) around local datetime `dt`."""
    terms = jie_terms(dt.year - 1, tz) + jie_terms(dt.year, tz) + jie_terms(dt.year + 1, tz)
    prev = max(t for t in terms if t[0] <= dt)
    nxt = min(t for t in terms if t[0] > dt)
    return prev, nxt


# --- pillars ---------------------------------------------------------------------

def _pillar(s: int, b: int, dm: int, role: str, role_zh: str) -> dict:
    return {
        "role": role, "pillar": role_zh, "stem": STEMS[s], "branch": BRANCHES[b], "gz": STEMS[s] + BRANCHES[b],
        "stem_idx": s, "branch_idx": b, "stem_elem": STEM_ELEM[s], "branch_elem": BRANCH_ELEM[b],
        "zodiac": ZODIAC[b], "stem_god": ("元男/元女" if role == "day" else ten_god(dm, s)),
        "hidden": hidden_gods(dm, b), "nayin": nayin(s, b), "kong_wang": kong_wang(s, b),
        "changsheng": changsheng(dm, b),
    }


def exact_pillars(dt: datetime, tz: float) -> dict:
    """四柱 with exact 立春 / 節 boundaries. 子時 23:00–00:59 stays on the clock date (晚子時不換日)."""
    prev, _nxt = surrounding_jie(dt, tz)
    lichun = next(t for t in jie_terms(dt.year, tz) if t[1] == "立春")
    y = dt.year if dt >= lichun[0] else dt.year - 1
    ys, yb = (y - 4) % 10, (y - 4) % 12
    mb = prev[2]
    base_yin = (2 + 2 * (ys % 5)) % 10
    ms = (base_yin + (mb - 2) % 12) % 10
    ds, db = BZ.day_pillar(dt.date())
    hs, hb = BZ.hour_pillar(ds, dt.hour)
    return {
        "year": _pillar(ys, yb, ds, "year", "年柱"), "month": _pillar(ms, mb, ds, "month", "月柱"),
        "day": _pillar(ds, db, ds, "day", "日柱"), "hour": _pillar(hs, hb, ds, "hour", "時柱"),
    }


def tai_yuan(ms: int, mb: int) -> str:
    """胎元 = 月干進一・月支進三."""
    return STEMS[(ms + 1) % 10] + BRANCHES[(mb + 3) % 12]


def ming_gong(ms: int, mb: int, hb: int) -> str:
    """命宮 (寅=1 counting for both month & hour; stems follow the month pillar in the 60-cycle)."""
    m = (mb - 2) % 12 + 1
    h = (hb - 2) % 12 + 1
    idx = 26 - (m + h)
    if idx > 12:
        idx -= 12
    shift = idx - m
    i = (gz_index(ms, mb) + shift) % 60
    return STEMS[i % 10] + BRANCHES[i % 12]


# --- 神煞 -------------------------------------------------------------------------

_TIANYI = ["丑未", "子申", "亥酉", "亥酉", "丑未", "子申", "午寅", "午寅", "巳卯", "巳卯"]
_TAIJI = ["子午", "子午", "卯酉", "卯酉", "辰戌丑未", "辰戌丑未", "寅亥", "寅亥", "巳申", "巳申"]
_WENCHANG = "巳午申酉申酉亥子寅卯"
_TIANCHU = "巳午巳午申酉亥子寅卯"
_LUSHEN = "寅卯巳午巳午申酉亥子"
_YANGREN = "卯辰午未午未酉戌子丑"
_GUOYIN = "戌亥丑寅丑寅辰巳未申"
_TIANDE = ["巳", "庚", "丁", "申", "壬", "辛", "亥", "甲", "癸", "寅", "丙", "乙"]   # by month branch 子…亥 (stem or branch)
_YUEDE = {0: "壬", 1: "庚", 2: "丙", 3: "甲", 4: "壬", 5: "庚", 6: "丙", 7: "甲", 8: "壬", 9: "庚", 10: "丙", 11: "甲"}
_SANHE_GROUP = {0: 0, 4: 0, 8: 0, 2: 1, 6: 1, 10: 1, 5: 2, 9: 2, 1: 2, 11: 3, 3: 3, 7: 3}   # 申子辰/寅午戌/巳酉丑/亥卯未
_JIANGXING = [0, 6, 9, 3]
_YIMA = [2, 8, 11, 5]
_HUAGAI = [4, 10, 1, 7]
_TAOHUA = [9, 3, 6, 0]
_JIESHA = [5, 11, 2, 8]
_WANGSHEN = [11, 5, 8, 2]
_GUCHEN = {11: 2, 0: 2, 1: 2, 2: 5, 3: 5, 4: 5, 5: 8, 6: 8, 7: 8, 8: 11, 9: 11, 10: 11}
_GUASU = {11: 10, 0: 10, 1: 10, 2: 1, 3: 1, 4: 1, 5: 4, 6: 4, 7: 4, 8: 7, 9: 7, 10: 7}
_SIFEI = {2: ("庚申", "辛酉"), 3: ("庚申", "辛酉"), 4: ("庚申", "辛酉"), 5: ("壬子", "癸亥"), 6: ("壬子", "癸亥"), 7: ("壬子", "癸亥"),
          8: ("甲寅", "乙卯"), 9: ("甲寅", "乙卯"), 10: ("甲寅", "乙卯"), 11: ("丙午", "丁巳"), 0: ("丙午", "丁巳"), 1: ("丙午", "丁巳")}
_TIANSHE = {2: "戊寅", 3: "戊寅", 4: "戊寅", 5: "甲午", 6: "甲午", 7: "甲午", 8: "戊申", 9: "戊申", 10: "戊申", 11: "甲子", 0: "甲子", 1: "甲子"}


def shensha_for(stem: int | None, branch: int, *, ys: int, ds: int, yb: int, db: int, mb: int, is_pillar: bool = False, gz: str = "") -> list[str]:
    """神煞 landing on (stem, branch): looked up from 年干/日干 (stem rules) and 年支/日支 (三合 rules)."""
    b = BRANCHES[branch]
    out: list[str] = []
    for s in {ys, ds}:
        if b in _TIANYI[s]:
            out.append("天乙貴人")
        if b in _TAIJI[s]:
            out.append("太極貴人")
        if b == _WENCHANG[s]:
            out.append("文昌貴人")
        if b == _GUOYIN[s]:
            out.append("國印貴人")
    if b == _TIANCHU[ds]:
        out.append("天廚貴人")
    if b == _LUSHEN[ds]:
        out.append("祿神")
    if b == _YANGREN[ds]:
        out.append("羊刃")
    if branch == _CS_START[ds]:
        out.append("學堂")
    if stem is not None and STEMS[stem] == _TIANDE[mb] or b == _TIANDE[mb]:
        out.append("天德貴人")
    if stem is not None and STEMS[stem] == _YUEDE[mb]:
        out.append("月德貴人")
    if branch == (mb - 1) % 12:
        out.append("天醫")
    for ref in {yb, db}:
        g = _SANHE_GROUP[ref]
        if branch == _JIANGXING[g]:
            out.append("將星")
        if branch == _YIMA[g]:
            out.append("驛馬")
        if branch == _HUAGAI[g]:
            out.append("華蓋")
        if branch == _TAOHUA[g]:
            out.append("桃花")
        if branch == _JIESHA[g]:
            out.append("劫煞")
        if branch == _WANGSHEN[g]:
            out.append("亡神")
    if branch == _GUCHEN[yb]:
        out.append("孤辰")
    if branch == _GUASU[yb]:
        out.append("寡宿")
    if branch == (3 - yb) % 12:
        out.append("紅鸞")
    if branch == (9 - yb) % 12:
        out.append("天喜")
    if branch == (yb + 2) % 12:
        out.append("喪門")
    if branch == (yb - 2) % 12:
        out.append("吊客")
    if is_pillar and gz:
        if gz in _SIFEI[mb]:
            out.append("四廢")
        if gz == _TIANSHE[mb]:
            out.append("天赦")
        if gz in ("庚辰", "壬辰", "戊戌", "庚戌"):
            out.append("魁罡")
        if gz in ("乙丑", "己巳", "癸酉"):
            out.append("金神")
    return list(dict.fromkeys(out))


# --- 刑沖合會 relations -------------------------------------------------------------

_LIUHE = {(0, 1): "土", (2, 11): "木", (3, 10): "火", (4, 9): "金", (5, 8): "水", (6, 7): "火"}
_SANHE = [((8, 0, 4), "水"), ((2, 6, 10), "火"), ((5, 9, 1), "金"), ((11, 3, 7), "木")]
_SANHUI = [((2, 3, 4), "東方木"), ((5, 6, 7), "南方火"), ((8, 9, 10), "西方金"), ((11, 0, 1), "北方水")]
_PO = {(0, 9), (3, 6), (2, 11), (5, 8), (1, 4), (7, 10)}
_HAI = {(0, 7), (1, 6), (2, 5), (3, 4), (8, 11), (9, 10)}
_ANHE = {(1, 2): "土", (6, 11): "木", (3, 8): "金", (0, 4): "火", (0, 10): "火", (5, 9): "水"}
_ZIXING = {4, 6, 9, 11}
_WUHE = {(0, 5): "土", (1, 6): "金", (2, 7): "水", (3, 8): "木", (4, 9): "火"}
_GANCHONG = {(0, 6), (1, 7), (2, 8), (3, 9)}


def branch_relations(branches: list[int]) -> list[str]:
    """Pairwise/triple relations among the given branches (natal, or natal+大運+流年)."""
    out: list[str] = []
    n = len(branches)
    present = set(branches)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = sorted((branches[i], branches[j]))      # canonical 地支 order for the label
            k = (a, b)
            ba, bb = BRANCHES[a], BRANCHES[b]
            if (a - b) % 12 == 6:
                out.append(f"{ba}{bb}相沖")
            if k in _LIUHE:
                out.append(f"{ba}{bb}合化{_LIUHE[k]}")
            if a == b and a in _ZIXING:
                out.append(f"{ba}{bb}自刑")
            if {a, b} == {0, 3}:
                out.append(f"{ba}{bb}相刑")
            if k in _PO:
                out.append(f"{ba}{bb}相破")
            if k in _HAI:
                out.append(f"{ba}{bb}相害")
            if k in _ANHE:
                out.append(f"{ba}{bb}暗合{_ANHE[k]}")
    for trio, elem in _SANHE:
        if set(trio) <= present:
            out.append("".join(BRANCHES[x] for x in trio) + f"三合{elem}局")
    for trio, elem in _SANHUI:
        if set(trio) <= present:
            out.append("".join(BRANCHES[x] for x in trio) + f"會{elem}")
    for trio, name in (((2, 5, 8), "無恩之刑"), ((1, 10, 7), "恃勢之刑")):
        if set(trio) <= present:
            out.append("".join(BRANCHES[x] for x in trio) + f"三刑（{name}）")
    return list(dict.fromkeys(out))


def stem_relations(stems: list[int]) -> list[str]:
    out: list[str] = []
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            a, b = sorted((stems[i], stems[j]))
            k = (a, b)
            if k in _WUHE:
                out.append(f"{STEMS[a]}{STEMS[b]}合化{_WUHE[k]}")
            if k in _GANCHONG:
                out.append(f"{STEMS[a]}{STEMS[b]}相沖")
    return list(dict.fromkeys(out))


# --- 稱骨 -----------------------------------------------------------------------------

_BONE_YEAR = [1.2, 0.9, 0.6, 0.7, 1.2, 0.5, 0.9, 0.8, 0.7, 0.8, 1.5, 0.9, 1.6, 0.8, 0.8, 1.9, 1.2, 0.6, 0.8, 0.7,
              0.5, 1.5, 0.6, 1.6, 1.5, 0.7, 0.9, 1.2, 1.0, 0.7, 1.5, 0.6, 0.5, 1.4, 1.4, 0.9, 0.7, 0.7, 0.9, 1.2,
              0.8, 0.7, 1.3, 0.5, 1.4, 0.5, 0.9, 1.7, 0.5, 0.7, 1.2, 0.8, 0.8, 0.6, 1.9, 0.6, 0.8, 1.6, 1.0, 0.6]
_BONE_MONTH = [0.6, 0.7, 1.8, 0.9, 0.5, 1.6, 0.9, 1.5, 1.8, 0.8, 0.9, 0.5]
_BONE_DAY = [0.5, 1.0, 0.8, 1.5, 1.6, 1.5, 0.8, 1.6, 0.8, 1.6, 0.9, 1.7, 0.8, 1.7, 1.0, 0.8, 0.9, 1.8, 0.5, 1.5,
             1.0, 0.9, 0.8, 0.9, 1.5, 1.8, 0.7, 0.8, 1.6, 0.6]
_BONE_HOUR = [1.6, 0.6, 0.7, 1.0, 0.9, 1.6, 1.0, 0.8, 0.8, 0.9, 0.6, 0.6]
_BONE_TEXT = {
    21: "短命非業謂大空，平生災難事重重；凶禍頻臨陷逆境，終世困苦事不成。",
    22: "身寒骨冷苦伶仃，此命推來行乞人；勞勞碌碌無度日，終年打拱過平年。",
    23: "此命推來骨自輕，求謀作事事難成；妻兒兄弟實難靠，別處他鄉作散人。",
    24: "此命推來福祿無，門庭困苦總難榮；六親骨肉皆無靠，流浪他鄉作老翁。",
    25: "此命推來祖業微，門庭營度似稀奇；六親骨肉如冰炭，一世勤勞自把持。",
    26: "平生衣祿苦中求，獨自營謀事不休；離祖出門宜早計，晚來衣祿自無休。",
    27: "一生作事少商量，難靠祖宗作主張；獨馬單槍空做去，早年晚歲總無長。",
    28: "一生行事似飄蓬，祖宗產業在夢中；若不過房改名姓，也當移徙二三通。",
    29: "初年運限未曾亨，縱有功名在後成；須過四旬才可立，移居改姓始為良。",
    30: "勞勞碌碌苦中求，東奔西走何日休；若使終身勤與儉，老來稍可免憂愁。",
    31: "忙忙碌碌苦中求，何日雲開見日頭；難得祖基家可立，中年衣食漸無憂。",
    32: "初年運蹇事難謀，漸有財源如水流；到得中年衣食旺，那時名利一齊收。",
    33: "早年做事事難成，百年勤勞枉費心；半世自如流水去，後來運到始得金。",
    34: "此命福氣果如何，僧道門中衣祿多；離祖出家方為妙，朝晚拜佛念彌陀。",
    35: "生平福量不周全，祖業根基覺少傳；營事生涯宜守舊，時來衣食勝從前。",
    36: "不須勞碌過平生，獨自成家福不輕；早有福星常照命，任君行去百般成。",
    37: "此命般般事不成，弟兄少力自孤成；雖然祖業須微有，來得明時去不明。",
    38: "一生骨肉最清高，早入簧門姓名標；待到年將三十六，藍衫脫去換紅袍。",
    39: "此命終身運不通，勞勞作事盡皆空；苦心竭力成家計，到得那時在夢中。",
    40: "平生衣祿是綿長，件件心中自主張；前面風霜多受過，後來必定享安康。",
    41: "此命推來事不同，為人能幹略凡庸；中年還有逍遙福，不比前時運未通。",
    42: "得寬懷處且寬懷，何用雙眉皺不開；若使中年命運濟，那時名利一齊來。",
    43: "為人心性最聰明，作事軒昂近貴人；衣祿一生天數定，不須勞碌是豐亨。",
    44: "來事由天莫苦求，須知福祿勝前途；當年財帛難如意，晚景欣然便不憂。",
    45: "名利推來竟若何，前番辛苦後奔波；命中難養男與女，骨肉扶持也不多。",
    46: "東西南北盡皆通，出姓移居更覺隆；衣祿無虧天數定，中年晚景一般同。",
    47: "此命推來旺末年，妻榮子貴自怡然；平生原有滔滔福，可有財源如水源。",
    48: "初年運道未曾通，幾許蹉跎命亦窮；兄弟六親皆無靠，一身事業晚年成。",
    49: "此命推來福不輕，自成自立顯門庭；從來富貴人欽敬，使婢差奴過一生。",
    50: "為利為名終日勞，中年福祿也多遭；老來自有財星照，不比前番目下高。",
    51: "一世榮華事事通，不須勞碌自亨通；弟兄叔侄皆如意，家業成時福祿宏。",
    52: "一世亨通事事能，不須勞思自然寧；宗族欣然心皆好，家業豐亨自稱心。",
    53: "此格推來福澤宏，興家立業在其中；一生衣食安排定，卻是人間一福翁。",
    54: "此命推來厚且清，詩書滿腹看功成；豐衣足食自然穩，正是人間有福人。",
    55: "走馬揚鞭爭利名，少年作事費籌論；一朝福祿源源至，富貴榮華顯六親。",
    56: "此格推來禮義通，一生福祿用無窮；甜酸苦辣皆嘗過，滾滾財源穩且豐。",
    57: "福祿豐盈萬事全，一生榮耀顯雙親；名揚威振人欽敬，處世逍遙似遇春。",
    58: "平生福祿自然來，名利兼全福壽偕；雁塔題名為貴客，紫袍玉帶走金階。",
    59: "細推此格妙且清，必定財高禮義通；甲第之中應有分，揚鞭走馬顯威榮。",
    60: "一朝金榜快題名，顯祖榮宗立大功；一生衣祿豐盈足，世上榮華萬事通。",
    61: "不作朝中金榜客，定為世上一財翁；聰明天賦經書熟，名顯高科自是榮。",
    62: "此命生來福不窮，讀書必定顯親宗；紫衣金帶為卿相，富貴榮華皆可同。",
    63: "命主為官福祿長，得來富貴實非常；名題雁塔傳金榜，定中高科天下揚。",
    64: "此格威權不可當，紫袍金帶坐高堂；榮華富貴誰能及，萬古留名姓氏揚。",
    65: "細推此命福非輕，富貴榮華孰與爭；定是天生官祿格，封侯拜相更揚名。",
    66: "此格人間一福人，堆金積玉滿堂春；從來富貴由天定，正笏垂紳謁聖君。",
    67: "此命生來福自宏，田園家業最高隆；平生衣祿盈豐足，一路榮華萬事通。",
    68: "富貴由天莫苦求，萬金家計不須謀；十年不比前番事，祖業根基千古留。",
    69: "君是人間衣祿星，一生富貴眾人欽；縱然福祿由天定，安享榮華過一生。",
    70: "此命推來福不輕，不須愁慮苦勞心；一生天定衣與祿，富貴榮華主一生。",
    71: "此命生成大不同，公侯卿相在其中；一生自有逍遙福，富貴榮華極品隆。",
}
_CN_NUM = "零一二三四五六七八九"


def lunar_info(d: date, hb: int) -> dict:
    from lunardate import LunarDate
    ld = LunarDate.from_solar_date(d.year, d.month, d.day)
    ly = (ld.year - 4) % 60
    return {
        "year": ld.year, "month": ld.month, "day": ld.day, "leap": bool(ld.is_leap_month),
        "year_gz": STEMS[ly % 10] + BRANCHES[ly % 12], "zodiac": ZODIAC[(ld.year - 4) % 12],
        "text": f"{ld.year}年（{ZODIAC[(ld.year - 4) % 12]}）{'閏' if ld.is_leap_month else ''}{LUNAR_MONTH[ld.month - 1]}{LUNAR_DAY[ld.day - 1]}{BRANCHES[hb]}時",
    }


def cheng_gu(lunar: dict, hb: int) -> dict:
    """袁天罡稱骨: 年(農曆干支) + 月(農曆) + 日(農曆) + 時 weights in 兩."""
    ly = (lunar["year"] - 4) % 60
    w = _BONE_YEAR[ly] + _BONE_MONTH[lunar["month"] - 1] + _BONE_DAY[lunar["day"] - 1] + _BONE_HOUR[hb]
    key = int(round(w * 10))
    key = max(21, min(71, key))
    liang, qian = key // 10, key % 10
    label = f"{_CN_NUM[liang]}兩" + (f"{_CN_NUM[qian]}錢" if qian else "")
    return {"weight": round(w, 1), "label": label, "verdict": _BONE_TEXT[key]}


# --- 起運 / 大運 / 流年 / 流月 ---------------------------------------------------------

def _is_male(birth: BirthInput) -> bool | None:
    g = (birth.gender or "").strip().lower()
    if g in {"male", "m", "男", "boy", "man"}:
        return True
    if g in {"female", "f", "女", "girl", "woman"}:
        return False
    return None


def _add_months(dt: datetime, years: int, months: int) -> datetime:
    m = dt.month - 1 + months + 12 * years
    y, m = dt.year + m // 12, m % 12 + 1
    day = min(dt.day, [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return dt.replace(year=y, month=m, day=day)


def qi_yun(dt: datetime, tz: float, forward: bool) -> dict:
    """起運: distance to the next (順) / previous (逆) 節, 三日折一年 (1 day → 4 months, 1 時辰 → 10 days)."""
    prev, nxt = surrounding_jie(dt, tz)
    delta = (nxt[0] - dt) if forward else (dt - prev[0])
    luck_days = delta.total_seconds() / 86400.0 * 120.0        # ×120: 3 days → 360 luck-days (1 yr)
    years = int(luck_days // 360)
    rem = luck_days - years * 360
    months = int(rem // 30)
    rem -= months * 30
    days = int(rem)
    hours = int(round((rem - days) * 24))
    if hours == 24:
        days, hours = days + 1, 0
    jiao = _add_months(dt, years, months) + timedelta(days=days, hours=hours)
    return {
        "forward": forward, "ref_term": (nxt if forward else prev)[1], "ref_term_at": (nxt if forward else prev)[0].isoformat(timespec="minutes"),
        "years": years, "months": months, "days": days, "hours": hours,
        "text": f"出生後 {years} 年 {months} 個月 {days} 天 {hours} 小時起運",
        "jiao_yun": jiao.isoformat(timespec="minutes"), "jiao_yun_year": jiao.year,
        "huan_yun_digit": jiao.year % 10,
    }


def _liuyue(year_stem: int) -> list[dict]:
    base = (2 + 2 * (year_stem % 5)) % 10
    return [{"gz": STEMS[(base + k) % 10] + BRANCHES[(2 + k) % 12], "jie": JIE[k][1]} for k in range(12)]


def full_chart(birth: BirthInput, *, dayun_count: int = 9, today: date | None = None) -> dict:
    """Everything the 排盤 sheet needs, as one JSON-able dict."""
    today = today or date.today()
    tz = birth.tz_offset_hours
    dt = birth.dt
    p = exact_pillars(dt, tz)
    ys, yb = p["year"]["stem_idx"], p["year"]["branch_idx"]
    ms, mb = p["month"]["stem_idx"], p["month"]["branch_idx"]
    ds, db = p["day"]["stem_idx"], p["day"]["branch_idx"]
    hs, hb = p["hour"]["stem_idx"], p["hour"]["branch_idx"]
    ss_kw = dict(ys=ys, ds=ds, yb=yb, db=db, mb=mb)
    for k in ("year", "month", "day", "hour"):
        p[k]["shensha"] = shensha_for(p[k]["stem_idx"], p[k]["branch_idx"], is_pillar=True, gz=p[k]["gz"], **ss_kw)

    natal_stems = [ys, ms, ds, hs]
    natal_branches = [yb, mb, db, hb]
    prev, nxt = surrounding_jie(dt, tz)
    male = _is_male(birth)
    assumed = male is None
    if male is None:
        male = True
    p["day"]["stem_god"] = "元男" if male else "元女"
    year_yang = ys % 2 == 0
    forward = (year_yang and male) or (not year_yang and not male)
    qy = qi_yun(dt, tz, forward)
    lunar = lunar_info(dt.date(), hb)
    fav = set(BZ.strength_and_favourable({k: {"stem_elem": p[k]["stem_elem"], "branch_elem": p[k]["branch_elem"], "stem": p[k]["stem"]} for k in p})["favourable"])
    birth_year_gz = (dt.year if dt >= next(t for t in jie_terms(dt.year, tz) if t[1] == "立春")[0] else dt.year - 1)

    dayun: list[dict] = []
    for i in range(dayun_count):
        step = (i + 1) if forward else -(i + 1)
        s, b = (ms + step) % 10, (mb + step) % 12
        start_year = qy["jiao_yun_year"] + 10 * i
        start_age = qy["years"] + 10 * i
        liunian = []
        for k in range(10):
            yr = start_year + k
            ls, lb = (yr - 4) % 10, (yr - 4) % 12
            liunian.append({
                "year": yr, "age": yr - birth_year_gz, "gz": STEMS[ls] + BRANCHES[lb],
                "stem_god": ten_god(ds, ls), "hidden": hidden_gods(ds, lb), "nayin": nayin(ls, lb),
                "changsheng": changsheng(ds, lb), "shensha": shensha_for(ls, lb, **ss_kw),
                "stem_notes": stem_relations(natal_stems + [s, ls]),
                "branch_notes": branch_relations(natal_branches + [b, lb]),
                "liuyue": _liuyue(ls), "nature": "favourable" if STEM_ELEM[ls] in fav else "unfavourable",
                "current": yr == today.year,
            })
        dayun.append({
            "index": i, "gz": STEMS[s] + BRANCHES[b], "stem": STEMS[s], "branch": BRANCHES[b],
            "stem_god": ten_god(ds, s), "hidden": hidden_gods(ds, b), "nayin": nayin(s, b),
            "changsheng": changsheng(ds, b), "kong_wang": kong_wang(s, b),
            "shensha": shensha_for(s, b, **ss_kw),
            "start_age": start_age, "start_year": start_year, "end_year": start_year + 9,
            "stem_notes": stem_relations(natal_stems + [s]), "branch_notes": branch_relations(natal_branches + [b]),
            "nature": "favourable" if STEM_ELEM[s] in fav else "unfavourable",
            "current": start_year <= today.year <= start_year + 9,
            "liunian": liunian,
        })

    xiaoyun = []
    for k in range(1, max(1, qy["years"]) + 1):
        step = k if forward else -k
        s, b = (hs + step) % 10, (hb + step) % 12
        xiaoyun.append({"age": k, "year": birth_year_gz + k, "gz": STEMS[s] + BRANCHES[b], "stem_god": ten_god(ds, s)})

    return {
        "pillars": [p["year"], p["month"], p["day"], p["hour"]],
        "day_master": {"stem": STEMS[ds], "elem": STEM_ELEM[ds], "yinyang": BZ.STEM_YINYANG[ds]},
        "gender": "男" if male else "女", "gender_assumed": assumed,
        "tai_yuan": tai_yuan(ms, mb), "tai_yuan_nayin": nayin((ms + 1) % 10, (mb + 3) % 12),
        "ming_gong": ming_gong(ms, mb, hb),
        "ming_gong_nayin": NAYIN[gz_index(STEMS.index(ming_gong(ms, mb, hb)[0]), BRANCHES.index(ming_gong(ms, mb, hb)[1])) // 2],
        "jie_prev": {"name": prev[1], "at": prev[0].isoformat(timespec="minutes")},
        "jie_next": {"name": nxt[1], "at": nxt[0].isoformat(timespec="minutes")},
        "solar": dt.isoformat(timespec="minutes"), "time_known": birth.birth_time is not None,
        "lunar": lunar,
        "qi_yun": qy,
        "stem_notes": stem_relations(natal_stems), "branch_notes": branch_relations(natal_branches),
        "cheng_gu": cheng_gu(lunar, hb),
        "dayun": dayun, "xiaoyun": xiaoyun,
        "favourable": sorted(fav),
    }
