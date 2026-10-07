"""Supported-language registry.

Support levels are stated per provider and are based on the providers' own
published language lists (verified Oct 2026):

* Sarvam ``saaras:v4`` STT: en-IN + 22 Indic languages, auto-detect via
  ``language_code=unknown``; returns ``language_probability``.
* Sarvam ``bulbul:v3`` TTS: bn, en, gu, hi, kn, ml, mr, od, pa, ta, te.
* OpenAI ``whisper-1`` STT: multilingual incl. hi/ta/te/ml/kn/bn/mr/gu/pa/ur;
  **no Odia**. Accuracy on several Indic languages is noticeably lower than
  on English/Hindi, so these are marked "partial".
* Browser Web Speech API: Chrome/Edge only, requires a fixed language tag
  (no auto-detection), so every language is at most "partial".

"full"    = recognised/synthesised natively with good expected quality
"partial" = works, but with reduced accuracy or missing auto-detection
"none"    = not supported by that provider
"""
from __future__ import annotations

# code -> metadata. ``code`` is the ISO-639-1 code used everywhere internally
# (and by the translator). ``bcp47`` is used for Sarvam and the browser.
LANGUAGES: dict[str, dict] = {
    "en": {"name": "English", "native": "English", "bcp47": "en-IN", "script": "Latin"},
    "hi": {"name": "Hindi", "native": "हिन्दी", "bcp47": "hi-IN", "script": "Devanagari"},
    "ta": {"name": "Tamil", "native": "தமிழ்", "bcp47": "ta-IN", "script": "Tamil"},
    "te": {"name": "Telugu", "native": "తెలుగు", "bcp47": "te-IN", "script": "Telugu"},
    "ml": {"name": "Malayalam", "native": "മലയാളം", "bcp47": "ml-IN", "script": "Malayalam"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ", "bcp47": "kn-IN", "script": "Kannada"},
    "bn": {"name": "Bengali", "native": "বাংলা", "bcp47": "bn-IN", "script": "Bengali"},
    "mr": {"name": "Marathi", "native": "मराठी", "bcp47": "mr-IN", "script": "Devanagari"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી", "bcp47": "gu-IN", "script": "Gujarati"},
    "pa": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ", "bcp47": "pa-IN", "script": "Gurmukhi"},
    "or": {"name": "Odia", "native": "ଓଡ଼ିଆ", "bcp47": "od-IN", "script": "Odia"},
    "as": {"name": "Assamese", "native": "অসমীয়া", "bcp47": "as-IN", "script": "Bengali"},
    "ur": {"name": "Urdu", "native": "اردو", "bcp47": "ur-IN", "script": "Arabic"},
}

STT_SUPPORT: dict[str, dict[str, str]] = {
    "sarvam": {c: "full" for c in ["en", "hi", "ta", "te", "ml", "kn", "bn", "mr", "gu", "pa", "or", "as", "ur"]},
    "openai": {
        "en": "full", "hi": "full",
        "ta": "partial", "te": "partial", "ml": "partial", "kn": "partial", "bn": "partial",
        "mr": "partial", "gu": "partial", "pa": "partial", "ur": "partial", "as": "partial",
        "or": "none",
    },
    "browser": {c: "partial" for c in ["en", "hi", "ta", "te", "ml", "kn", "bn", "mr", "gu", "pa", "ur"]},
    "mock": {c: "full" for c in LANGUAGES},
}

TTS_SUPPORT: dict[str, dict[str, str]] = {
    "sarvam": {c: "full" for c in ["en", "hi", "ta", "te", "ml", "kn", "bn", "mr", "gu", "pa", "or"]},
    "openai": {"en": "full", **{c: "partial" for c in ["hi", "ta", "te", "ml", "kn", "bn", "mr", "gu", "pa", "ur"]}},
    # Browser voices depend on the OS; checked at runtime in the frontend.
    "browser": {c: "partial" for c in LANGUAGES},
}

# Whisper verbose_json returns English language names.
WHISPER_NAME_TO_CODE = {
    "english": "en", "hindi": "hi", "tamil": "ta", "telugu": "te", "malayalam": "ml",
    "kannada": "kn", "bengali": "bn", "marathi": "mr", "gujarati": "gu", "punjabi": "pa",
    "panjabi": "pa", "assamese": "as", "urdu": "ur", "nepali": "ne", "sanskrit": "sa",
}


def normalize_language_code(raw: str | None) -> str | None:
    """Map provider codes (``hi-IN``, ``od-IN``, ``tamil``) to internal ISO codes."""
    if not raw:
        return None
    value = raw.strip().lower()
    if value in WHISPER_NAME_TO_CODE:
        return WHISPER_NAME_TO_CODE[value]
    base = value.split("-")[0].split("_")[0]
    if base == "od":
        base = "or"
    return base or None


def to_bcp47(code: str) -> str:
    meta = LANGUAGES.get(code)
    return meta["bcp47"] if meta else "en-IN"


def language_name(code: str | None) -> str:
    if not code:
        return "Unknown"
    meta = LANGUAGES.get(code)
    return meta["name"] if meta else code


def is_supported(code: str | None) -> bool:
    return bool(code) and code in LANGUAGES


def support_matrix(stt_provider: str, tts_provider: str) -> list[dict]:
    rows = []
    for code, meta in LANGUAGES.items():
        rows.append({
            "code": code,
            "name": meta["name"],
            "native": meta["native"],
            "bcp47": meta["bcp47"],
            "stt": STT_SUPPORT.get(stt_provider, {}).get(code, "none"),
            "tts": TTS_SUPPORT.get(tts_provider, {}).get(code, "none"),
        })
    return rows
