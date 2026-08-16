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
THRESHOLDS = {
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
