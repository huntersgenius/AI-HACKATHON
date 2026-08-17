"""Keyword and threshold rules — the fallback that always works.

Two independent checks run over every answer:

1. numeric thresholds, selected by the check-in's `question_key` (data, not
   persona — a new question type adds a row to THRESHOLDS, never an `if`);
2. Uzbek danger keywords, scanned regardless of which question was asked,
   because a patient may report something alarming in any answer.

Negations are respected: "qizarish yo'q" must not raise a flag.
"""

import re
import unicodedata

from analyzers.base import GREEN, RED, YELLOW, AnalyzerResult, analyzer, max_risk

SCORE = {GREEN: 10, YELLOW: 55, RED: 90}

# question_key -> ordered bands. First matching band wins.
# (low, high, risk_level, signal, reasoning)
#
# Diabet chegaralari: O'zR SSV 2025-yil 23-iyun 180-sonli buyrug'iga ilova
# qilingan «2-tur qandli diabet» va «Diabetik ketoatsidoz» milliy klinik
# protokollaridan olingan.
THRESHOLDS = {
    # --- Diabet: glikemiya ---
    "glucose_fasting": [
        (0.0, 3.9, RED, "gipoglikemiya",
         "Nahorgi qand 3.9 mmol/l dan past — gipoglikemiya. Protokol bo'yicha "
         "shoshilinch holat: tez hazm bo'ladigan uglevod kerak."),
        (3.9, 7.0, GREEN, None, "Nahorgi qand maqsadli oraliqda."),
        (7.0, 11.0, YELLOW, "nahorgi_giperglikemiya",
         "Nahorgi qand maqsaddan yuqori (maqsad < 7.0 mmol/l)."),
        (11.0, 16.0, YELLOW, "giperglikemiya",
         "Nahorgi qand 11.0 dan yuqori — ketoatsidoz chegarasi. Keton "
         "tekshiruvi tavsiya etiladi."),
        (16.0, 60.0, RED, "ogir_giperglikemiya",
         "Nahorgi qand 16.0 mmol/l dan yuqori — og'ir giperglikemiya, "
         "ketoatsidoz xavfi."),
    ],
    "glucose_pp": [
        (0.0, 3.9, RED, "gipoglikemiya",
         "Ovqatdan keyingi qand 3.9 mmol/l dan past — gipoglikemiya."),
        (3.9, 10.0, GREEN, None, "Ovqatdan keyingi qand maqsadli oraliqda."),
        (10.0, 16.0, YELLOW, "postprandial_giperglikemiya",
         "Ovqatdan 2 soat keyingi qand maqsaddan yuqori (maqsad < 10.0 mmol/l)."),
        (16.0, 60.0, RED, "ogir_giperglikemiya",
         "Ovqatdan keyingi qand 16.0 mmol/l dan yuqori — og'ir giperglikemiya."),
    ],
    "hba1c": [
        (0.0, 4.0, YELLOW, "shubhali_hba1c",
         "HbA1c qiymati juda past — o'lchov xatosi bo'lishi mumkin."),
        (4.0, 7.0, GREEN, None, "HbA1c maqsadli darajada (< 7.0%)."),
        (7.0, 9.0, YELLOW, "hba1c_maqsaddan_yuqori",
         "HbA1c maqsaddan yuqori (maqsad < 7.0%). Terapiyani qayta ko'rib "
         "chiqish 3 oydan kechiktirilmasligi kerak."),
        (9.0, 20.0, RED, "hba1c_dekompensatsiya",
         "HbA1c 9% dan yuqori — uglevod almashinuvi dekompensatsiyasi."),
    ],
    # Javobda birinchi son sistolik bosim deb olinadi ("128/82" -> 128).
    "blood_pressure": [
        (0.0, 90.0, RED, "past_bosim",
         "Sistolik bosim 90 dan past — kollaps xavfi."),
        (90.0, 131.0, GREEN, None, "Qon bosimi maqsadli oraliqda."),
        (131.0, 160.0, YELLOW, "bosim_maqsaddan_yuqori",
         "Sistolik bosim maqsaddan yuqori (18–65 yosh uchun maqsad ≤ 130)."),
        (160.0, 300.0, RED, "yuqori_bosim",
         "Sistolik bosim 160 dan yuqori — gipertenziv holat."),
    ],
    # --- Jarrohlik personalari uchun saqlanadi ---
    "temperature": [
        (38.5, 45.0, RED, "juda_yuqori_harorat",
         "Tana harorati 38.5°C dan yuqori — infeksiya belgisi bo'lishi mumkin."),
        (37.5, 38.5, YELLOW, "yuqori_harorat",
         "Tana harorati biroz ko'tarilgan (37.5–38.5°C)."),
        (35.0, 37.5, GREEN, None, "Tana harorati me'yorda."),
        (0.0, 35.0, RED, "past_harorat",
         "Tana harorati juda past — zudlik bilan tekshiruv kerak."),
    ],
    "pain": [
        (8.0, 11.0, RED, "kuchli_ogriq",
         "Og'riq darajasi 8 dan yuqori — kuchli og'riq."),
        (5.0, 8.0, YELLOW, "ortacha_ogriq",
         "Og'riq darajasi o'rtacha (5–7)."),
        (0.0, 5.0, GREEN, None, "Og'riq darajasi past."),
    ],
}

# (regex, risk_level, signal, reasoning)
KEYWORD_RULES = [
    # --- Diabetik ketoatsidoz (DKA) — «Diabetik ketoatsidoz» protokoli ---
    (r"aseton|atseton|sirka hid|g'alati hid|galati hid|hid kel", RED, "aseton_hidi",
     "Nafasda aseton hidi — ketoatsidoz sindromining eng xarakterli belgisi. "
     "Protokol bo'yicha shoshilinch kasalxonaga yotqizish talab qilinadi."),
    (r"chuqur nafas|shovqinli nafas|tez nafas ol", RED, "kussmaul_nafasi",
     "Chuqur, shovqinli nafas (Kussmaul) — ketoatsidoz belgisi."),
    (r"kofe quyqa|qora qus|qora rangli qus", RED, "kofe_quyqasi_qusish",
     "\"Kofe quyqasi\" rangidagi qusish — eroziv gastrit yoki stress yarasi belgisi."),
    (r"ko'p siy|kop siy|tez-tez siy|siyishim ko'pay|siyishim kopay", YELLOW, "poliuriya",
     "Poliuriya — dekompensatsiya belgisi. Ketoatsidozda kuniga 3–6 litrgacha yetadi."),
    (r"chanqa|tashna|suv ich(gim|aver)", YELLOW, "polidipsiya",
     "Kuchli chanqash — giperglikemiya belgisi."),
    (r"og'zim quruq|ogzim quruq|og'iz qurish|ogiz qurish", YELLOW, "ogiz_qurishi",
     "Og'iz qurishi — suvsizlanish sindromi belgisi."),

    # --- Gipoglikemiya — teri NAM, tez rivojlanadi ---
    (r"terla|ter bos|sovuq ter", RED, "terlash",
     "Terlash (teri nam) — gipoglikemiyaning xarakterli belgisi. "
     "Bu holatni ketoatsidozdan ajratadi: ketoatsidozda teri quruq."),
    (r"och qol|ochlik|qorn?i(m)? och|juda och", RED, "ochlik_hissi",
     "Kuchli ochlik hissi — gipoglikemiya belgisi."),

    # --- Dori/insulin uzilishi — DKA ning eng ko'p uchraydigan sababi ---
    (r"insulin.{0,20}(qilmad|unutdim|tugad|yo'q|yoq)", RED, "insulin_uzilishi",
     "Insulin in'eksiyasi o'tkazib yuborilgan — protokol bo'yicha ketoatsidozning "
     "eng ko'p uchraydigan sababi."),
    (r"dori.{0,20}(ichmad|qilmad|unutdim|tugad)|ukol qilmad", YELLOW, "dori_uzilishi",
     "Dori qabul qilish uzilgan — dekompensatsiya xavfi."),

    # --- Nefropatiya (SBK C4–C5) ---
    (r"siydik kam|peshob kam|siya olma|siydik chiqma", RED, "oliguriya",
     "Siydik chiqishining kamayishi — buyrak funksiyasining yomonlashuvi belgisi."),
    (r"butun tana(m)? shish|hamma yerim shish|yuzim shish", RED, "anasarka",
     "Keng tarqalgan shish — protokol bo'yicha shoshilinch kasalxonaga yotqizish ko'rsatmasi."),
    (r"terim qichi|qichish", YELLOW, "teri_qichishishi",
     "Terining qichishishi — uremik intoksikatsiya yoki giperglikemiya belgisi."),

    # --- Diabetik neyropatiya / retinopatiya ---
    (r"oyoq.{0,15}uvish|uvishyap|chumoli yugur|karaxt", YELLOW, "parasteziya",
     "Oyoqlarda uvishish — diabetik neyropatiya belgisi."),
    (r"ko'rish(im)? xira|korish xira|ko'zim xira|kozim xira|xira ko'r", YELLOW, "korish_xiralashishi",
     "Ko'rishning xiralashishi — retinopatiya yoki giperglikemiya belgisi."),
    (r"oyog'im(da)? yara|oyoqda yara|yara bit(may|mas)", RED, "diabetik_oyoq",
     "Oyoqdagi yara — diabetik oyoq sindromi xavfi, shoshilinch ko'rik kerak."),

    # --- Jarrohlik personalari uchun saqlanadi ---
    (r"yiring", RED, "yiring",
     "Jarohatdan yiring ajralmoqda — infeksiya belgisi."),
    (r"qon ket|qon oq|qonayap", RED, "qon_ketishi",
     "Qon ketishi haqida xabar berildi."),
    (r"hushdan ket|hushimni yo'qot", RED, "hushdan_ketish",
     "Hushdan ketish holati — shoshilinch holat."),
    (r"nafas ol(a|maya)|nafasim qisil|nafas qisil", RED, "nafas_qisilishi",
     "Nafas olishda qiyinchilik."),
    (r"yara ochil|chok ochil|chok yechil", RED, "yara_ochilishi",
     "Jarohat yoki chok ochilgan."),
    (r"qusyap|qus(d|y)|qayt qil", RED, "qusish",
     "Qusish — asorat belgisi bo'lishi mumkin."),
    (r"qaltira|titra|bezgak", RED, "qaltirash",
     "Qaltirash va isitma — infeksiya belgisi."),
    (r"qizar", YELLOW, "qizarish", "Jarohat atrofida qizarish."),
    (r"shish|shishib", YELLOW, "shish", "Jarohat atrofida shish."),
    (r"bosh(im)? aylan", YELLOW, "bosh_aylanishi", "Bosh aylanishi."),
    (r"holsiz|darmonsiz|kuchim yo'q", YELLOW, "holsizlik", "Umumiy holsizlik."),
    (r"ishtaha(m)? yo'q|ovqat yey(a|olma)", YELLOW, "ishtahasizlik",
     "Ishtaha yo'qolgan."),
    (r"uxlay olma|uyqusiz", YELLOW, "uyqusizlik", "Uyqu buzilgan."),
]

# A hit is discarded when one of these follows it closely.
NEGATIONS = (r"yo'q", r"yoq", r"emas", r"kuzatilma", r"sezilma", r"ko'rinma")
NEGATION_WINDOW = 20


def _normalize(text):
    """Lowercase and fold the apostrophe variants Uzbek text arrives with."""
    folded = unicodedata.normalize("NFKC", text or "")
    for ch in ("‘", "’", "ʻ", "ʼ", "`", "´"):
        folded = folded.replace(ch, "'")
    return folded.lower().strip()


def _is_negated(text, end_index):
    window = text[end_index:end_index + NEGATION_WINDOW]
    return any(re.search(pattern, window) for pattern in NEGATIONS)


def _first_number(text):
    """First number in the answer; accepts both 36.8 and 36,8."""
    match = re.search(r"\d{1,3}(?:[.,]\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def _check_thresholds(question_key, text):
    bands = THRESHOLDS.get(question_key)
    if not bands:
        return None
    value = _first_number(text)
    if value is None:
        return None
    for low, high, level, signal, reasoning in bands:
        if low <= value < high:
            return level, signal, reasoning, value
    return None


def _check_keywords(text):
    hits = []
    for pattern, level, signal, reasoning in KEYWORD_RULES:
        match = re.search(pattern, text)
        if not match or _is_negated(text, match.end()):
            continue
        hits.append((level, signal, reasoning))
    return hits


@analyzer("rules", priority=10)
def analyze(context):
    """Return the merged rule verdict for one patient answer."""
    text = _normalize(context.get("text"))
    if not text:
        return None

    signals = []
    reasons = []
    levels = []

    threshold_hit = _check_thresholds(context.get("question_key"), text)
    if threshold_hit:
        level, signal, reasoning, value = threshold_hit
        levels.append(level)
        reasons.append("%s (qiymat: %s)" % (reasoning, value))
        if signal:
            signals.append(signal)

    for level, signal, reasoning in _check_keywords(text):
        levels.append(level)
        reasons.append(reasoning)
        signals.append(signal)

    level = max_risk(levels)
    if not reasons:
        reasons.append("Javobda xavf belgisi aniqlanmadi.")

    return AnalyzerResult(
        risk_level=level,
        risk_score=SCORE[level],
        danger_signals=signals,
        reasoning=" ".join(reasons),
        recommended_action=RECOMMENDATIONS[level],
    )


RECOMMENDATIONS = {
    GREEN: None,
    YELLOW: "Bemor holatini kuzatib boring, kerak bo'lsa bog'laning.",
    RED: "Bemor bilan zudlik bilan bog'laning yoki ko'rikka chaqiring.",
}
