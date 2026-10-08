"""專科命理師 / The specialist readers — 事業 career · 財運 wealth · 健康 health · 學業 study · 家庭 family.

Same skeleton as fortune/love.py (感情專科), driven by one SPEC per topic:

  classify(topic, question)                   → sub-intent (e.g. career: change | promotion | startup | direction | exam | current)
  natal(topic, charts, male)                  → 命：八字 本題十神／本題宮位／神煞／旺衰, 紫微 本題宮位三方四正, 西洋 本題宮位・主星・相位,
                                                 Jyotiṣa 本題 bhāva・kāraka — each scored with listed reasons
  timing(topic, birth, charts, start, count)  → 運：every year scored from 八字 流年 (本題星透干, 流年與本題宮位合沖, 本題神煞, 喜忌),
                                                 紫微 流年四化入本題宮 + 流年本題宮, 西洋 木土行運對本題行星／宮位, Jyotiṣa daśā — every +/− listed
  extra(topic, charts, male)                  → the topic's own sheet: 事業方向 / 財性與財庫 / 體質與臟腑 / 學習傾向與科系 / 六親宮位
  consult(topic, birth, question, …)          → the whole sitting: natal + this_year (all 13 systems) + timing + extra (+ the reading)

Everything but the prose is deterministic and auditable; each 專科 prompt (prompts/specialist/) is told to read only
from these facts, answer the sub-question first, and never to pronounce fate.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import ephem

from fortune import astro_ext as AX
from fortune import bazi_ext as X
from fortune import casting
from fortune import focus as F
from fortune.birth import BirthInput
from fortune.engines.astrology import astro
from fortune.engines.ziwei import ziwei as ZW
from fortune.love import _SHA, _grade, _male, _verdict
from fortune.schemas import Chart
from fortune.shared.llm import complete

_PROMPTS = Path(__file__).resolve().parent.parent / "prompts" / "specialist"
_B = "子丑寅卯辰巳午未申酉戌亥"
_PALACE_OFFSET = {"命宮": 0, "兄弟": 1, "夫妻": 2, "子女": 3, "財帛": 4, "疾厄": 5, "遷移": 6, "僕役": 7, "官祿": 8, "田宅": 9, "福德": 10, "父母": 11}
_MAJORS = {"紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府", "太陰", "貪狼", "巨門", "天相", "天梁", "七殺", "破軍"}
_LUCKY = {"左輔", "右弼", "文昌", "文曲", "天魁", "天鉞", "祿存"}
_HARM = {"trine", "sextile"}
_HARD = {"square", "opposition"}
_BENEFIC = {"Jupiter", "Venus", "Sun", "Moon", "Mercury"}
_MALEFIC = {"Saturn", "Mars"}
_V_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
_V_MALEFIC = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}
_TOMB = {"木": "未", "火": "戌", "金": "丑", "水": "辰", "土": "辰"}
_ORGAN = {"木": "肝膽、筋、眼", "火": "心、小腸、血脈", "土": "脾胃、消化、肌肉", "金": "肺、大腸、皮膚、呼吸道", "水": "腎、膀胱、骨、耳、泌尿生殖"}
_INDUSTRY = {"木": "教育、文化出版、木材家具、園藝農林、中醫藥、紡織服飾", "火": "能源電力、電子資訊、餐飲、美容、演藝影視、光學",
             "土": "不動產、營建、農牧、土地開發、仲介、管理顧問", "金": "金融、機械、五金汽車、法律、軍警、珠寶、醫療器材",
             "水": "貿易、物流航運、旅遊、媒體傳播、流通零售、飲品水產"}
_MAJOR_FIELD = {"木": "教育、生命科學、文學、環境、中醫", "火": "資訊、電機、藝術設計、傳播、能源", "土": "建築、地質、管理、農業、公共行政",
                "金": "法律、工程、金融、醫學、軍警", "水": "商學、語言、傳播、海洋、流通物流"}
_GOD_STYLE = {"正官": "制度內升遷、公職與管理、守規則的專業", "七殺": "軍警／業務／開創、高壓高回報的專業", "正印": "學術、文書、教育、宗教與照護",
              "偏印": "技術研究、設計、非主流專業、獨立顧問", "食神": "創作、餐飲、藝術、服務與享受型工作", "傷官": "表演、口才、技術專長、自由業",
              "正財": "穩定薪資、會計、製造與實務", "偏財": "投資經商、業務、流通", "比肩": "獨立專業、合夥、自由業", "劫財": "競爭型業務、體育、開拓"}
_ZW_CAREER = {"紫微": "主管／領導／高階幕僚", "天機": "企劃、技術、顧問、宗教哲學", "太陽": "公眾事務、政治、服務人群、能源", "武曲": "金融、軍警、製造、技術",
              "天同": "服務、福利、文創、享樂產業", "廉貞": "公務、法律、科技、電子", "天府": "行政、財務、穩定大機構", "太陰": "不動產、財務、文藝、夜間產業",
              "貪狼": "業務、娛樂、多元斜槓、公關", "巨門": "口才、法律、媒體、教學、研究", "天相": "幕僚、行政、服務、輔佐", "天梁": "醫療、教育、公益、監督審核",
              "七殺": "開創、軍警、高風險專業、外派", "破軍": "改革、開創、技術變革、拆解重建"}
_ZW_MONEY = {"武曲": "正財星，金融、技術生財，理財務實", "天府": "財庫星，善積蓄、守成", "太陰": "積累型，不動產與穩定收益", "貪狼": "偏財、投機與人脈生財，大起大落",
             "破軍": "大進大出，先破後立", "七殺": "勞力與冒險生財", "巨門": "口才、專業知識生財", "天機": "智慧財、企劃與技術", "紫微": "高薪管理、名大於利",
             "天同": "享福小財，不宜投機", "廉貞": "公門財、科技財，忌賭", "天相": "穩定薪資，宜服務業", "天梁": "正派保守，意外之財少", "太陽": "博名不博利，付出型"}
_ZW_ORGAN = {"紫微": "脾胃、頭部", "天機": "肝膽、神經、四肢", "太陽": "心、眼、頭部、血壓", "武曲": "肺、呼吸道、金屬刀傷", "天同": "腎、膀胱、耳、水腫",
             "廉貞": "心血管、血液、婦科", "天府": "脾胃", "太陰": "陰虛、眼、腎、婦科", "貪狼": "肝、泌尿生殖", "巨門": "口腔、腸胃、陰疾",
             "天相": "皮膚、膀胱、泌尿", "天梁": "腸胃、慢性病", "七殺": "肺、外傷、骨", "破軍": "腎、消耗性疾病",
             "擎羊": "外傷、手術", "陀羅": "慢性傷、牙齒骨骼", "火星": "發炎、發燒", "鈴星": "發炎、皮膚", "地空": "虛症", "地劫": "虛症"}
_ZW_FAMILY_GOOD = {"天府", "太陰", "武曲", "紫微", "天同", "天相", "天梁"}

SPECS: dict[str, dict] = {
    "career": {
        "zh": "事業", "en": "career", "title": "事業專科", "master": "事業命理師",
        "stars": ["正官", "七殺"], "stars2": ["正印", "偏印", "食神", "傷官"], "star_zh": "官殺（職位・事業星）",
        "branch_role": "month", "branch_zh": "月支（提綱・事業宮）", "palace": "官祿", "palace2": ["遷移"],
        "zw_good": {"紫微", "天府", "武曲", "太陽", "天相", "天梁", "廉貞"}, "zw_rough": {"破軍", "七殺", "貪狼", "巨門"},
        "houses": [10, 6], "planet": "Saturn", "planet2": "Sun", "house_zh": {10: "十宮（事業宮）", 6: "六宮（工作宮）"},
        "bhavas": [10, 6], "karaka": ["Saturn", "Sun"],
        "good_sha": {"將星": (1, "掌權、適合帶人"), "天乙貴人": (1, "職場貴人"), "國印貴人": (1, "掌印、公職之象"), "華蓋": (0.5, "專技、研究型"), "驛馬": (0, "變動、外派、出差")},
        "bad_sha": {"羊刃": (-0.5, "職場鋒芒易樹敵"), "劫煞": (-0.5, "小人、被奪"), "亡神": (-0.5, "謀事暗中受阻")},
        "intents": {
            "change": {"zh": "轉職／跳槽", "en": "changing jobs", "kw": ["轉職", "跳槽", "換工作", "離職", "辭職", "要不要走", "新工作", "offer", "quit", "resign", "switch", "new job", "leave"]},
            "promotion": {"zh": "升遷／加薪", "en": "promotion", "kw": ["升遷", "升職", "晉升", "加薪", "主管", "升官", "promot", "raise", "manager"]},
            "startup": {"zh": "創業／合夥", "en": "starting a business", "kw": ["創業", "開店", "自己做", "合夥", "開公司", "startup", "business", "found", "partner"]},
            "direction": {"zh": "適合什麼方向", "en": "what direction suits me", "kw": ["適合", "方向", "行業", "什麼工作", "哪種", "天賦", "才能", "suit", "direction", "industry", "what career", "talent"]},
            "exam": {"zh": "考試／公職", "en": "exams / public service", "kw": ["考試", "公職", "國考", "證照", "考公", "exam", "civil service", "license"]},
            "current": {"zh": "目前工作運", "en": "the current job", "kw": []},
        },
        "order": {"change": ["this_year", "timing", "natal", "extra"], "promotion": ["this_year", "timing", "natal", "extra"], "startup": ["natal", "extra", "timing", "this_year"],
                  "direction": ["extra", "natal", "this_year", "timing"], "exam": ["timing", "this_year", "natal", "extra"], "current": ["this_year", "natal", "timing", "extra"]},
    },
    "wealth": {
        "zh": "財運", "en": "wealth", "title": "財運專科", "master": "財運命理師",
        "stars": ["正財", "偏財"], "stars2": ["食神", "傷官"], "star_zh": "財星",
        "branch_role": "tomb", "branch_zh": "財庫", "palace": "財帛", "palace2": ["田宅"],
        "zw_good": {"武曲", "天府", "太陰", "紫微", "天相"}, "zw_rough": {"破軍", "七殺", "貪狼", "巨門", "廉貞"},
        "houses": [2, 8], "planet": "Jupiter", "planet2": "Venus", "house_zh": {2: "二宮（財帛宮）", 8: "八宮（他人之財）"},
        "bhavas": [2, 11], "karaka": ["Jupiter"],
        "good_sha": {"祿神": (1, "祿神：正財穩定"), "天廚貴人": (0.5, "衣食豐足"), "驛馬": (0.5, "動中求財"), "天乙貴人": (0.5, "貴人助財")},
        "bad_sha": {"劫煞": (-1, "劫財、破耗"), "亡神": (-0.5, "暗耗"), "羊刃": (-0.5, "劫財之刃")},
        "intents": {
            "invest": {"zh": "投資／偏財", "en": "investing", "kw": ["投資", "股票", "基金", "偏財", "樂透", "彩券", "加密", "幣", "投機", "invest", "stock", "crypto", "lottery", "trade"]},
            "income": {"zh": "正財／收入", "en": "income / salary", "kw": ["收入", "薪水", "薪資", "加薪", "正財", "賺", "income", "salary", "earn"]},
            "loss": {"zh": "破財／借貸", "en": "losses / debt", "kw": ["破財", "借", "貸", "欠", "負債", "賠", "被騙", "loss", "debt", "loan", "owe", "scam"]},
            "property": {"zh": "買房／置產", "en": "buying property", "kw": ["買房", "房子", "置產", "房貸", "不動產", "property", "house", "mortgage", "real estate"]},
            "partner": {"zh": "合夥／合作", "en": "business partnership", "kw": ["合夥", "合作", "合資", "partner", "joint"]},
            "current": {"zh": "整體財運", "en": "overall wealth", "kw": []},
        },
        "order": {"invest": ["this_year", "timing", "extra", "natal"], "income": ["this_year", "natal", "timing", "extra"], "loss": ["this_year", "timing", "natal", "extra"],
                  "property": ["timing", "this_year", "extra", "natal"], "partner": ["natal", "this_year", "timing", "extra"], "current": ["this_year", "natal", "timing", "extra"]},
    },
    "health": {
        "zh": "健康", "en": "health", "title": "健康專科", "master": "健康命理師",
        "stars": [], "stars2": [], "star_zh": "（健康不看十神，看五行平衡與日主強弱）",
        "branch_role": "day", "branch_zh": "日支（身宮）", "palace": "疾厄", "palace2": ["命宮"],
        "zw_good": set(), "zw_rough": {"廉貞", "貪狼", "巨門", "七殺", "破軍"},
        "houses": [6, 1], "planet": "Sun", "planet2": "Moon", "house_zh": {6: "六宮（健康宮）", 1: "一宮（身體）"},
        "bhavas": [6, 1], "karaka": ["Sun", "Moon"],
        "good_sha": {"天醫": (1, "天醫：近醫藥、易得良醫"), "天德貴人": (0.5, "逢凶化吉"), "月德貴人": (0.5, "逢凶化吉"), "天赦": (0.5, "化解"), "天乙貴人": (0.5, "貴人助")},
        "bad_sha": {"羊刃": (-1, "外傷、手術、血光"), "劫煞": (-0.5, "意外"), "亡神": (-0.5, "暗疾"), "喪門": (-0.5, "白事、情緒低"), "吊客": (-0.5, "白事、情緒低"), "四廢": (-0.5, "氣弱")},
        "intents": {
            "illness": {"zh": "某病／手術", "en": "an illness or surgery", "kw": ["病", "手術", "開刀", "癌", "腫瘤", "檢查", "治療", "illness", "surgery", "cancer", "diagnos", "treatment"]},
            "chronic": {"zh": "慢性／調養", "en": "chronic condition / recovery", "kw": ["慢性", "調養", "恢復", "復原", "體質", "過敏", "免疫", "chronic", "recover", "allergy"]},
            "mental": {"zh": "壓力／睡眠／情緒", "en": "stress, sleep, mood", "kw": ["壓力", "睡", "失眠", "焦慮", "憂鬱", "情緒", "心情", "stress", "sleep", "anxiety", "depress", "burnout", "mood"]},
            "timing": {"zh": "哪年要注意", "en": "which years to watch", "kw": ["哪年", "哪一年", "幾歲", "什麼時候", "今年", "明年", "注意", "which year", "when", "watch"]},
            "current": {"zh": "整體健康", "en": "overall health", "kw": []},
        },
        "order": {"illness": ["this_year", "extra", "natal", "timing"], "chronic": ["extra", "natal", "timing", "this_year"], "mental": ["extra", "this_year", "natal", "timing"],
                  "timing": ["timing", "extra", "natal", "this_year"], "current": ["extra", "this_year", "natal", "timing"]},
    },
    "study": {
        "zh": "學業", "en": "study", "title": "學業專科", "master": "學業命理師",
        "stars": ["正印", "偏印"], "stars2": ["食神", "傷官", "正官"], "star_zh": "印星（學習・文書星）",
        "branch_role": "month", "branch_zh": "月支（提綱）", "palace": "父母", "palace2": ["命宮"],
        "zw_good": {"天機", "巨門", "天梁", "太陽", "紫微", "天相"}, "zw_rough": {"貪狼", "破軍", "七殺"},
        "houses": [3, 9], "planet": "Mercury", "planet2": "Jupiter", "house_zh": {3: "三宮（學習宮）", 9: "九宮（高等教育宮）"},
        "bhavas": [5, 4], "karaka": ["Mercury", "Jupiter"],
        "good_sha": {"文昌貴人": (1.5, "文昌：考運、文書"), "學堂": (1.5, "學堂：讀書緣"), "華蓋": (1, "華蓋：專研、藝術宗教之才"), "天乙貴人": (0.5, "師長貴人"), "太極貴人": (0.5, "玄學哲思"), "驛馬": (0.5, "異地求學、留學")},
        "bad_sha": {"桃花": (-0.5, "分心"), "劫煞": (-0.5, "阻礙"), "羊刃": (-0.5, "浮躁")},
        "intents": {
            "exam": {"zh": "考試／考運", "en": "exams", "kw": ["考試", "考運", "會考", "學測", "指考", "分科", "統測", "研究所", "托福", "雅思", "證照", "exam", "test", "gre", "toefl", "ielts"]},
            "admission": {"zh": "升學／留學", "en": "admission / studying abroad", "kw": ["升學", "留學", "申請", "出國", "學校", "錄取", "admission", "apply", "abroad", "university", "college"]},
            "major": {"zh": "選系／方向", "en": "choosing a major", "kw": ["選系", "科系", "方向", "適合", "念什麼", "讀什麼", "轉系", "major", "field", "suit", "what to study"]},
            "focus": {"zh": "讀不下去／專注", "en": "focus and motivation", "kw": ["讀不下", "專注", "分心", "沒動力", "拖延", "焦慮", "focus", "motivat", "procrastinat", "distract"]},
            "current": {"zh": "整體學運", "en": "overall study luck", "kw": []},
        },
        "order": {"exam": ["timing", "this_year", "natal", "extra"], "admission": ["timing", "this_year", "extra", "natal"], "major": ["extra", "natal", "this_year", "timing"],
                  "focus": ["extra", "natal", "this_year", "timing"], "current": ["this_year", "natal", "timing", "extra"]},
    },
    "family": {
        "zh": "家庭", "en": "family", "title": "家庭專科", "master": "家庭命理師",
        "stars": ["正印", "偏印", "正財", "偏財"], "stars2": ["食神", "傷官", "正官", "七殺"], "star_zh": "六親星（印母・財父）",
        "branch_role": "year", "branch_zh": "年支（父母宮・祖業）", "palace": "田宅", "palace2": ["父母", "子女"],
        "zw_good": _ZW_FAMILY_GOOD, "zw_rough": {"破軍", "七殺", "貪狼", "廉貞"},
        "houses": [4, 5], "planet": "Moon", "planet2": "Saturn", "house_zh": {4: "四宮（家庭宮）", 5: "五宮（子女宮）"},
        "bhavas": [4, 5], "karaka": ["Moon", "Jupiter"],
        "good_sha": {"紅鸞": (1, "家有喜事"), "天喜": (1, "家有喜事、添丁"), "天乙貴人": (0.5, "長輩助力"), "天德貴人": (0.5, "家宅安")},
        "bad_sha": {"喪門": (-1, "長輩健康、白事"), "吊客": (-1, "長輩健康、白事"), "孤辰": (-0.5, "與家人疏離"), "寡宿": (-0.5, "與家人疏離"), "劫煞": (-0.5, "家宅不寧")},
        "intents": {
            "parents": {"zh": "父母／長輩", "en": "parents and elders", "kw": ["父母", "爸", "媽", "爸爸", "媽媽", "長輩", "父親", "母親", "公婆", "岳", "parent", "father", "mother", "elder", "in-law"]},
            "children": {"zh": "子女／懷孕", "en": "children / pregnancy", "kw": ["子女", "小孩", "孩子", "懷孕", "生子", "求子", "添丁", "兒子", "女兒", "child", "kid", "pregnan", "baby", "son", "daughter"]},
            "home": {"zh": "搬家／住處", "en": "moving / the home", "kw": ["搬家", "搬", "住", "房子", "住處", "遷", "移民", "move", "moving", "home", "relocat", "emigrat"]},
            "siblings": {"zh": "兄弟姊妹", "en": "siblings", "kw": ["兄弟", "姊妹", "姐妹", "哥", "弟", "姊", "妹", "sibling", "brother", "sister"]},
            "harmony": {"zh": "家庭和睦／衝突", "en": "family harmony", "kw": ["和睦", "吵", "衝突", "相處", "關係", "不合", "家運", "harmony", "conflict", "fight", "get along"]},
            "current": {"zh": "整體家運", "en": "overall family luck", "kw": []},
        },
        "order": {"parents": ["extra", "this_year", "timing", "natal"], "children": ["timing", "extra", "natal", "this_year"], "home": ["timing", "this_year", "extra", "natal"],
                  "siblings": ["extra", "natal", "this_year", "timing"], "harmony": ["this_year", "natal", "extra", "timing"], "current": ["this_year", "natal", "timing", "extra"]},
    },
}
TOPICS = list(SPECS)


def spec(topic: str) -> dict:
    if topic not in SPECS:
        raise ValueError(f"unknown specialist topic {topic!r}; one of {', '.join(TOPICS)} (love → fortune.love)")
    return SPECS[topic]


# --- the question ---------------------------------------------------------------------------

def classify(topic: str, question: str | None) -> str:
    """Sub-intent of a question inside one 專科."""
    s = spec(topic)
    if not question:
        return "current"
    q = question.lower()
    best, score = "current", 0
    for key, t in s["intents"].items():
        n = sum(1 for k in t["kw"] if k.lower() in q)
        if n > score:
            best, score = key, n
    return best


def intent_label(topic: str, intent: str) -> str:
    t = spec(topic)["intents"].get(intent) or spec(topic)["intents"]["current"]
    return f"{t['zh']} / {t['en']}"


def route(question: str | None) -> str:
    """Which 專科 a free question belongs to (love included): the focus classifier's topic, `general` → career."""
    t = F.classify(question)
    return t if t in SPECS or t == "love" else "career"


# --- helpers ---------------------------------------------------------------------------------

def _bare(s: str) -> str:
    return s.split("(")[0]


def _elem_of_stem(ch: str) -> str:
    return X.STEM_ELEM[X.STEMS.index(ch)]


def _god_elems(dm_elem: str) -> dict[str, str]:
    """Element of each ten-god family for this day master."""
    return {"財": X.KE[dm_elem], "官": X._CTRL_OF[dm_elem], "印": X._GEN_OF[dm_elem], "食傷": X.SHENG[dm_elem], "比劫": dm_elem}


def _element_tally(pillars: list[dict]) -> dict[str, float]:
    tally = {e: 0.0 for e in "木火土金水"}
    for p in pillars:
        tally[p["stem_elem"]] += 1.0
        for i, h in enumerate(p.get("hidden", [])):
            tally[_elem_of_stem(h["stem"])] += 1.0 if i == 0 else 0.4
    return {k: round(v, 1) for k, v in tally.items()}


def _topic_branch(s: dict, full: dict) -> tuple[int, str]:
    """The 八字 branch that stands for the topic (事業→月支, 健康→日支, 家庭→年支, 財運→財庫)."""
    pillars = full["pillars"]
    role = s["branch_role"]
    if role == "tomb":
        tomb = _TOMB[_god_elems(full["strength"]["dm_elem"])["財"]]
        return _B.index(tomb), "財庫"
    idx = {"year": 0, "month": 1, "day": 2, "hour": 3}[role]
    return pillars[idx]["branch_idx"], s["branch_zh"]


def _relation(a: int, b: int) -> tuple[str, float]:
    """Branch relation of a (流年 / other) against b (the topic branch): (name, weight)."""
    lo, hi = sorted((a, b))
    if (a - b) % 12 == 6:
        return "沖", -1.5
    if (lo, hi) in X._LIUHE:
        return "六合", 1
    if X._SANHE_GROUP.get(a) == X._SANHE_GROUP.get(b) and a != b:
        return "三合", 0.8
    if (lo, hi) in X._HAI:
        return "害", -0.5
    if {lo, hi} == {0, 3} or (a == b and a in X._ZIXING):
        return "刑", -0.7
    if a == b:
        return "伏吟", -0.3
    return "", 0


def _stars_of(p: dict) -> str:
    return "、".join(p.get("stars", [])) or "空宮"


# --- 命：natal disposition -------------------------------------------------------------------

def _bazi_natal(topic: str, c: dict, male: bool | None) -> dict:
    s = spec(topic)
    pillars = c["pillars"]
    st = c.get("strength", {})
    dm_elem = st.get("dm_elem", pillars[2]["stem_elem"])
    ge = _god_elems(dm_elem)
    score, reasons = 0.0, []
    stars, stars2 = list(s["stars"]), list(s["stars2"])
    if topic == "family":
        child = ["食神", "傷官"] if male is False else ["正官", "七殺"] if male else ["食神", "傷官", "正官", "七殺"]
        stars2 = child
    seen = [f"{p['pillar']}干{p['stem']}（{p['stem_god']}）" for p in pillars if p.get("stem_god") in stars]
    seen += [f"{p['pillar']}支藏{h['stem']}（{h['god']}）" for p in pillars for h in p.get("hidden", []) if h["god"] in stars]
    transparent = [p for p in pillars if p.get("stem_god") in stars and p["role"] != "day"]
    bi, bzh = _topic_branch(s, c)
    tally = _element_tally(pillars)
    strong = st.get("strong")
    if stars:
        if transparent:
            score += 1
            reasons.append(f"{s['star_zh']}透干（{'、'.join(p['pillar'] + '干' + p['stem_god'] for p in transparent)}）→ 本題在命中明顯、容易被看見")
        elif seen:
            score += 0.5
            reasons.append(f"{s['star_zh']}藏於地支（{'、'.join(seen[:3])}）→ 有根基，發揮需行運引動")
        else:
            score -= 1
            reasons.append(f"原局不見{s['star_zh']} → 需靠行運與後天努力，起步較慢")
        if len(seen) >= 4 and topic != "family":
            score -= 0.5
            reasons.append(f"{s['star_zh']}多見（{len(seen)} 處）→ 多頭、分散或壓力大")
    gods = [p.get("stem_god") for p in pillars if p["role"] != "day"] + [h["god"] for p in pillars for h in p.get("hidden", [])[:1]]
    # topic-specific structure
    if topic == "career":
        if "正官" in gods and ("正印" in gods or "偏印" in gods):
            score += 1
            reasons.append("官印相生 → 制度內升遷、名位之象")
        if "七殺" in gods and ("食神" in gods or "傷官" in gods):
            score += 0.5
            reasons.append("食傷制殺 → 以專業駕馭壓力、適合開創")
        if "傷官" in gods and "正官" in gods:
            score -= 1
            reasons.append("傷官見官 → 與制度、上司易衝撞，宜專業或自由業")
        if not strong and "七殺" in gods and not ("正印" in gods or "偏印" in gods):
            score -= 1
            reasons.append("身弱七殺無印化 → 工作壓力大、易被事業消耗")
    elif topic == "wealth":
        cai = [g for g in gods if g in ("正財", "偏財")]
        if cai and strong:
            score += 1
            reasons.append("身強能任財 → 財來能守、可承擔較大財務規模")
        elif cai and not strong and len(cai) >= 2:
            score -= 1
            reasons.append("身弱財多（富屋貧人）→ 財來財去、忌貪大，宜穩定正財")
        if ("食神" in gods or "傷官" in gods) and cai:
            score += 1
            reasons.append("食傷生財 → 以才華、技術、口才生財，財源有根")
        if gods.count("比肩") + gods.count("劫財") >= 2:
            score -= 1
            reasons.append("比劫重 → 劫財之象：合夥、借貸、朋友分利需謹慎")
        tomb = _B[bi]
        if any(p["branch"] == tomb for p in pillars):
            score += 0.5
            reasons.append(f"原局有財庫（{tomb}）→ 善積蓄、逢沖開庫之年財動")
    elif topic == "health":
        missing = [e for e, v in tally.items() if v == 0]
        dominant = max(tally, key=tally.get)
        if missing:
            score -= 0.5 * len(missing)
            reasons.append(f"五行缺{'、'.join(missing)} → {'；'.join(_ORGAN[e] for e in missing)} 相對薄弱，宜保養")
        if tally[dominant] >= 4:
            score -= 0.5
            reasons.append(f"{dominant}過旺（{tally[dominant]}）→ {_ORGAN[dominant]}易失衡；被{dominant}所剋的{X.KE[dominant]}（{_ORGAN[X.KE[dominant]]}）受壓")
        if st.get("cong"):
            reasons.append("從格 → 體質偏向單一五行，順其勢而養")
        elif strong:
            score += 1
            reasons.append(f"日主{st.get('day_master', '')}身強 → 元氣足、恢復力好，忌過勞與飲食過度")
        else:
            score -= 0.5
            reasons.append(f"日主{st.get('day_master', '')}身弱 → 元氣易耗，作息與睡眠是根本")
        if st.get("tiaohou"):
            reasons.append(f"調候：{st.get('tiaohou_note', '')}")
        if "七殺" in gods and not strong:
            score -= 1
            reasons.append("身弱逢七殺 → 壓力型體質，易因操勞、緊張而生病")
    elif topic == "study":
        yin = [g for g in gods if g in ("正印", "偏印")]
        shi = [g for g in gods if g in ("食神", "傷官")]
        if yin and shi:
            score += 0.5
            reasons.append("印與食傷並見 → 既能吸收也能輸出，學以致用")
        if yin and "正官" in gods:
            score += 1
            reasons.append("官印相生 → 考運、功名之象，制度內考試有利")
        if any(g in ("正財", "偏財") for g in gods) and yin and strong is False:
            score -= 1
            reasons.append("財壞印（身弱）→ 易被外務、打工、感情分心")
        if "偏印" in yin and "食神" in shi:
            score -= 0.5
            reasons.append("梟神奪食 → 想得多、做得慢，需固定輸出習慣")
    elif topic == "family":
        yr, hr = pillars[0], pillars[3]
        rel, w = _relation(yr["branch_idx"], pillars[2]["branch_idx"])
        if rel == "沖":
            score -= 1
            reasons.append(f"年支{yr['branch']}沖日支{pillars[2]['branch']} → 與父母緣分或距離較遠，早離家、各過各的")
        elif rel in ("六合", "三合"):
            score += 1
            reasons.append(f"年支{yr['branch']}{rel}日支 → 與原生家庭親近、長輩助力")
        if c.get("time_known", True):
            relh, wh = _relation(hr["branch_idx"], pillars[2]["branch_idx"])
            if relh == "沖":
                score -= 1
                reasons.append(f"時支{hr['branch']}沖日支 → 子女宮動，與子女聚少或晚得子")
            elif relh in ("六合", "三合"):
                score += 1
                reasons.append(f"時支{hr['branch']}{relh}日支 → 子女緣厚、晚年有靠")
            if hr.get("stem_god") in stars2 or any(h["god"] in stars2 for h in hr.get("hidden", [])[:1]):
                score += 1
                reasons.append(f"子女星入時柱（{hr['gz']}）→ 子女緣分明顯")
        if any(g in ("正印", "偏印") for g in gods):
            score += 0.5
            reasons.append("印星現 → 母緣、長輩庇蔭")
        if any(g in ("正財", "偏財") for g in gods):
            score += 0.3
            reasons.append("財星現 → 父緣、家中經濟有根")
    # the topic branch: 合／沖 from the other pillars
    if s["branch_role"] != "tomb":
        others = [p for p in pillars if p["branch_idx"] != bi or p["role"] != s["branch_role"]]
        for p in others:
            if p["role"] == s["branch_role"]:
                continue
            rel, w = _relation(p["branch_idx"], bi)
            if rel in ("沖", "六合"):
                score += w * 0.6
                reasons.append(f"{bzh}逢{p['pillar']}支{p['branch']}{rel} → {'本題根基動搖、多變動' if rel == '沖' else '本題有助力、穩'}")
    # 神煞
    all_sha = [x for p in pillars for x in p.get("shensha", [])]
    good = [(x, s["good_sha"][x]) for x in dict.fromkeys(all_sha) if x in s["good_sha"]]
    bad = [(x, s["bad_sha"][x]) for x in dict.fromkeys(all_sha) if x in s["bad_sha"]]
    for x, (w, why) in good:
        score += w
        reasons.append(f"神煞 {x} → {why}")
    for x, (w, why) in bad:
        score += w
        reasons.append(f"神煞 {x} → {why}")
    # 喜用
    fav = st.get("favourable", [])
    if stars and fav:
        star_elem = ge["官"] if topic == "career" else ge["財"] if topic == "wealth" else ge["印"] if topic in ("study", "family") else None
        if star_elem in fav:
            score += 1
            reasons.append(f"{s['star_zh'][:2]}五行（{star_elem}）為喜用 → 本題是此命的順風面")
        elif star_elem in st.get("avoid", []):
            score -= 0.5
            reasons.append(f"{s['star_zh'][:2]}五行（{star_elem}）為忌神 → 本題需付出較多才有回報")
    facts = {
        "日主": f"{st.get('day_master', '')}{dm_elem}・{st.get('label', '')}・格局 {st.get('pattern', '')}",
        "本題星": s["star_zh"], "本題星所在": seen or "原局未見", bzh: _B[bi],
        "十神（干＋本氣）": "、".join(g for g in gods if g), "五行": tally,
        "神煞": [x for x, _ in good + bad] or "無", "喜用／忌": f"喜 {'/'.join(fav)}・忌 {'/'.join(st.get('avoid', []))}・用神 {st.get('yongshen', '')}（{st.get('yongshen_why', '')}）",
    }
    return {"system": "bazi", "system_zh": "八字", "score": round(score, 1), "verdict": _verdict(score), "reasons": reasons, "facts": facts}


def _ziwei_natal(topic: str, c: dict) -> dict:
    s = spec(topic)
    palaces = c.get("palaces", [])
    by_name = {p["name"]: p for p in palaces}
    by_branch = {p["branch"]: p for p in palaces}
    pal = by_name.get(s["palace"])
    if not pal:
        return {"system": "ziwei", "system_zh": "紫微", "score": 0, "verdict": "neutral", "reasons": [f"無{s['palace']}宮"], "facts": {}}
    bi = _B.index(pal["branch"])
    opp = by_branch[_B[(bi + 6) % 12]]
    trine = [by_branch[_B[(bi + 4) % 12]], by_branch[_B[(bi + 8) % 12]]]
    life = by_name.get("命宮", {})
    majors = [_bare(x) for x in pal.get("stars", []) if _bare(x) in _MAJORS]
    score, reasons = 0.0, []
    name = s["palace"] + ("宮" if not s["palace"].endswith("宮") else "")
    if not majors:
        bm = [_bare(x) for x in opp.get("stars", []) if _bare(x) in _MAJORS]
        reasons.append(f"{name}無主星，借對宮{opp['name']}（{'、'.join(bm) or '空'}）→ 本題受外在環境與他人影響較大")
        majors = bm
        score -= 0.5
    good = [m for m in majors if m in s["zw_good"]]
    rough = [m for m in majors if m in s["zw_rough"]]
    if good:
        score += 1
        reasons.append(f"{name}主星 {'、'.join(good)} → " + {"career": "事業有格局、穩中求進", "wealth": "財星入財宮，聚財守財", "health": "", "study": "學習有耐性、文書之才", "family": "家宅安穩、田產有根"}[topic])
    if rough:
        score -= 1 if topic != "health" else 0.5
        reasons.append(f"{name}主星 {'、'.join(rough)} → " + {"career": "事業起伏大、適合開創或變動型工作", "wealth": "財來財去、大進大出，忌投機", "health": f"注意 {'、'.join(_ZW_ORGAN.get(m, '') for m in rough)}", "study": "坐不住、需動手型學習", "family": "家中變動多、離家發展"}[topic])
    tags = {_bare(x): x[x.find("(") + 1:-1] for x in pal.get("stars", []) if "(" in x}
    if "祿" in tags.values():
        score += 1
        reasons.append(f"生年化祿在{name}（{next(k for k, v in tags.items() if v == '祿')}）→ 本題得福、有財有緣")
    if "權" in tags.values():
        score += 0.5
        reasons.append(f"生年化權在{name} → 本題有主導權、能掌控")
    if "科" in tags.values():
        score += 0.5
        reasons.append(f"生年化科在{name} → 本題有名聲、貴人")
    if "忌" in tags.values():
        score -= 1.5
        reasons.append(f"生年化忌在{name}（{next(k for k, v in tags.items() if v == '忌')}）→ 本題是此生功課，多糾結、需耐心")
    sha = [_bare(x) for x in pal.get("stars", []) if _bare(x) in _SHA]
    if len(sha) >= 2:
        score -= 1
        reasons.append(f"{name}煞星 {'、'.join(sha)} → " + ("外傷、手術、發炎之象，宜定期檢查" if topic == "health" else "本題多磨、宜慢"))
    elif sha:
        score -= 0.5
        reasons.append(f"{name}見{sha[0]} → " + (f"注意 {_ZW_ORGAN.get(sha[0], '')}" if topic == "health" else "本題有一項持續的摩擦"))
    lucky = [_bare(x) for x in pal.get("stars", []) if _bare(x) in _LUCKY]
    if lucky:
        score += 0.5 * min(2, len(lucky))
        reasons.append(f"{name}見吉曜 {'、'.join(lucky)} → 貴人、助力")
    if topic == "study":
        wen = [n for n in ("文昌", "文曲") if c.get("star_palace", {}).get(n) in {"命宮", s["palace"], opp["name"], *[p["name"] for p in trine]} or c.get("star_palace", {}).get(n) == "命宮"]
        if wen:
            score += 1
            reasons.append(f"{'、'.join(wen)}入命宮或父母宮三方 → 文星照命，讀書考試有利")
        if "科" in {x[x.find('(') + 1:-1] for x in life.get("stars", []) if "(" in x}:
            score += 1
            reasons.append("生年化科入命宮 → 名聲、考運")
    if topic == "wealth":
        lu = c.get("star_palace", {}).get("祿存")
        if lu in (s["palace"], "命宮", "田宅", opp["name"]):
            score += 1
            reasons.append(f"祿存在{lu} → 財祿有根")
    if topic == "family":
        for pn in ("父母", "子女"):
            pp = by_name.get(pn, {})
            sha_p = [_bare(x) for x in pp.get("stars", []) if _bare(x) in _SHA]
            if len(sha_p) >= 2:
                score -= 0.5
                reasons.append(f"{pn}宮見{'、'.join(sha_p)} → 與{'長輩' if pn == '父母' else '子女'}緣分需經營")
            if "忌" in {x[x.find('(') + 1:-1] for x in pp.get("stars", []) if "(" in x}:
                score -= 0.5
                reasons.append(f"生年化忌入{pn}宮 → {'長輩' if pn == '父母' else '子女'}是此生牽掛")
    facts = {
        name: f"{pal['stem']}{pal['branch']}：{_stars_of(pal)}", "亮度": pal.get("brightness") or "—", "雜曜": pal.get("adjective_stars") or "—",
        f"對宮（{opp['name']}）": _stars_of(opp), "三方": {p["name"]: _stars_of(p) for p in trine},
        **{f"{pn}宮": _stars_of(by_name.get(pn, {})) for pn in s["palace2"]},
        "命宮": _stars_of(life), "身宮": next((p["name"] for p in palaces if p.get("is_body")), ""),
    }
    return {"system": "ziwei", "system_zh": "紫微", "score": round(score, 1), "verdict": _verdict(score), "reasons": reasons, "facts": facts}


def _astro_natal(topic: str, ch: Chart) -> dict:
    s = spec(topic)
    c = ch.chart
    planets = {p["body"]: p for p in c.get("planets", [])}
    asp = c.get("aspects_detail", [])
    score, reasons = 0.0, []
    pl = s["planet"]
    def aspects_of(body):
        return [x for x in asp if body in (x["a"], x["b"])]
    pa = aspects_of(pl)
    harm = [x for x in pa if x["type"] in _HARM or (x["type"] == "conjunction" and ({x["a"], x["b"]} - {pl}) <= {"Jupiter", "Venus", "Sun", "Moon"})]
    hard = [x for x in pa if x["type"] in _HARD or (x["type"] == "conjunction" and ({x["a"], x["b"]} - {pl}) <= {"Saturn", "Mars"} and pl not in ("Saturn", "Mars"))]
    pl_zh = {"Saturn": "土星（事業・結構）", "Jupiter": "木星（財富・擴張）", "Sun": "太陽（活力）", "Mercury": "水星（學習・思考）", "Moon": "月亮（家庭・情感）"}[pl]
    for x in harm:
        other = x["b"] if x["a"] == pl else x["a"]
        score += 1 if other in ("Jupiter", "Sun", "Venus") else 0.5
        reasons.append(f"{pl} {x['type']} {other}（{x['orb']}°）→ {pl_zh[:2]}得助，本題順")
    for x in hard:
        other = x["b"] if x["a"] == pl else x["a"]
        score -= 1 if other == "Saturn" else 0.5
        reasons.append(f"{pl} {x['type']} {other}（{x['orb']}°）→ 本題有結構性張力，需以紀律化解")
    if ch.ascendant:
        cusps = {h["house"]: h for h in ch.ascendant.get("houses", [])}
        h1 = s["houses"][0]
        ruler = F._RULER.get(cusps.get(h1, {}).get("sign", ""))
        rp = planets.get(ruler)
        inh = {h: [p for p in planets.values() if p.get("house") == h] for h in s["houses"]}
        for h, ps in inh.items():
            if not ps:
                continue
            names = "、".join(p["body"] for p in ps)
            ben = [p for p in ps if p["body"] in _BENEFIC]
            mal = [p for p in ps if p["body"] in _MALEFIC]
            if ben:
                score += 1 if h == h1 else 0.5
            if mal:
                score -= 0.5 if topic != "career" or any(p["body"] == "Mars" for p in mal) else 0
            why = {"career": "事業是人生重心" if ben else "事業靠承擔與長期累積", "wealth": "財運有來源" if ben else "理財需紀律、忌衝動",
                   "health": "體質有護持" if ben else "注意發炎、過勞與慢性病", "study": "學習有興趣與助力" if ben else "學習要靠自律、慢工",
                   "family": "家庭是支持來源" if ben else "家中責任重、早熟"}[topic]
            reasons.append(f"{s['house_zh'][h]}有 {names} → {why}")
        if rp:
            r_asp = aspects_of(ruler)
            hc, dc = sum(1 for x in r_asp if x["type"] in _HARM), sum(1 for x in r_asp if x["type"] in _HARD)
            score += 0.5 if hc > dc else -0.5 if dc > hc else 0
            reasons.append(f"{s['house_zh'][h1][:2]}主 {ruler} 在 {rp['sign']} 第{rp.get('house')}宮（和諧{hc}／緊張{dc}）")
        facts_h = {s["house_zh"][h]: f"{cusps.get(h, {}).get('sign')} {cusps.get(h, {}).get('sign_zh', '')}；內有 " + ("、".join(f"{p['body']} {p['sign']}" for p in inh[h]) or "空") for h in s["houses"]}
        facts_h["宮主"] = f"{ruler} in {rp['sign']} H{rp.get('house')}" if rp else "—"
    else:
        facts_h = {"註": "無時辰／出生地，無宮位：只看行星與相位"}
    p1, p2 = planets.get(pl), planets.get(s["planet2"])
    facts = {pl_zh: f"{p1['sign']} {p1['sign_zh']}" + (f" H{p1['house']}" if p1.get("house") else "") if p1 else "—",
             s["planet2"]: f"{p2['sign']} {p2['sign_zh']}" + (f" H{p2['house']}" if p2.get("house") else "") if p2 else "—",
             f"{pl} 相位": [f"{x['a']} {x['type']} {x['b']} ({x['orb']}°)" for x in pa] or "無", **facts_h}
    return {"system": "astrology", "system_zh": "西洋占星", "score": round(score, 1), "verdict": _verdict(score), "reasons": reasons, "facts": facts}


def _jyotish_natal(topic: str, ch: Chart) -> dict:
    s = spec(topic)
    grahas = {g["graha"]: g for g in ch.chart.get("grahas", [])}
    score, reasons = 0.0, []
    facts = {"現行 daśā": f"{ch.readings.get('mahadasha_lord')}（{ch.readings.get('dasha_nature')}）", "月宿": ch.readings.get("moon_nakshatra"),
             "kāraka": "、".join(f"{k} in {grahas[k]['rashi']} B{grahas[k].get('bhava')}" for k in s["karaka"] if k in grahas)}
    lord = None
    if ch.ascendant:
        hs = {h["house"]: h["rashi"] for h in ch.ascendant.get("houses", [])}
        b1 = s["bhavas"][0]
        lord = F._VEDIC_RULER.get(hs.get(b1, ""))
        lp = grahas.get(lord)
        for b in s["bhavas"]:
            inb = [g for g in grahas.values() if g.get("bhava") == b]
            facts[f"第{b} bhāva"] = f"{hs.get(b)}；內有 {'、'.join(g['graha'] for g in inb) or '無'}"
            mal = [g["graha"] for g in inb if g["graha"] in _V_MALEFIC]
            ben = [g["graha"] for g in inb if g["graha"] in _V_BENEFIC]
            if mal:
                if topic == "health" and b == 6:
                    score += 0.5
                    reasons.append(f"第6 bhāva 見 {'、'.join(mal)} → 傳統視為能克病敵，但體質偏燥，注意發炎")
                else:
                    score -= 0.5
                    reasons.append(f"第{b} bhāva 見 {'、'.join(mal)} → 本題需審慎、晚成")
            if ben:
                score += 0.5
                reasons.append(f"第{b} bhāva 見吉曜 {'、'.join(ben)} → 本題有福")
        if lp:
            facts[f"B{b1} 主"] = f"{lord} in {lp['rashi']} B{lp.get('bhava')}"
            if lp.get("bhava") in (6, 8, 12):
                score -= 1
                reasons.append(f"第{b1} bhāva 主 {lord} 落 dusthāna B{lp['bhava']} → 本題多波折、需加倍經營")
            elif lp.get("bhava") in (1, 4, 5, 7, 9, 10, 11):
                score += 1
                reasons.append(f"第{b1} bhāva 主 {lord} 落 B{lp['bhava']}（吉位）→ 本題有支撐")
    else:
        facts["註"] = "無時辰／出生地，無 bhāva：只看 kāraka 與 daśā"
    for k in s["karaka"]:
        g = grahas.get(k)
        if g and g.get("bhava") in (6, 8, 12):
            score -= 0.5
            reasons.append(f"kāraka {k} 落 B{g['bhava']} → 本題付出多、回報慢")
    return {"system": "jyotish", "system_zh": "Jyotiṣa", "score": round(score, 1), "verdict": _verdict(score), "reasons": reasons, "facts": facts, "lord": lord}


def _name_topic(obj, zh: str):
    """Replace the generic 本題 with the topic's own name everywhere in a result (keys and strings)."""
    if isinstance(obj, str):
        return obj.replace("本題", zh)
    if isinstance(obj, list):
        return [_name_topic(x, zh) for x in obj]
    if isinstance(obj, dict):
        return {_name_topic(k, zh): _name_topic(v, zh) for k, v in obj.items()}
    return obj


def natal(topic: str, charts: dict[str, Chart], male: bool | None) -> dict:
    """命：the four systems with a natal 本題宮位, each scored on the topic."""
    rows = []
    if "bazi" in charts:
        rows.append(_bazi_natal(topic, charts["bazi"].chart, male))
    if "ziwei" in charts:
        rows.append(_ziwei_natal(topic, charts["ziwei"].chart))
    if "astrology" in charts:
        rows.append(_astro_natal(topic, charts["astrology"]))
    if "jyotish" in charts:
        rows.append(_jyotish_natal(topic, charts["jyotish"]))
    rows = _name_topic(rows, spec(topic)["zh"])
    total = sum(r["score"] for r in rows)
    g, label = _grade(total)
    return {"systems": rows, "score": round(total, 1), "grade": g, "label": label,
            "summary": f"命中{spec(topic)['zh']}格局：" + "；".join(f"{r['system_zh']}{F.VERDICT_ZH[r['verdict']]}" for r in rows) + f" → 合計 {total:+.1f}（{label}）"}


# --- 運：the years ---------------------------------------------------------------------------

def _bazi_year(topic: str, full: dict, yr: int, male: bool | None) -> tuple[list[dict], dict | None]:
    s = spec(topic)
    ln = next((l for d in full["dayun"] for l in d["liunian"] if l["year"] == yr), None)
    dy = next((d for d in full["dayun"] if d["start_year"] <= yr <= d["end_year"]), None)
    if not ln:
        return [], None
    st = full["strength"]
    strong = st.get("strong")
    stars, stars2 = list(s["stars"]), list(s["stars2"])
    if topic == "family":
        stars2 = ["食神", "傷官"] if male is False else ["正官", "七殺"] if male else ["食神", "傷官", "正官", "七殺"]
    bi, bzh = _topic_branch(s, full)
    lb = _B.index(ln["gz"][1])
    rs: list[dict] = []
    def add(delta, text):
        rs.append({"src": "八字", "delta": delta, "text": text})
    god = ln["stem_god"]
    hid = ln["hidden"][0]["god"] if ln["hidden"] else ""
    if topic == "career":
        if god in stars:
            add(2 if strong or any(g in ("正印", "偏印") for g in (dy or {}).get("stem_god", "") ) else 1, f"流年{ln['gz']}透{god} → 職務、名位變化：升遷或換位之應" + ("" if strong else "（身弱，壓力同來）"))
        elif hid in stars:
            add(1, f"流年支{ln['gz'][1]}藏{hid} → 工作機會暗動，需主動爭取")
        if god in ("正印", "偏印"):
            add(1, f"流年透{god} → 貴人、文書、考試、進修有利")
        if god in ("食神", "傷官"):
            add(0.5 if god == "食神" else -0.5, f"流年透{god} → {'才華展現、適合創作與提案' if god == '食神' else '想法多、與上司易衝突，適合自立或專業'}")
        if god in ("正財", "偏財"):
            add(0.5, f"流年透{god} → 財生官，業績、業務有利")
        if god in ("比肩", "劫財"):
            add(-0.5, f"流年透{god} → 競爭者多、合夥需明算")
    elif topic == "wealth":
        if god in stars:
            add(2 if strong else 1, f"流年{ln['gz']}透{god} → 財星現，{'進財之年' if strong else '財來但身弱難守，宜穩不宜貪'}")
        elif hid in stars:
            add(1, f"流年支{ln['gz'][1]}藏{hid} → 暗財、小財")
        if god in ("食神", "傷官"):
            add(1, f"流年透{god} → 食傷生財，才藝、業務、副業有進")
        if god in ("比肩", "劫財"):
            add(-1.5, f"流年透{god} → 劫財：破耗、借貸、合夥分利，忌投機")
        if god in ("正印", "偏印"):
            add(-0.5, f"流年透{god} → 印剋食傷，財源放慢，宜守成進修")
        if god in ("正官", "七殺"):
            add(0.3, f"流年透{god} → 官護財，穩定但支出多")
        if (lb - bi) % 12 == 6:
            add(1.5 if strong else -1, f"流年{_B[lb]}沖財庫{_B[bi]} → {'財庫開，大進大出，適合動用資金' if strong else '庫被沖，破財或不得已的大支出'}")
    elif topic == "health":
        ln_elem = _elem_of_stem(ln["gz"][0])
        if ln_elem in st.get("avoid", []):
            add(-1, f"流年{ln['gz']}天干{ln_elem}為忌神 → {_ORGAN[ln_elem]} 相關負擔加重")
        if god == "七殺" and not strong:
            add(-1.5, "流年七殺攻身（身弱）→ 壓力、過勞、意外之年，當減量")
        if god in ("正印", "偏印") and not strong:
            add(1, f"流年透{god}生身 → 元氣回補、適合調養治療")
        if god in ("食神", "傷官") and not strong:
            add(-0.5, f"流年透{god}洩身 → 體力消耗、注意腸胃與睡眠")
        rel, w = _relation(lb, full["pillars"][2]["branch_idx"])
        if rel == "沖":
            add(-1, f"流年{_B[lb]}沖日支{full['pillars'][2]['branch']} → 身體動，注意舊疾、手術、出行安全")
        rel_y, _ = _relation(lb, full["pillars"][0]["branch_idx"])
        if rel_y == "沖":
            add(-0.5, f"流年{_B[lb]}沖年支（太歲相沖）→ 本命受擾，宜安太歲、定期檢查")
        elif lb == full["pillars"][0]["branch_idx"]:
            add(-0.3, "流年伏吟年支（值太歲）→ 宜靜不宜動")
    elif topic == "study":
        if god in stars:
            add(2, f"流年{ln['gz']}透{god} → 印星：吸收力強、考運與文書之年")
        elif hid in stars:
            add(1, f"流年支{ln['gz'][1]}藏{hid} → 學習有根，需規律")
        if god == "正官":
            add(1, "流年透正官 → 官印相生之應，制度內考試有利")
        if god in ("食神", "傷官"):
            add(0.5, f"流年透{god} → 表達與創作佳，口試、作品集有利")
        if god in ("正財", "偏財"):
            add(-1, f"流年透{god} → 財壞印：外務、打工、感情分心")
        if god == "七殺":
            add(-0.5, "流年透七殺 → 壓力大、競爭激烈")
    elif topic == "family":
        if god in stars2:
            add(1.5, f"流年{ln['gz']}透{god}（子女星）→ 添丁、子女之事有動")
        if god in ("正印", "偏印"):
            add(0.5, f"流年透{god}（母星）→ 長輩、母親相關之事")
        if god in ("正財", "偏財"):
            add(0.3, f"流年透{god}（父星）→ 父親、家中經濟相關")
        rel_y, _ = _relation(lb, full["pillars"][0]["branch_idx"])
        if rel_y == "沖":
            add(-1, f"流年{_B[lb]}沖年支{full['pillars'][0]['branch']} → 家宅動：搬遷、長輩健康或家庭變化")
        elif rel_y in ("六合", "三合"):
            add(0.8, f"流年{_B[lb]}{rel_y}年支 → 家人和睦、長輩有助")
        if full.get("time_known", True):
            rel_h, _ = _relation(lb, full["pillars"][3]["branch_idx"])
            if rel_h == "沖":
                add(-0.8, f"流年{_B[lb]}沖時支（子女宮）→ 子女變動、聚少離多或懷孕需護")
            elif rel_h in ("六合", "三合"):
                add(0.8, f"流年{_B[lb]}{rel_h}時支（子女宮）→ 子女緣、添丁或子女喜事")
    if s["branch_role"] in ("month", "day") and topic != "health":
        rel, w = _relation(lb, bi)
        if rel:
            add(round(w, 1), f"流年{_B[lb]}{rel}{bzh[:2]}{_B[bi]} → " + {"沖": "本題根基動搖：換環境、轉換跑道之應", "六合": "本題穩定、有人拉一把", "三合": "合緣、合作順", "害": "小人暗傷", "刑": "自我拉扯、折騰", "伏吟": "原地踏步、舊事重提"}[rel])
    for x in ln.get("shensha", []):
        if x in s["good_sha"]:
            w, why = s["good_sha"][x]
            add(w, f"流年逢{x} → {why}")
        elif x in s["bad_sha"]:
            w, why = s["bad_sha"][x]
            add(w, f"流年逢{x} → {why}")
        elif x == "驛馬" and topic in ("career", "family"):
            add(0, f"流年逢驛馬 → {'外派、出差、轉換' if topic == 'career' else '搬遷、遠行之應'}")
    add(1 if ln["nature"] == "favourable" else -1, f"流年{ln['gz']}為{'喜用' if ln['nature'] == 'favourable' else '忌耗'}五行 → 整體{'順' if ln['nature'] == 'favourable' else '需忍耐'}")
    if dy and dy["stem_god"] in stars:
        add(1, f"大運{dy['gz']}透{dy['stem_god']}（{dy['start_year']}–{dy['end_year']}）→ 十年本題底色佳")
    if dy and dy["nature"] == "unfavourable" and topic == "health":
        add(-0.5, f"大運{dy['gz']}為忌（{dy['start_year']}–{dy['end_year']}）→ 十年體力底色需養")
    ctx = {"流年": f"{ln['gz']}（{god}・{ln['nature']}）", "神煞": ln.get("shensha", []), "大運": f"{dy['gz']}（{dy['stem_god']}・{dy['nature']}）" if dy else None, "age": ln["age"]}
    return rs, ctx


def _ziwei_year(topic: str, natal_chart: dict, yr: int) -> tuple[list[dict], dict]:
    s = spec(topic)
    stem = X.STEMS[(yr - 4) % 10]
    lyb = (yr - 4) % 12
    mut = ZW.SIHUA[stem]
    sp = natal_chart.get("star_palace", {})
    by_branch = {p["branch"]: p for p in natal_chart.get("palaces", [])}
    rs: list[dict] = []
    def add(delta, text):
        rs.append({"src": "紫微", "delta": delta, "text": text})
    landing = {ZW.HUA[i]: sp.get(mut[i], "?") for i in range(4)}
    name = s["palace"]
    why = {"career": ("事業有進展、升遷得利", "掌權、升職或接新任務", "名聲、考績、貴人", "工作糾結、被人事所困"),
           "wealth": ("進財之年", "財務主導權、投資有為", "財名兩得", "破財、財務糾結"),
           "health": ("身體有護持", "體力過度使用", "醫藥貴人", "病符、舊疾或體力透支"),
           "study": ("學習順、文書得利", "學業掌握度高", "考運、名次", "學習卡關、文書糾紛"),
           "family": ("家宅添福、置產", "家中有主導權", "家有名聲、喜事", "家宅不寧、牽掛家人")}[topic]
    for hua, w, text in (("祿", 2, why[0]), ("權", 1, why[1]), ("科", 1, why[2]), ("忌", -2 if topic != "health" else -1.5, why[3])):
        if landing[hua] == name:
            add(w, f"流年{stem}干 {mut[ZW.HUA.index(hua)]}化{hua}入{name}宮 → {text}")
    for pn in s["palace2"]:
        if landing["祿"] == pn:
            add(0.8, f"流年化祿入{pn}宮 → 本題旁助")
        if landing["忌"] == pn:
            add(-0.8, f"流年化忌入{pn}宮 → 本題旁擾")
    taisui = by_branch.get(_B[lyb])
    if taisui and taisui["name"] == name:
        add(1, f"流年太歲入本命{name}宮 → 本題為當年主題")
    flow_b = _B[(lyb - _PALACE_OFFSET[name]) % 12]
    flow = by_branch.get(flow_b)
    sha = [_bare(x) for x in (flow or {}).get("stars", []) if _bare(x) in _SHA]
    if len(sha) >= 2:
        add(-1, f"流年{name}宮（{flow_b}）見{'、'.join(sha)} → 當年本題多磨" + ("、注意意外與發炎" if topic == "health" else ""))
    lucky = [_bare(x) for x in (flow or {}).get("stars", []) if _bare(x) in _LUCKY]
    if lucky:
        add(0.8, f"流年{name}宮（{flow_b}）見{'、'.join(lucky)} → 當年本題有貴人")
    if topic == "study":
        wen = [_bare(x) for x in (flow or {}).get("stars", []) + (taisui or {}).get("stars", []) if _bare(x) in ("文昌", "文曲")]
        if wen:
            add(1, f"流年命宮／父母宮見{'、'.join(dict.fromkeys(wen))} → 文星照，考運佳")
    if topic == "family":
        joy = [_bare(x) for x in (flow or {}).get("stars", []) + (flow or {}).get("adjective_stars", []) if _bare(x) in ("紅鸞", "天喜")]
        if joy:
            add(1, f"流年田宅宮見{'、'.join(dict.fromkeys(joy))} → 家有喜事")
    return rs, {"流年四化": [f"{mut[i]}化{ZW.HUA[i]}→{landing[ZW.HUA[i]]}" for i in range(4)], "太歲宮": (taisui or {}).get("name"), f"流年{name}宮": flow_b}


def _astro_year(topic: str, ch: Chart, yr: int) -> tuple[list[dict], dict]:
    s = spec(topic)
    planets = {p["body"]: p for p in ch.chart.get("planets", [])}
    target = planets.get(s["planet"]) if s["planet"] not in ("Saturn", "Jupiter") else planets.get(s["planet2"])
    tname = target["body"] if target else None
    asc = ch.ascendant
    rs: list[dict] = []
    seen: set[str] = set()
    def add(key, delta, text):
        if key in seen:
            return
        seen.add(key)
        rs.append({"src": "西洋", "delta": delta, "text": text})
    ctx = {}
    jup_h = {"career": {10: (1.5, "行運木星過十宮（事業宮）→ 事業擴張、升遷、貴人年"), 6: (0.8, "行運木星過六宮 → 工作量增但順")},
             "wealth": {2: (1.5, "行運木星過二宮（財帛宮）→ 收入擴張之年"), 8: (1, "行運木星過八宮 → 他人之財：投資、遺產、合資有利")},
             "health": {6: (0.8, "行運木星過六宮 → 治療順利、體重易增"), 1: (1, "行運木星過一宮 → 活力回升、恢復年")},
             "study": {9: (1.5, "行運木星過九宮 → 高等教育、留學、申請有利"), 3: (1, "行運木星過三宮 → 學習、考試、寫作順")},
             "family": {4: (1.5, "行運木星過四宮（家庭宮）→ 家宅擴張：搬新家、添丁、家運旺"), 5: (1, "行運木星過五宮 → 子女之喜")}}[topic]
    sat_h = {"career": {10: (0.5, "行運土星過十宮 → 事業承擔與考驗年：以實績升遷，或清理不合的位置"), 6: (-0.5, "行運土星過六宮 → 工作繁重、健康需顧")},
             "wealth": {2: (-1, "行運土星過二宮 → 收入收緊、需精算；適合建立長期理財"), 8: (-0.5, "行運土星過八宮 → 債務、稅務、他人資金的壓力")},
             "health": {6: (-1, "行運土星過六宮 → 慢性病、體力下滑，必須調整作息"), 1: (-1, "行運土星過一宮 → 身體負擔重、情緒低，宜減量休養")},
             "study": {9: (-0.5, "行運土星過九宮 → 升學路慢但扎實"), 3: (-0.5, "行運土星過三宮 → 學習變慢、需要紀律")},
             "family": {4: (-1, "行運土星過四宮 → 家中責任、長輩健康、搬遷壓力"), 5: (-0.5, "行運土星過五宮 → 子女教養壓力")}}[topic]
    for body, cls, table in (("Jupiter", ephem.Jupiter, jup_h), ("Saturn", ephem.Saturn, sat_h)):
        for m in (1, 4, 7, 10):
            lon = AX.lon_on(cls, date(yr, m, 1))
            if m == 7:
                ctx[body] = f"{AX.sign_of(lon)} {lon:.0f}°"
            if target:
                sep = astro._separation(lon, target["ecliptic_lon"])
                for name, ang in astro._ASPECTS.items():
                    if abs(sep - ang) <= 6:
                        if body == "Jupiter" and name in ("conjunction", "trine", "sextile"):
                            add(f"J-{name}", 1.2, f"行運木星 {name} 本命{tname}（{yr}）→ " + {"career": "事業機會擴張、貴人", "wealth": "財運得助、機會多", "health": "活力回升、恢復力好", "study": "學習與考運得助", "family": "家庭溫暖、添福"}[topic])
                        elif body == "Saturn" and name in ("conjunction", "square", "opposition"):
                            add(f"S-{name}", -1, f"行運土星 {name} 本命{tname}（{yr}）→ 本題受現實檢驗，慢而重")
                        elif body == "Saturn":
                            add(f"S-{name}", 0.5, f"行運土星 {name} 本命{tname} → 本題踏實、適合長期規劃")
                        break
            if asc:
                h = AX.house_of(lon, asc["longitude"])
                if h in table:
                    w, text = table[h]
                    add(f"{body}-H{h}", w, f"{text}（{yr}）")
    return rs, ctx


def _jyotish_year(topic: str, ch: Chart, birth: BirthInput, yr: int, lord: str | None) -> tuple[list[dict], dict]:
    from fortune import jyotish_ext as JX
    s = spec(topic)
    dl = JX.mahadasha_lord(AX.birth_utc(birth), date(yr, 7, 1))
    rs: list[dict] = []
    if dl in s["karaka"]:
        rs.append({"src": "Jyotiṣa", "delta": 1.5, "text": f"{dl} 大運（本題 kāraka）→ 本題被啟動（{yr}）"})
    elif lord and dl == lord:
        rs.append({"src": "Jyotiṣa", "delta": 1.5, "text": f"第{s['bhavas'][0]} bhāva 主 {dl} 大運 → 本題之事被啟動（{yr}）"})
    elif dl == "Jupiter":
        rs.append({"src": "Jyotiṣa", "delta": 1, "text": f"Guru 大運 → 福報、擴張、學習與家庭順（{yr}）"})
    elif dl == "Saturn":
        rs.append({"src": "Jyotiṣa", "delta": 0.5 if topic == "career" else -0.5, "text": f"Śani 大運 → {'勞而有功、靠實績' if topic == 'career' else '步調慢、講責任、體力需養'}（{yr}）"})
    elif dl == "Rahu":
        rs.append({"src": "Jyotiṣa", "delta": 0.5 if topic in ("career", "wealth") else -0.5, "text": f"Rāhu 大運 → {'非典型機會、外來之財' if topic in ('career', 'wealth') else '迷惘、作息紊亂'}（{yr}）"})
    elif dl == "Ketu":
        rs.append({"src": "Jyotiṣa", "delta": -0.5, "text": f"Ketu 大運 → 抽離、看淡，本題進展慢（{yr}）"})
    return rs, {"daśā": dl}


_SIGN_KW = {"career": ("透", "升遷", "化祿入官祿", "過十宮", "化權入官祿"), "wealth": ("財星", "財庫開", "化祿入財帛", "過二宮", "過八宮"),
            "health": ("忌神", "七殺攻身", "沖日支", "化忌入疾厄", "過六宮", "羊刃"), "study": ("印星", "文昌", "學堂", "化科", "過九宮", "過三宮", "正官"),
            "family": ("子女星", "添丁", "喜事", "化祿入田宅", "過四宮", "過五宮", "沖年支", "搬遷")}


def timing(topic: str, birth: BirthInput, charts: dict[str, Chart], start_year: int, count: int = 8) -> dict:
    """運：each year scored across 八字, 紫微, 西洋行運 and Jyotiṣa daśā, every term listed."""
    s = spec(topic)
    male = _male(birth)
    full = charts["bazi"].chart if "bazi" in charts else None
    zw = charts.get("ziwei")
    lord = _jyotish_natal(topic, charts["jyotish"]).get("lord") if "jyotish" in charts else None
    years = []
    for yr in range(start_year, start_year + count):
        reasons: list[dict] = []
        ctx: dict = {}
        if full:
            r, c = _bazi_year(topic, full, yr, male)
            reasons += r
            ctx["bazi"] = c
        if zw:
            r, c = _ziwei_year(topic, zw.chart, yr)
            reasons += r
            ctx["ziwei"] = c
        if "astrology" in charts:
            r, c = _astro_year(topic, charts["astrology"], yr)
            reasons += r
            ctx["astrology"] = c
        if "jyotish" in charts:
            r, c = _jyotish_year(topic, charts["jyotish"], birth, yr, lord)
            reasons += r
            ctx["jyotish"] = c
        score = round(sum(r["delta"] for r in reasons), 1)
        g, label = _grade(score)
        kws = _SIGN_KW[topic]
        if topic == "health":
            sign = any(any(k in r["text"] for k in kws) and r["delta"] < 0 for r in reasons) and score <= -1
        else:
            sign = any(any(k in r["text"] for k in kws) and r["delta"] > 0 for r in reasons) and score >= 3
        years.append({"year": yr, "age": (ctx.get("bazi") or {}).get("age") or (yr - birth.birth_date.year + 1), "score": score, "grade": g, "label": label,
                      "sign": sign, "reasons": _name_topic(sorted(reasons, key=lambda r: -abs(r["delta"])), s["zh"]), "context": ctx})
    if topic == "health":
        best = [y["year"] for y in sorted(years, key=lambda y: -y["score"]) if y["score"] >= 2][:3]
        caution = [y["year"] for y in years if y["score"] <= -1.5]
        sign_zh = "注意年"
    else:
        best = [y["year"] for y in sorted(years, key=lambda y: -y["score"]) if y["score"] >= 3][:3]
        caution = [y["year"] for y in years if y["grade"] == 1]
        sign_zh = {"career": "升遷／轉換年", "wealth": "進財年", "study": "考運年", "family": "家運年"}[topic]
    return {"start_year": start_year, "count": count, "years": years, "best": best, "caution": caution, "sign_label": sign_zh,
            "summary": f"{s['zh']}流年：" + ("、".join(f"{y}（{next(x['label'] for x in years if x['year'] == y)}）" for y in best) or "此區間無明顯旺年") + (f"；{'需注意' if topic == 'health' else '宜守'} {'、'.join(map(str, caution))}" if caution else "")}


# --- the topic's own sheet ------------------------------------------------------------------

def _top_gods(pillars: list[dict]) -> list[tuple[str, float]]:
    w: dict[str, float] = {}
    for p in pillars:
        if p["role"] != "day" and p.get("stem_god"):
            w[p["stem_god"]] = w.get(p["stem_god"], 0) + 1.0
        for i, h in enumerate(p.get("hidden", [])):
            w[h["god"]] = w.get(h["god"], 0) + (0.8 if i == 0 else 0.3)
    return sorted(w.items(), key=lambda kv: -kv[1])


def _zw_majors(c: dict, palace: str) -> list[str]:
    p = next((p for p in c.get("palaces", []) if p["name"] == palace), None)
    if not p:
        return []
    m = [_bare(x) for x in p.get("stars", []) if _bare(x) in _MAJORS]
    if not m:
        by_branch = {q["branch"]: q for q in c["palaces"]}
        opp = by_branch[_B[(_B.index(p["branch"]) + 6) % 12]]
        m = [_bare(x) for x in opp.get("stars", []) if _bare(x) in _MAJORS]
    return m


def extra(topic: str, charts: dict[str, Chart], male: bool | None) -> dict:
    """事業方向 / 財性與財庫 / 體質與臟腑 / 學習傾向與科系 / 六親宮位 — the sheet only this 專科 produces."""
    bz = charts["bazi"].chart if "bazi" in charts else None
    zw = charts["ziwei"].chart if "ziwei" in charts else None
    ast = charts.get("astrology")
    out: dict = {"facts": {}, "lines": []}
    if not bz:
        return out
    st, pillars = bz["strength"], bz["pillars"]
    fav = st.get("favourable", [])
    gods = _top_gods(pillars)
    planets = {p["body"]: p for p in ast.chart.get("planets", [])} if ast else {}
    if topic == "career":
        out["industries"] = {e: _INDUSTRY[e] for e in fav}
        out["styles"] = [f"{g}（{_GOD_STYLE[g]}）" for g, _ in gods[:3] if g in _GOD_STYLE]
        out["facts"]["喜用五行 → 行業"] = out["industries"]
        out["facts"]["主要十神 → 工作型態"] = out["styles"]
        out["facts"]["格局"] = f"{st.get('pattern', '')}：{st.get('pattern_note', '')}"
        if zw:
            m = _zw_majors(zw, "官祿")
            out["facts"]["紫微 官祿宮主星 → 職業象"] = [f"{x}：{_ZW_CAREER.get(x, '')}" for x in m] or "空宮借對宮"
        if ast and ast.ascendant:
            cusps = {h["house"]: h for h in ast.ascendant.get("houses", [])}
            out["facts"]["西洋 十宮（MC）"] = f"{cusps.get(10, {}).get('sign')} {cusps.get(10, {}).get('sign_zh', '')}；宮內 " + ("、".join(p["body"] for p in planets.values() if p.get("house") == 10) or "空")
        out["lines"] = [f"行業五行：{'、'.join(fav)}", f"型態：{'、'.join(g for g, _ in gods[:3])}"]
        out["summary"] = f"事業方向：喜用{'/'.join(fav)}（{'；'.join(_INDUSTRY[e].split('、')[0] + '…' for e in fav)}）・型態 {'、'.join(g for g, _ in gods[:2])}" + (f"・官祿宮 {'、'.join(_zw_majors(zw, '官祿'))}" if zw else "")
    elif topic == "wealth":
        ge = _god_elems(st["dm_elem"])
        n_zheng = sum(w for g, w in gods if g == "正財")
        n_pian = sum(w for g, w in gods if g == "偏財")
        kind = "正財型（薪資、穩定積累）" if n_zheng > n_pian else "偏財型（投資、經商、業務）" if n_pian > n_zheng else "財星不顯（靠食傷生財或行運）" if not (n_zheng or n_pian) else "正偏財並見"
        tomb = _TOMB[ge["財"]]
        has_tomb = any(p["branch"] == tomb for p in pillars)
        out["facts"]["財性"] = kind
        out["facts"]["財星五行"] = f"{ge['財']}（財庫 {tomb}{'，原局有' if has_tomb else '，原局無'}）"
        out["facts"]["身能任財"] = "身強能任財：可承擔較大財務規模" if st.get("strong") else "身弱：財多反為負擔，宜穩定正財、忌槓桿"
        out["facts"]["財源（食傷）"] = "有" if any(g in ("食神", "傷官") for g, _ in gods) else "弱：財靠機運與他人，宜培養專業"
        out["facts"]["劫財風險"] = "比劫重：忌合夥借貸" if sum(w for g, w in gods if g in ("比肩", "劫財")) >= 1.6 else "低"
        out["facts"]["喜用五行 → 生財行業"] = {e: _INDUSTRY[e] for e in fav}
        if zw:
            m = _zw_majors(zw, "財帛")
            out["facts"]["紫微 財帛宮主星 → 財性"] = [f"{x}：{_ZW_MONEY.get(x, '')}" for x in m] or "空宮借對宮"
            out["facts"]["祿存／生年化祿所在"] = f"祿存 {zw.get('star_palace', {}).get('祿存')}・化祿 " + (next((f"{_bare(x)}在{p['name']}" for p in zw['palaces'] for x in p.get('stars', []) if x.endswith('(祿)')), '—'))
        if planets:
            out["facts"]["西洋 金星／木星"] = f"Venus {planets.get('Venus', {}).get('sign')} H{planets.get('Venus', {}).get('house')}・Jupiter {planets.get('Jupiter', {}).get('sign')} H{planets.get('Jupiter', {}).get('house')}"
        out["summary"] = f"財性：{kind.split('（')[0]}・{'身強任財' if st.get('strong') else '身弱宜守'}・財庫{tomb}{'有' if has_tomb else '無'}" + (f"・財帛宮 {'、'.join(_zw_majors(zw, '財帛'))}" if zw else "")
    elif topic == "health":
        tally = _element_tally(pillars)
        dominant = max(tally, key=tally.get)
        weak = sorted(tally, key=tally.get)[:2]
        out["facts"]["五行分布"] = tally
        out["facts"]["偏旺"] = f"{dominant}（{tally[dominant]}）→ {_ORGAN[dominant]} 易亢；受剋的 {X.KE[dominant]}（{_ORGAN[X.KE[dominant]]}）易虛"
        out["facts"]["偏弱"] = {e: _ORGAN[e] for e in weak}
        out["facts"]["日主"] = f"{st.get('day_master')}{st.get('dm_elem')}・{st.get('label')}"
        out["facts"]["調候"] = st.get("tiaohou_note")
        out["facts"]["養生方向（喜用）"] = {e: _ORGAN[e] for e in fav}
        if zw:
            m = _zw_majors(zw, "疾厄")
            p = next(p for p in zw["palaces"] if p["name"] == "疾厄")
            sha = [_bare(x) for x in p.get("stars", []) if _bare(x) in _SHA]
            out["facts"]["紫微 疾厄宮 → 臟腑"] = [f"{x}：{_ZW_ORGAN.get(x, '')}" for x in m + sha] or "空宮借對宮"
        if planets:
            out["facts"]["西洋 日月火土"] = {b: f"{planets[b]['sign']} H{planets[b].get('house')}" for b in ("Sun", "Moon", "Mars", "Saturn") if b in planets}
        out["summary"] = f"體質：{dominant}旺・{'/'.join(weak)}弱（{'；'.join(_ORGAN[e].split('、')[0] for e in weak)}）・{st.get('label', '')[:2]}" + (f"・疾厄宮 {'、'.join(_zw_majors(zw, '疾厄'))}" if zw else "")
    elif topic == "study":
        yin = sum(w for g, w in gods if g in ("正印", "偏印"))
        shi = sum(w for g, w in gods if g in ("食神", "傷官"))
        style = "印型：靠記憶、系統、理論與老師，適合課堂與筆試" if yin > shi + 0.5 else "食傷型：靠表達、創作與實作，適合專題、口試與作品" if shi > yin + 0.5 else "印與食傷均衡：吸收與輸出並重"
        sha = [x for p in pillars for x in p.get("shensha", []) if x in ("文昌貴人", "學堂", "華蓋", "太極貴人")]
        out["facts"]["學習型態"] = style
        out["facts"]["文星神煞"] = list(dict.fromkeys(sha)) or "無"
        out["facts"]["喜用五行 → 科系方向"] = {e: _MAJOR_FIELD[e] for e in fav}
        out["facts"]["十神主軸"] = [f"{g}" for g, _ in gods[:3]]
        if zw:
            sp = zw.get("star_palace", {})
            out["facts"]["紫微 文昌／文曲／化科"] = f"文昌在{sp.get('文昌')}・文曲在{sp.get('文曲')}・化科 " + (next((f"{_bare(x)}在{p['name']}" for p in zw['palaces'] for x in p.get('stars', []) if x.endswith('(科)')), '—'))
            out["facts"]["紫微 父母宮（文書宮）"] = "、".join(_zw_majors(zw, "父母")) or "空"
        if planets:
            out["facts"]["西洋 水星／木星"] = f"Mercury {planets.get('Mercury', {}).get('sign')} H{planets.get('Mercury', {}).get('house')}・Jupiter {planets.get('Jupiter', {}).get('sign')} H{planets.get('Jupiter', {}).get('house')}"
        out["summary"] = f"學習：{style.split('：')[0]}・科系向 {'/'.join(fav)}" + (f"・文星 {'、'.join(dict.fromkeys(sha))}" if sha else "") + (f"・昌曲在 {zw.get('star_palace', {}).get('文昌')}/{zw.get('star_palace', {}).get('文曲')}" if zw else "")
    elif topic == "family":
        yr, hr, dayp = pillars[0], pillars[3], pillars[2]
        child = ["食神", "傷官"] if male is False else ["正官", "七殺"] if male else ["食神", "傷官", "正官", "七殺"]
        rel_y, _ = _relation(yr["branch_idx"], dayp["branch_idx"])
        rel_h, _ = _relation(hr["branch_idx"], dayp["branch_idx"])
        out["facts"]["父母宮（年柱）"] = f"{yr['gz']}（{yr['stem_god']}）{'與日支' + rel_y if rel_y else ''}・納音{yr['nayin']}・{'、'.join(yr.get('shensha', [])) or '—'}"
        out["facts"]["母星（印）"] = "有" if any(g in ("正印", "偏印") for g, _ in gods) else "不顯：母緣淡或靠自己"
        out["facts"]["父星（財）"] = "有" if any(g in ("正財", "偏財") for g, _ in gods) else "不顯：父緣淡或早離"
        out["facts"]["子女宮（時柱）"] = (f"{hr['gz']}（{hr['stem_god']}）{'與日支' + rel_h if rel_h else ''}・{hr.get('changsheng', '')}" if bz.get("time_known", True) else "無時辰")
        out["facts"]["子女星"] = "、".join(child) + ("：" + ("有" if any(g in child for g, _ in gods) else "不顯，子女緣靠行運"))
        out["facts"]["兄弟宮（月柱）"] = f"{pillars[1]['gz']}（{pillars[1]['stem_god']}）・比劫 {'有' if any(g in ('比肩', '劫財') for g, _ in gods) else '少（獨立、手足緣淡）'}"
        if zw:
            for pn in ("田宅", "父母", "子女", "兄弟"):
                p = next(p for p in zw["palaces"] if p["name"] == pn)
                out["facts"][f"紫微 {pn}宮"] = f"{p['stem']}{p['branch']}：{_stars_of(p)}"
        if planets:
            out["facts"]["西洋 月亮／四宮"] = f"Moon {planets.get('Moon', {}).get('sign')} H{planets.get('Moon', {}).get('house')}" + (f"；四宮內 " + ("、".join(p["body"] for p in planets.values() if p.get("house") == 4) or "空") if ast and ast.ascendant else "")
        out["summary"] = f"六親：父母宮{yr['gz']}{('（' + rel_y + '日支）') if rel_y else ''}・子女宮{hr['gz'] if bz.get('time_known', True) else '無時辰'}・子女星{'有' if any(g in child for g, _ in gods) else '不顯'}" + (f"・田宅宮 {'、'.join(_zw_majors(zw, '田宅'))}" if zw else "")
    return out


# --- the consultation ------------------------------------------------------------------------

def consult(topic: str, birth: BirthInput, question: str | None = None, *, start_year: int | None = None, years: int = 8,
            read: bool = False, lang: str = "zh", house_system: str = "whole_sign") -> dict:
    """One sitting with a 專科命理師: cast once, then 命 (natal), 今年 (all 13), 運 (timing), the topic sheet, and the reading."""
    s = spec(topic)
    male = _male(birth)
    charts: dict[str, Chart] = {}
    errors: dict[str, str] = {}
    for k in casting.REGISTRY:
        try:
            charts[k] = casting.cast(k, birth, house_system=house_system, transits=(k == "astrology"))
        except Exception as e:  # noqa: BLE001 — one system never sinks the sitting
            errors[k] = str(e)
    intent = classify(topic, question)
    this_year = F.synthesize(charts, topic, male)
    out = {
        "topic": topic, "topic_label": f"{s['zh']} / {s['en']}", "subject": birth.label(), "question": question,
        "intent": intent, "intent_label": intent_label(topic, intent),
        "natal": natal(topic, charts, male),
        "this_year": {k: this_year[k] for k in ("systems", "tally", "lean", "lean_zh", "consensus", "conflicts", "summary")},
        "timing": timing(topic, birth, charts, start_year or date.today().year, years),
        "extra": extra(topic, charts, male),
        "errors": errors,
    }
    out["summary"] = " ｜ ".join(x for x in (out["natal"]["summary"], out["this_year"]["summary"], out["timing"]["summary"], out["extra"].get("summary")) if x)
    if read:
        out["interpretation"] = interpret(out, lang=lang)
    return out


def _persona(topic: str) -> str:
    p = _PROMPTS / f"{topic}_master.md"
    return p.read_text(encoding="utf-8") if p.exists() else f"You are a warm, rigorous {spec(topic)['en']}-specialist diviner. Read only from the facts."


def prompts(out: dict, *, lang: str = "zh") -> tuple[str, str]:
    """(system, user) for the 專科 reading — the facts the sub-question needs, in the order it needs them."""
    from fortune.interpret import lang_instruction
    topic, intent = out["topic"], out["intent"]
    s = spec(topic)
    order = s["order"].get(intent) or s["order"]["current"]
    slim = {}
    for k in order:
        v = out.get(k)
        if not v:
            continue
        if k == "timing":
            v = {"summary": v["summary"], "best": v["best"], "caution": v["caution"], "sign_label": v["sign_label"],
                 "years": [{"year": y["year"], "age": y["age"], "score": y["score"], "label": y["label"], "sign": y["sign"],
                            "reasons": [f"{r['src']} {r['delta']:+} {r['text']}" for r in y["reasons"][:6]]} for y in v["years"]]}
        elif k == "this_year":
            v = {"summary": v["summary"], "systems": [{"system": r["system_zh"], "verdict": r["verdict_zh"], "why": r["reason"], "facts": r["facts"]} for r in v["systems"]]}
        elif k == "natal":
            v = {"summary": v["summary"], "systems": [{"system": r["system_zh"], "score": r["score"], "reasons": r["reasons"], "facts": r["facts"]} for r in v["systems"]]}
        elif k == "extra":
            v = {"summary": v.get("summary"), "facts": v.get("facts")}
        slim[k] = v
    default_q = f"（未指定，請看整體{s['zh']}運）"
    user = (f"命主 / Subject: {out['subject']}\n★ 問題 / Question: {out.get('question') or default_q}（子題 sub-intent: {out['intent_label']}）\n"
            f"（先回答這個子題，再補其餘 / answer this sub-question FIRST）\n\nFacts (JSON, in the order to use them):\n{json.dumps(slim, ensure_ascii=False, indent=1)}\n\n"
            "Read only from these facts. " + lang_instruction(lang))
    return _persona(topic) + "\n" + lang_instruction(lang), user


def interpret(out: dict, *, lang: str = "zh") -> str:
    system, user = prompts(out, lang=lang)
    return complete(system, user)
