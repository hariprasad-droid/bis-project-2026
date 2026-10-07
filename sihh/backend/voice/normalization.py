"""Query normalisation for spoken BIS questions.

Responsibilities:
* Fix spoken / transcribed forms of BIS terms ("I S 1 2 9 3" -> "IS 1293",
  "बीआईएस" -> "BIS").
* Protect technical terms (BIS, IS numbers, CRS, HUID, ...) so translation
  never alters them.
* Remove filler words from conversational speech.
* Map common romanised Indic function words to English for retrieval
  (Hinglish / Tanglish / ...), without discarding the original text.
* Detect follow-up questions ("How much does it cost?") and build a
  context-enriched retrieval query from the conversation history.

Nothing here invents content: transformations are either lossless
(term protection) or limited to well-known function words.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Protected technical vocabulary
# ---------------------------------------------------------------------------
PROTECTED_TERMS = [
    "Bureau of Indian Standards", "Indian Standard", "Quality Control Order", "Compulsory Registration Scheme",
    "Foreign Manufacturers Certification Scheme", "Manak Online", "ISI mark", "BIS Act",
    "BIS", "ISI", "CRS", "HUID", "QCO", "FMCS", "AHC", "MSME", "MeitY", "LRS",
]

# IS numbers: IS 1293, IS:1293, IS-1293, IS 1293:2019, IS 1293 (Part 1)
IS_NUMBER_RE = re.compile(
    r"\bIS\s*[:\-]?\s*\d{2,6}(?:\s*\(\s*Part\s*\d+\s*\))?(?:\s*[:\-]\s*\d{4})?\b",
    re.IGNORECASE,
)

# Native-script spellings of acronyms commonly produced by STT.
_NATIVE_ACRONYMS = [
    (r"बी\s*आई\s*एस", "BIS"), (r"आई\s*एस\s*आई", "ISI"), (r"सी\s*आर\s*एस", "CRS"),
    (r"एच\s*यू\s*आई\s*डी", "HUID"), (r"क्यू\s*सी\s*ओ", "QCO"),
    (r"பி\s*ஐ\s*எஸ்", "BIS"), (r"ஐ\s*எஸ்\s*ஐ", "ISI"), (r"சி\s*ஆர்\s*எஸ்", "CRS"),
    (r"బీ\s*ఐ\s*ఎస్", "BIS"), (r"ఐ\s*ఎస్\s*ఐ", "ISI"),
    (r"ಬಿ\s*ಐ\s*ಎಸ್", "BIS"), (r"ಐ\s*ಎಸ್\s*ಐ", "ISI"),
    (r"ബി\s*ഐ\s*എസ്", "BIS"), (r"ഐ\s*എസ്\s*ഐ", "ISI"),
    (r"বি\s*আই\s*এস", "BIS"), (r"আই\s*এস\s*আই", "ISI"),
    (r"બી\s*આઈ\s*એસ", "BIS"), (r"આઈ\s*એસ\s*આઈ", "ISI"),
    (r"ਬੀ\s*ਆਈ\s*ਐਸ", "BIS"), (r"ਆਈ\s*ਐਸ\s*ਆਈ", "ISI"),
]
# "आईएस 1293" / "ஐஎஸ் 1293" -> "IS 1293"
_NATIVE_IS_NUMBER = re.compile(r"(?:आई\s*एस|ஐ\s*எஸ்|ఐ\s*ఎస్|ಐ\s*ಎಸ್|ഐ\s*എസ്|আই\s*এস|આઈ\s*એસ|ਆਈ\s*ਐਸ)\s*[:\-]?\s*(\d{2,6})")

_UNIT_WORDS = r"(?:days?|months?|years?|hours?|weeks?|rupees?|rs|percent|%|lakhs?|crores?|minutes?)"

_FILLERS_RE = re.compile(r"\b(?:um+|uh+|hmm+|erm+|ah+|you know|i mean)\b[,]?\s*", re.IGNORECASE)

# Romanised function words -> English (only applied for the detected language).
ROMAN_LEXICON: dict[str, dict[str, str]] = {
    "hi": {"kya": "what", "kaise": "how", "kaisa": "how", "kitna": "how much", "kitne": "how much", "kitni": "how much",
           "chahiye": "required", "kaha": "where", "kahan": "where", "kab": "when", "kaun": "who", "liye": "for",
           "mujhe": "I", "karna": "do", "karen": "do", "karein": "do", "batao": "tell", "bataiye": "tell",
           "nahi": "not", "nahin": "not", "milega": "get", "aur": "and", "hai": "", "hain": "", "ka": "", "ke": "",
           "ki": "", "ko": "", "mein": "in", "se": "from", "hoga": "", "kripya": "please"},
    "ta": {"enna": "what", "yenna": "what", "eppadi": "how", "epdi": "how", "venum": "required", "vendum": "required",
           "panna": "do", "pannanum": "do", "pannuvathu": "do", "enga": "where", "evvalavu": "how much",
           "ethana": "how much", "eppo": "when", "ku": "for", "la": "in", "irukku": "is", "iruka": "is",
           "sollunga": "tell", "naan": "I", "enaku": "I", "enakku": "I", "seyya": "do"},
    "te": {"enti": "what", "emiti": "what", "ela": "how", "kavali": "required", "cheyali": "do", "cheyyali": "do",
           "ekkada": "where", "entha": "how much", "kosam": "for", "nenu": "I", "naaku": "I", "cheppandi": "tell",
           "undi": "is", "chesukovali": "do"},
    "kn": {"enu": "what", "yenu": "what", "hege": "how", "beku": "required", "maadodu": "do", "madbeku": "do",
           "elli": "where", "eshtu": "how much", "nanage": "I", "heli": "tell", "ide": "is"},
    "ml": {"enthu": "what", "engane": "how", "venam": "required", "cheyyanam": "do", "evide": "where",
           "ethra": "how much", "enikku": "I", "parayamo": "tell", "aanu": "is"},
    "bn": {"kivabe": "how", "kemon": "how", "koto": "how much", "lagbe": "required", "dorkar": "required",
           "korte": "do", "kothay": "where", "keno": "why", "jonno": "for", "ami": "I", "amar": "my", "bolun": "tell"},
    "mr": {"kay": "what", "kase": "how", "kashi": "how", "pahije": "required", "kiti": "how much",
           "kuthe": "where", "sathi": "for", "mala": "I", "aahe": "is", "ahe": "is", "sanga": "tell"},
    "gu": {"shu": "what", "kevi": "how", "rite": "", "joie": "required", "joiye": "required", "ketlu": "how much",
           "maate": "for", "mane": "I", "chhe": "is", "che": "is"},
    "pa": {"kiven": "how", "kive": "how", "kinna": "how much", "kinne": "how much", "chahida": "required",
           "layi": "for", "mainu": "I", "kithe": "where", "dasso": "tell"},
}

_FOLLOW_UP_WORDS = {"it", "its", "this", "that", "these", "those", "they", "them", "same", "above", "there", "here"}
_FOLLOW_UP_PHRASES = re.compile(
    r"^(?:and|also|what about|how about|then|so|ok(?:ay)?|but)\b|\b(?:for (?:it|this|that)|the same|mentioned above)\b",
    re.IGNORECASE,
)
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "and", "or", "for", "in", "on", "at", "by",
    "with", "what", "how", "why", "when", "where", "which", "who", "do", "does", "did", "can", "could", "should",
    "would", "will", "i", "me", "my", "we", "you", "your", "it", "this", "that", "please", "tell", "about",
    "much", "many", "get", "need", "required", "there", "any", "from", "as", "per", "under", "into",
}


# ---------------------------------------------------------------------------
# Spoken-form fixes
# ---------------------------------------------------------------------------
def fix_spoken_terms(text: str) -> str:
    """Repair common STT renderings of BIS acronyms and IS numbers."""
    out = text
    for pattern, repl in _NATIVE_ACRONYMS:
        out = re.sub(pattern, repl, out)
    out = _NATIVE_IS_NUMBER.sub(lambda m: f"IS {m.group(1)}", out)

    # Spelled-out acronyms: "B I S", "B.I.S.", "C R S", "I S I", "H U I D"
    out = re.sub(r"\bB\.?\s+I\.?\s+S\b\.?", "BIS", out)
    out = re.sub(r"\bB\.I\.S\.?", "BIS", out)
    out = re.sub(r"\bI\.?\s+S\.?\s+I\b\.?", "ISI", out)
    out = re.sub(r"\bC\.?\s+R\.?\s+S\b\.?", "CRS", out)
    out = re.sub(r"\bH\.?\s+U\.?\s+I\.?\s+D\b\.?", "HUID", out)
    out = re.sub(r"\bQ\.?\s+C\.?\s+O\b\.?", "QCO", out)

    # "I.S. 1293", "I S 1 2 9 3", "IS-1293" -> "IS 1293"
    def _is_num(m: re.Match) -> str:
        return f"IS {re.sub(r'\s+', '', m.group(1))}"
    out = re.sub(r"\bI\.?\s?S\.?\s*[-:]?\s*((?:\d\s?){2,6})(?=\b)", _is_num, out)
    # lowercase "is 10500" only when the number is 3+ digits and not a quantity
    out = re.sub(
        rf"\bis\s+(\d{{3,6}})\b(?!\s*{_UNIT_WORDS})",
        lambda m: f"IS {m.group(1)}", out,
    )
    # Normalise licence spelling variants but keep the user's meaning.
    out = re.sub(r"\blisence\b|\blicense\b", "licence", out, flags=re.IGNORECASE)
    out = re.sub(r"\bhall\s?marking\b", "hallmarking", out, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", out).strip()


def remove_fillers(text: str) -> str:
    return re.sub(r"\s{2,}", " ", _FILLERS_RE.sub("", text)).strip()


# ---------------------------------------------------------------------------
# Term protection (used around machine translation)
# ---------------------------------------------------------------------------
_PLACEHOLDER = "ZXQ{}QXZ"
_PLACEHOLDER_RE = re.compile(r"ZXQ\s*(\d+)\s*QXZ", re.IGNORECASE)


def protect_terms(text: str) -> tuple[str, list[str]]:
    """Replace protected terms with opaque placeholders. Returns (masked, terms)."""
    terms: list[str] = []

    def _stash(match: re.Match) -> str:
        terms.append(match.group(0))
        return _PLACEHOLDER.format(len(terms) - 1)

    masked = IS_NUMBER_RE.sub(_stash, text)
    for term in sorted(PROTECTED_TERMS, key=len, reverse=True):
        masked = re.sub(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", _stash, masked)
    return masked, terms


def restore_terms(text: str, terms: list[str]) -> tuple[str, bool]:
    """Restore placeholders. Returns (text, all_restored)."""
    seen: set[int] = set()

    def _put(match: re.Match) -> str:
        idx = int(match.group(1))
        if 0 <= idx < len(terms):
            seen.add(idx)
            return terms[idx]
        return match.group(0)

    restored = _PLACEHOLDER_RE.sub(_put, text)
    return restored, len(seen) == len(terms)


def extract_protected_terms(text: str) -> list[str]:
    _, terms = protect_terms(text)
    return terms


# ---------------------------------------------------------------------------
# Romanised code-mixed handling
# ---------------------------------------------------------------------------
def romanized_to_english(text: str, language: str) -> str:
    """Map romanised function words of ``language`` to English, keep everything else."""
    lexicon = ROMAN_LEXICON.get(language)
    if not lexicon:
        return text
    # Split hyphen-attached suffixes: "certification-ku" -> "certification ku"
    spaced = re.sub(r"([A-Za-z])-([a-z]{1,4})\b", r"\1 \2", text)
    out_tokens = []
    for token in re.findall(r"[A-Za-z0-9]+(?:[.:][0-9]+)?|[^\sA-Za-z0-9]", spaced):
        low = token.lower()
        if low in lexicon:
            mapped = lexicon[low]
            if mapped:
                out_tokens.append(mapped)
        else:
            out_tokens.append(token)
    joined = " ".join(out_tokens)
    joined = re.sub(r"\s+([?.!,])", r"\1", joined)
    return re.sub(r"\s{2,}", " ", joined).strip()


# ---------------------------------------------------------------------------
# Conversation context
# ---------------------------------------------------------------------------
def is_follow_up(query: str) -> bool:
    words = re.findall(r"[a-z]+", query.lower())
    if not words:
        return False
    if _FOLLOW_UP_PHRASES.search(query):
        return True
    has_pronoun = any(w in _FOLLOW_UP_WORDS for w in words)
    content = [w for w in words if w not in _STOPWORDS and w not in _FOLLOW_UP_WORDS]
    # e.g. "How much does it cost?" -> pronoun + few content words
    return has_pronoun and len(content) <= 3


def topic_terms(text: str, limit: int = 12) -> list[str]:
    terms = extract_protected_terms(text)
    for w in re.findall(r"[A-Za-z][A-Za-z\-]+", text):
        lw = w.lower()
        if lw in _STOPWORDS or lw in _FOLLOW_UP_WORDS or len(lw) < 3:
            continue
        if not any(lw == t.lower() for t in terms):
            terms.append(w)
        if len(terms) >= limit:
            break
    seen, out = set(), []
    for t in terms:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out[:limit]


def contextualize_query(query: str, history: list[dict] | None) -> tuple[str, bool]:
    """Return (retrieval_query, used_context).

    For follow-ups, append topic terms from the most recent substantive user
    turn so retrieval searches for the right subject ("it" -> "BIS
    certification"). The user's own words are always kept first.
    """
    if not history or not is_follow_up(query):
        return query, False
    for msg in reversed(history):
        if msg.get("role") != "user":
            continue
        prev = str(msg.get("content", ""))
        if not prev.strip() or is_follow_up(prev):
            continue
        terms = topic_terms(prev)
        if terms:
            return f"{query} (regarding: {' '.join(terms)})", True
    return query, False


def normalize_for_search(text: str) -> str:
    """Spoken-form fixes + filler removal; safe for any language."""
    return remove_fillers(fix_spoken_terms(text))
