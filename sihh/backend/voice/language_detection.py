"""LanguageDetectionService.

Detects the language of transcribed text, including romanised code-mixed
speech such as "BIS certification-ku apply panna enna documents venum?".

Strategy (deterministic, no network, fast):
1. Unicode script analysis -> strong signal for native-script text.
2. Disambiguation inside a shared script (Devanagari: hi vs mr,
   Bengali script: bn vs as) via marker words.
3. Romanised Indic marker lexicons for Latin-script text (Hinglish,
   Tanglish, ...). English technical terms are ignored for scoring.
4. Fuse with the STT provider's language hint when one is available.

Output: language, confidence, script, code_mixed flag, romanized flag.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from .languages import normalize_language_code

# Unicode block ranges -> (script name, default language)
_SCRIPT_RANGES = [
    ((0x0900, 0x097F), "Devanagari", "hi"),
    ((0x0980, 0x09FF), "Bengali", "bn"),
    ((0x0A00, 0x0A7F), "Gurmukhi", "pa"),
    ((0x0A80, 0x0AFF), "Gujarati", "gu"),
    ((0x0B00, 0x0B7F), "Odia", "or"),
    ((0x0B80, 0x0BFF), "Tamil", "ta"),
    ((0x0C00, 0x0C7F), "Telugu", "te"),
    ((0x0C80, 0x0CFF), "Kannada", "kn"),
    ((0x0D00, 0x0D7F), "Malayalam", "ml"),
    ((0x0600, 0x06FF), "Arabic", "ur"),
]

# Marathi-specific words (Devanagari) that are rare in Hindi.
_MARATHI_MARKERS = {"आहे", "आहेत", "काय", "कसे", "कशी", "मला", "आम्ही", "तुम्ही", "करावे", "साठी", "मध्ये", "नाही", "कोणते", "किती", "हवे", "पाहिजे"}
_HINDI_MARKERS = {"है", "हैं", "क्या", "कैसे", "मुझे", "के", "लिए", "में", "नहीं", "कितना", "चाहिए", "करें", "का", "की"}
# Assamese uses ৰ (U+09F0) and ৱ (U+09F1), absent from Bengali.
_ASSAMESE_CHARS = {"\u09F0", "\u09F1"}

# Romanised markers. Keep these to function words / very common verbs so that
# English words do not trigger false positives.
_ROMAN_MARKERS: dict[str, set[str]] = {
    "hi": {"kya", "kaise", "kaisa", "kitna", "kitne", "kitni", "hai", "hain", "ka", "ki", "ke", "liye", "mujhe",
           "chahiye", "karna", "karen", "karein", "kaha", "kahan", "kab", "kaun", "nahi", "nahin", "batao",
           "bataiye", "aur", "mera", "meri", "hoga", "hota", "milega", "lagta", "lagega", "kripya", "matlab"},
    "ta": {"enna", "eppadi", "epdi", "venum", "vendum", "panna", "pannanum", "irukku", "iruka", "enga", "yenna",
           "evvalavu", "ethana", "eppo", "naan", "enaku", "enakku", "sollunga", "theriyuma", "pannuvathu",
           "edhu", "athu", "idhu", "ku", "la", "kitta", "illai", "illa", "seyya"},
    "te": {"enti", "ela", "emiti", "kavali", "cheyali", "cheyyali", "unnayi", "undi", "ekkada", "entha",
           "enduku", "nenu", "naaku", "cheppandi", "ledu", "kosam", "avutundi", "evaru", "chesukovali"},
    "kn": {"enu", "yenu", "hege", "beku", "maadodu", "madbeku", "ide", "illa", "elli", "eshtu", "yaake",
           "nanage", "heli", "maadi", "agutte", "beda", "yavaga"},
    "ml": {"enthu", "engane", "evide", "venam", "cheyyanam", "undo", "ethra", "enikku", "parayamo",
           "aano", "alle", "illa", "cheyyam", "kittum", "aanu", "ningal"},
    "bn": {"ki", "kivabe", "kemon", "koto", "lagbe", "korte", "ache", "amar", "ami", "kothay", "keno",
           "bolun", "hobe", "korbo", "dorkar", "jonno"},
    "mr": {"kay", "kase", "kashi", "aahe", "ahe", "mala", "pahije", "kiti", "kuthe", "sathi", "karayche",
           "karaycha", "nahi", "milel", "sanga"},
    "gu": {"shu", "kevi", "rite", "kem", "chhe", "che", "mane", "joie", "joiye", "ketlu", "kya", "maate",
           "karvu", "karvanu", "nathi"},
    "pa": {"ki", "kiven", "kive", "kinna", "kinne", "hai", "chahida", "karna", "mainu", "tusi", "kithe",
           "layi", "nahi", "dasso"},
}

# Tokens that should never count as Indic markers (technical/English terms).
_ENGLISH_TERMS = {
    "bis", "is", "isi", "crs", "huid", "qco", "fmcs", "licence", "license", "certification", "certificate",
    "hallmark", "hallmarking", "standard", "standards", "indian", "registration", "testing", "lab",
    "product", "products", "apply", "documents", "fee", "fees", "gold", "mark", "number", "scheme",
}

_WORD_RE = re.compile(r"[a-z]+")


@dataclass
class LanguageDetectionResult:
    language: str
    confidence: float
    script: str
    code_mixed: bool
    romanized: bool
    source: str  # "script" | "lexicon" | "stt" | "fused" | "default"

    def to_dict(self) -> dict:
        return asdict(self)


class LanguageDetectionService:
    """Detect the language of a transcript; optionally fuse with an STT hint."""

    def detect(self, text: str, stt_language: str | None = None, stt_confidence: float | None = None) -> LanguageDetectionResult:
        text = (text or "").strip()
        if not text:
            return LanguageDetectionResult("en", 0.0, "Unknown", False, False, "default")

        script_counts, latin_letters = self._count_scripts(text)
        total_indic = sum(script_counts.values())
        total_letters = total_indic + latin_letters
        hint = normalize_language_code(stt_language)

        if total_indic > 0:
            script, base_lang = max(script_counts.items(), key=lambda kv: kv[1])[0]
            lang = self._disambiguate(text, script, base_lang)
            indic_ratio = total_indic / max(1, total_letters)
            code_mixed = latin_letters >= 3 and indic_ratio < 0.9
            conf = 0.75 + 0.2 * indic_ratio
            if hint and hint == lang:
                conf = min(0.99, conf + 0.05)
            elif hint and self._same_script_family(hint, script):
                # Trust a provider that heard audio over our marker heuristics.
                lang = hint
            return LanguageDetectionResult(lang, round(min(conf, 0.99), 3), script, code_mixed, False, "script")

        # Latin script: English or romanised Indic.
        lang, score, matched = self._romanized_guess(text)
        if lang and score >= 1:
            words = _WORD_RE.findall(text.lower())
            english_like = len(words) - matched
            code_mixed = english_like >= 1
            conf = min(0.9, 0.45 + 0.12 * score)
            if hint and hint == lang:
                conf = min(0.95, conf + 0.1)
            return LanguageDetectionResult(lang, round(conf, 3), "Latin", code_mixed, True, "lexicon")

        if hint and hint != "en" and stt_confidence is not None and stt_confidence >= 0.8:
            # Provider is confident the audio was Indic even though text is Latin.
            return LanguageDetectionResult(hint, round(stt_confidence * 0.8, 3), "Latin", True, True, "stt")

        return LanguageDetectionResult("en", 0.85 if total_letters >= 8 else 0.6, "Latin", False, False, "script")

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _count_scripts(text: str):
        counts: dict[tuple[str, str], int] = {}
        latin = 0
        for ch in text:
            cp = ord(ch)
            if ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
                latin += 1
                continue
            for (lo, hi), script, lang in _SCRIPT_RANGES:
                if lo <= cp <= hi:
                    counts[(script, lang)] = counts.get((script, lang), 0) + 1
                    break
        return counts, latin

    @staticmethod
    def _disambiguate(text: str, script: str, base_lang: str) -> str:
        if script == "Devanagari":
            tokens = set(re.findall(r"[\u0900-\u097F]+", text))
            mr = len(tokens & _MARATHI_MARKERS)
            hi = len(tokens & _HINDI_MARKERS)
            return "mr" if mr > hi else "hi"
        if script == "Bengali":
            return "as" if any(c in text for c in _ASSAMESE_CHARS) else "bn"
        return base_lang

    @staticmethod
    def _same_script_family(code: str, script: str) -> bool:
        families = {"Devanagari": {"hi", "mr", "ne", "sa"}, "Bengali": {"bn", "as"}}
        return code in families.get(script, set())

    @staticmethod
    def _romanized_guess(text: str):
        # Split hyphenated suffixes: "certification-ku" -> "certification", "ku"
        words = _WORD_RE.findall(text.lower())
        candidates = [w for w in words if w not in _ENGLISH_TERMS]
        best_lang, best_score, best_matched = None, 0.0, 0
        for lang, markers in _ROMAN_MARKERS.items():
            matched = [w for w in candidates if w in markers]
            # Very short generic tokens are weak evidence.
            score = sum(0.5 if len(w) <= 2 else 1.0 for w in matched)
            if score > best_score:
                best_lang, best_score, best_matched = lang, score, len(matched)
        return best_lang, best_score, best_matched


_default = LanguageDetectionService()


def detect_language(text: str, stt_language: str | None = None, stt_confidence: float | None = None) -> dict:
    return _default.detect(text, stt_language, stt_confidence).to_dict()
