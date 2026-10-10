"""姓名學引擎（熊崎式五格剖象法）— 筆畫、五格、三才、81 數理，全部是查表與加法。

- 筆畫：康熙筆畫＝部首「原形」的筆畫＋部首以外的筆畫（氵算水 4、扌算手 4、艹算艸 6、阝左算阜 8、阝右算邑 7……）。
  資料來自 Unicode 官方 Unihan 的 kRSUnicode（部首.其餘筆畫），每個字都查得到怎麼算的。
- 五格：天格、人格、地格、外格、總格；單姓天格、單名地格各加「假數」1。
- 三才：天、人、地三格的五行（尾數 1、2 木，3、4 火，5、6 土，7、8 金，9、0 水）與彼此生剋。
- 81 數理：超過 81 減 80 循環；吉凶分類見 SHULI。

流派開關（schools/*.yaml 的 xingming）：筆畫用康熙或現代、數字字照數值或照字形、單姓單名加不加假數。
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

STROKES_FILE = Path(__file__).with_name("strokes.tsv")

# 康熙 214 部首各自的筆畫（部首號區間 → 筆畫）
_RADICAL_RANGES = [(1, 6, 1), (7, 29, 2), (30, 60, 3), (61, 94, 4), (95, 117, 5), (118, 146, 6), (147, 166, 7),
                   (167, 175, 8), (176, 186, 9), (187, 194, 10), (195, 200, 11), (201, 204, 12), (205, 208, 13),
                   (209, 210, 14), (211, 211, 15), (212, 213, 16), (214, 214, 17)]
RADICAL_STROKES = {n: s for a, b, s in _RADICAL_RANGES for n in range(a, b + 1)}

def radical_char(n: int) -> str:
    """康熙部首號 → 部首字（Unicode 康熙部首區 U+2F00 起依序排，NFKC 正規化成一般漢字）。"""
    return unicodedata.normalize("NFKC", chr(0x2F00 + n - 1))


# 常被寫成變形、姓名學要還原的部首（只用來寫說明；筆畫一律照部首號查 RADICAL_STROKES）
RADICAL_NAMES = {
    9: "人（亻）", 18: "刀（刂）", 61: "心（忄）", 64: "手（扌）", 85: "水（氵）", 86: "火（灬）", 94: "犬（犭）",
    96: "玉（王）", 113: "示（礻）", 122: "网（罒）", 125: "老（耂）", 130: "肉（月）", 140: "艸（艹）",
    145: "衣（衤）", 162: "辵（辶）", 163: "邑（右阝）", 170: "阜（左阝）",
}

NUMERALS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

COMPOUND_SURNAMES = {
    "歐陽", "司馬", "上官", "諸葛", "東方", "皇甫", "尉遲", "公孫", "長孫", "慕容", "司徒", "司空", "令狐",
    "夏侯", "軒轅", "宇文", "端木", "西門", "南宮", "獨孤", "澹臺", "公羊", "張簡", "范姜", "鍾離", "呼延",
}

ELEMENTS = ["木", "火", "土", "金", "水"]
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}   # 我生
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}      # 我剋

# 81 數理吉凶（熊崎式通行分類，課程整理）。各家對「半吉」的歸類有出入：想照自己的師承，改這三組就好，盤面會跟著變。
_JI = {1, 3, 5, 6, 7, 8, 11, 13, 15, 16, 17, 18, 21, 23, 24, 25, 29, 31, 32, 33, 35, 37, 39, 41, 45, 47, 48,
       52, 57, 61, 63, 65, 67, 68, 81}
_BANJI = {27, 38, 49, 51, 55, 58, 71, 73, 75, 77, 78}
SHULI = {n: ("吉" if n in _JI else "半吉" if n in _BANJI else "凶") for n in range(1, 82)}

GRID_NAMES = ["天格", "人格", "地格", "外格", "總格"]
GRID_IDS = {"天格": "tian", "人格": "ren", "地格": "di", "外格": "wai", "總格": "zong"}


class NameInputError(ValueError):
    """姓名不合規。code：needs_full_name（沒填）｜bad_name（非中文、查不到筆畫、字數不對）。"""

    def __init__(self, message: str, code: str = "bad_name"):
        super().__init__(message)
        self.code = code


@dataclass
class Rules:
    stroke_basis: str = "kangxi"      # kangxi｜modern
    numeral_strokes: str = "value"    # value（四算 4、九算 9）｜shape（照字形）
    jiashu: str = "on"                # on：單姓天格、單名地格加假數 1｜off


@dataclass
class CharInfo:
    char: str
    role: str                 # 姓｜名
    strokes: int
    how: str                  # 這個字的筆畫怎麼來的
    modern: int               # 現代筆畫（台灣）
    kangxi: int               # 康熙筆畫
    traditional: str = ""     # 簡化字輸入時改用的正體字


@dataclass
class Grid:
    name: str
    number: int               # 原始數（未循環）
    shuli: int                # 數理用的數（>81 減 80）
    element: str
    yinyang: str
    luck: str                 # 吉｜半吉｜凶
    formula: str


@dataclass
class NameChart:
    surname: str
    given: str
    split_note: str
    chars: list[CharInfo]
    grids: dict[str, Grid]
    relations: dict[str, dict] = field(default_factory=dict)   # 成功運／基礎運／社交運
    sancai: str = ""
    warnings: list[str] = field(default_factory=list)


@lru_cache
def _table() -> dict[str, tuple[str, int, int, str]]:
    out = {}
    for line in STROKES_FILE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        out[parts[0]] = (parts[1], int(parts[2]), int(parts[3]), parts[4] if len(parts) > 4 else "")
    return out


def _kangxi(ch: str) -> tuple[int, str]:
    rad, residual, total, _ = _table()[ch]
    n = int(rad.rstrip("'"))
    if residual <= 0:          # 字本身就是部首（或部首的變形，如「王」是玉部 -1）：照字本身的筆畫
        return total, f"字本身就是部首（或部首的變形），照本字 {total} 畫（Unihan kRSUnicode {rad}.{residual}）"
    rs = RADICAL_STROKES[n]
    variant = RADICAL_NAMES.get(n)
    label = f"部首{variant or radical_char(n)} {rs} 畫" + ("（還原原形）" if variant else "")
    return rs + residual, f"{label}＋其餘 {residual} 畫＝{rs + residual}（Unihan kRSUnicode {rad}.{residual}）"


def char_strokes(ch: str, role: str, rules: Rules) -> tuple[CharInfo, list[str]]:
    t = _table()
    if ch not in t:
        if not ("㐀" <= ch <= "鿿" or "豈" <= ch <= "﫿"):
            raise NameInputError(f"「{ch}」不是中文字，姓名學只算中文姓名")
        raise NameInputError(f"「{ch}」不在筆畫表裡（罕用字），請改用常用寫法")
    warnings: list[str] = []
    trad = t[ch][3]
    base = ch
    if trad and trad in t:
        base = trad
        warnings.append(f"「{ch}」是簡化字，姓名學照正體「{trad}」計筆畫")
    kx, kx_how = _kangxi(base)
    modern = t[base][2]
    prefix = f"以正體「{base}」計；" if base != ch else ""
    if ch in NUMERALS and rules.numeral_strokes == "value":
        v = NUMERALS[ch]
        how = f"數字字照數值算 {v} 畫（字形 {modern} 畫）"
        return CharInfo(ch, role, v, how, modern, v), warnings
    if rules.stroke_basis == "modern":
        return CharInfo(ch, role, modern, prefix + f"現代筆畫 {modern} 畫（Unihan kTotalStrokes，台灣）", modern, kx, trad if base != ch else ""), warnings
    return CharInfo(ch, role, kx, prefix + "康熙筆畫：" + kx_how, modern, kx, trad if base != ch else ""), warnings


def split_name(full: str) -> tuple[str, str, str]:
    """回傳 (姓, 名, 說明)。有空白就照空白切；否則四字或三字開頭是常見複姓就當複姓，其餘第一字是姓。"""
    s = (full or "").strip()
    if not s:
        raise NameInputError("姓名學需要完整姓名", "needs_full_name")
    if " " in s or "　" in s:
        sur, _, giv = s.replace("　", " ").partition(" ")
        sur, giv = sur.strip(), giv.replace(" ", "")
        note = f"依空白切：姓「{sur}」、名「{giv}」"
    elif len(s) >= 3 and s[:2] in COMPOUND_SURNAMES:
        sur, giv = s[:2], s[2:]
        note = f"「{sur}」是常見複姓，當作複姓；若不是，請在姓與名之間加空白"
    else:
        sur, giv = s[:1], s[1:]
        note = "第一個字當姓；複姓或冠夫姓請在姓與名之間加空白（例：歐陽 娜娜）"
    if not giv:
        raise NameInputError("姓名至少要有姓和名兩個字")
    if not (1 <= len(sur) <= 2 and 1 <= len(giv) <= 3):
        raise NameInputError("姓要 1–2 字、名要 1–3 字")
    return sur, giv, note


def element_of(n: int) -> str:
    return ["水", "木", "木", "火", "火", "土", "土", "金", "金", "水"][n % 10]


def relation(a_name: str, a: str, b_name: str, b: str) -> dict:
    """兩格五行的關係：比和、相生、相剋（帶方向）。score：生 +1、比和 0、剋 -1（課程規則）。"""
    if a == b:
        return {"kind": "比和", "text": f"{a_name}{a}與{b_name}{b}比和", "score": 0}
    if SHENG[a] == b:
        return {"kind": "相生", "text": f"{a_name}{a}生{b_name}{b}", "score": 1}
    if SHENG[b] == a:
        return {"kind": "相生", "text": f"{b_name}{b}生{a_name}{a}", "score": 1}
    if KE[a] == b:
        return {"kind": "相剋", "text": f"{a_name}{a}剋{b_name}{b}", "score": -1}
    return {"kind": "相剋", "text": f"{b_name}{b}剋{a_name}{a}", "score": -1}


def _grid(name: str, n: int, formula: str) -> Grid:
    s = n if n <= 81 else (n - 1) % 80 + 1
    return Grid(name, n, s, element_of(n), "陽" if n % 2 else "陰", SHULI[s], formula + (f"；超過 81 減 80 取 {s}" if s != n else ""))


def analyze(full_name: str, rules: Rules | None = None) -> NameChart:
    rules = rules or Rules()
    sur, giv, note = split_name(full_name)
    chars: list[CharInfo] = []
    warnings: list[str] = []
    for role, text in (("姓", sur), ("名", giv)):
        for ch in text:
            info, w = char_strokes(ch, role, rules)
            chars.append(info)
            warnings += w
    S = [c for c in chars if c.role == "姓"]
    G = [c for c in chars if c.role == "名"]
    fmt = lambda cs: "＋".join(f"{c.char}{c.strokes}" for c in cs)  # noqa: E731
    plus = rules.jiashu == "on"

    if len(S) == 1 and plus:
        tian = _grid("天格", S[0].strokes + 1, f"單姓：{fmt(S)}＋假數 1")
    else:
        tian = _grid("天格", sum(c.strokes for c in S), ("複姓：" if len(S) > 1 else "單姓（不加假數）：") + fmt(S))
    ren = _grid("人格", S[-1].strokes + G[0].strokes, f"姓末字＋名首字：{S[-1].char}{S[-1].strokes}＋{G[0].char}{G[0].strokes}")
    if len(G) == 1 and plus:
        di = _grid("地格", G[0].strokes + 1, f"單名：{fmt(G)}＋假數 1")
    else:
        di = _grid("地格", sum(c.strokes for c in G), ("名字筆畫合計：" if len(G) > 1 else "單名（不加假數）：") + fmt(G))
    zong = _grid("總格", sum(c.strokes for c in chars), f"全部筆畫合計（不含假數）：{fmt(chars)}")
    wai_n = tian.number + di.number - ren.number
    wai = _grid("外格", wai_n if wai_n > 0 else 1, f"天格＋地格－人格：{tian.number}＋{di.number}－{ren.number}"
                + ("（得 0，不加假數的單姓單名以 1 計）" if wai_n <= 0 else ""))

    rel = {
        "成功運": relation("天格", tian.element, "人格", ren.element),
        "基礎運": relation("人格", ren.element, "地格", di.element),
        "社交運": relation("人格", ren.element, "外格", wai.element),
    }
    return NameChart(surname=sur, given=giv, split_note=note, chars=chars,
                     grids={"天格": tian, "人格": ren, "地格": di, "外格": wai, "總格": zong},
                     relations=rel, sancai=tian.element + ren.element + di.element, warnings=list(dict.fromkeys(warnings)))
