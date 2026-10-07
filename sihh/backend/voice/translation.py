"""Term-safe translation adapter.

Wraps a translator backend (``deep_translator.GoogleTranslator`` by default —
the same library the text chat already uses) and guarantees that protected
BIS terms and IS numbers survive translation unchanged. Markdown structure is
preserved line-by-line.

The backend is injectable so tests never hit the network.
"""
from __future__ import annotations

import re
from typing import Callable

from .normalization import protect_terms, restore_terms

TranslateFn = Callable[[str, str, str], str]  # (text, source, target) -> text

_MAX_CHUNK = 4500
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}")
_BOLD_FIX_RE = re.compile(r"\*\*\s+([^*]+?)\s+\*\*")


def _google_translate(text: str, source: str, target: str) -> str:
    from deep_translator import GoogleTranslator  # imported lazily
    return GoogleTranslator(source=source, target=target).translate(text) or text


class TranslationError(Exception):
    pass


class Translator:
    def __init__(self, backend: TranslateFn | None = None):
        self._backend = backend or _google_translate

    def translate(self, text: str, source: str, target: str) -> str:
        """Translate ``text``; raises TranslationError on backend failure."""
        if not text or not text.strip() or source == target:
            return text
        masked, terms = protect_terms(text)
        try:
            translated = self._translate_chunked(masked, source, target)
        except Exception as exc:  # network / quota / parsing
            raise TranslationError(str(exc)) from exc
        restored, ok = restore_terms(translated, terms)
        if not ok:
            # A placeholder was mangled; re-translate without masking so we
            # never drop a term silently, then re-append any missing terms.
            try:
                restored = self._translate_chunked(text, source, target)
            except Exception as exc:
                raise TranslationError(str(exc)) from exc
            missing = [t for t in terms if t not in restored]
            if missing:
                restored = f"{restored} ({', '.join(dict.fromkeys(missing))})"
        return _BOLD_FIX_RE.sub(r"**\1**", restored)

    def safe_translate(self, text: str, source: str, target: str) -> tuple[str, bool]:
        """Like translate() but returns (original, False) on failure."""
        try:
            return self.translate(text, source, target), True
        except TranslationError as exc:
            print(f"[Voice] translation {source}->{target} failed: {type(exc).__name__}")
            return text, False

    # -- internals -------------------------------------------------------
    def _translate_chunked(self, text: str, source: str, target: str) -> str:
        lines = text.split("\n")
        out_lines: list[str] = [""] * len(lines)
        batch_idx: list[int] = []
        batch_len = 0

        def flush():
            nonlocal batch_idx, batch_len
            if not batch_idx:
                return
            joined = "\n".join(lines[i] for i in batch_idx)
            result = self._backend(joined, source, target) or joined
            parts = result.split("\n")
            if len(parts) != len(batch_idx):
                # Line structure lost: translate individually.
                for i in batch_idx:
                    out_lines[i] = self._backend(lines[i], source, target) or lines[i]
            else:
                for i, part in zip(batch_idx, parts):
                    out_lines[i] = part
            batch_idx, batch_len = [], 0

        for i, line in enumerate(lines):
            if not line.strip() or _TABLE_SEP_RE.match(line) or line.strip().startswith("```"):
                out_lines[i] = line
                continue
            if batch_len + len(line) > _MAX_CHUNK:
                flush()
            batch_idx.append(i)
            batch_len += len(line) + 1
        flush()
        return "\n".join(out_lines)
