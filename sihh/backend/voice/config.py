"""Environment-based configuration for the voice layer.

All provider / model choices and thresholds come from environment variables so
nothing provider-specific (and no credential) is hard-coded.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(float(os.environ.get(name, "") or default))
    except ValueError:
        return default


DEFAULT_STT_MODELS = {"sarvam": "saaras:v4", "openai": "whisper-1"}
DEFAULT_TTS_MODELS = {"sarvam": "bulbul:v3", "openai": "gpt-4o-mini-tts"}
DEFAULT_TTS_VOICES = {"sarvam": "shubh", "openai": "alloy"}

# Domain vocabulary used to bias recognition toward BIS terminology.
DEFAULT_KEYTERMS = [
    "BIS", "Bureau of Indian Standards", "ISI mark", "Indian Standard", "IS number",
    "CRS", "Compulsory Registration Scheme", "hallmarking", "HUID", "licence",
    "certification", "Quality Control Order", "QCO", "FMCS", "BIS Act 2016",
    "Manak Online", "conformity assessment", "testing laboratory", "MSME",
    "registration", "standard number", "marking fee",
]


@dataclass
class VoiceConfig:
    enabled: bool = True
    stt_provider: str = "browser"       # sarvam | openai | browser | mock
    stt_model: str = ""
    stt_mode: str = ""                  # sarvam only (e.g. "codemix"); optional
    tts_provider: str = "browser"       # sarvam | openai | browser
    tts_model: str = ""
    tts_voice: str = ""
    max_duration_s: int = 60
    max_audio_mb: float = 10.0
    confidence_threshold: float = 0.6
    language_confidence_threshold: float = 0.5
    min_evidence_similarity: float = 0.40
    tts_max_chars: int = 2500
    request_timeout_s: float = 30.0
    keyterms: list[str] = field(default_factory=lambda: list(DEFAULT_KEYTERMS))
    metrics_enabled: bool = True

    # Credentials are read but NEVER serialised to clients (see public_dict).
    sarvam_api_key: str = field(default="", repr=False)
    openai_api_key: str = field(default="", repr=False)

    @property
    def stt_is_server(self) -> bool:
        return self.stt_provider in {"sarvam", "openai", "mock"}

    @property
    def tts_is_server(self) -> bool:
        return self.tts_provider in {"sarvam", "openai"}

    def public_dict(self) -> dict:
        """Safe subset for the frontend. Contains no credentials or URLs."""
        return {
            "enabled": self.enabled,
            "stt": {"provider": self.stt_provider, "mode": "server" if self.stt_is_server else "browser"},
            "tts": {"provider": self.tts_provider, "mode": "server" if self.tts_is_server else "browser"},
            "max_duration_s": self.max_duration_s,
            "confidence_threshold": self.confidence_threshold,
            "tts_max_chars": self.tts_max_chars,
        }


def _resolve_provider(explicit: str, sarvam_key: str, openai_key: str) -> str:
    explicit = (explicit or "auto").strip().lower()
    if explicit != "auto":
        return explicit
    if sarvam_key:
        return "sarvam"
    if openai_key:
        return "openai"
    return "browser"


def load_voice_config() -> VoiceConfig:
    sarvam_key = os.environ.get("SARVAM_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    stt_provider = _resolve_provider(os.environ.get("STT_PROVIDER", "auto"), sarvam_key, openai_key)
    tts_provider = _resolve_provider(os.environ.get("TTS_PROVIDER", "auto"), sarvam_key, openai_key)

    # A server provider without its key silently degrades to the browser.
    if stt_provider == "sarvam" and not sarvam_key:
        stt_provider = "browser"
    if stt_provider == "openai" and not openai_key:
        stt_provider = "browser"
    if tts_provider == "sarvam" and not sarvam_key:
        tts_provider = "browser"
    if tts_provider == "openai" and not openai_key:
        tts_provider = "browser"

    max_duration = _env_int("VOICE_MAX_DURATION", 60)
    if stt_provider == "sarvam":
        # Sarvam's synchronous REST endpoint is limited to ~30 s of audio.
        max_duration = min(max_duration, 30)

    keyterms_env = os.environ.get("STT_KEYTERMS", "").strip()
    keyterms = [k.strip() for k in keyterms_env.split("|") if k.strip()] if keyterms_env else list(DEFAULT_KEYTERMS)

    return VoiceConfig(
        enabled=_env_bool("VOICE_ENABLED", True),
        stt_provider=stt_provider,
        stt_model=os.environ.get("STT_MODEL", "").strip() or DEFAULT_STT_MODELS.get(stt_provider, ""),
        stt_mode=os.environ.get("STT_MODE", "").strip(),
        tts_provider=tts_provider,
        tts_model=os.environ.get("TTS_MODEL", "").strip() or DEFAULT_TTS_MODELS.get(tts_provider, ""),
        tts_voice=os.environ.get("TTS_VOICE", "").strip() or DEFAULT_TTS_VOICES.get(tts_provider, ""),
        max_duration_s=max(5, max_duration),
        max_audio_mb=_env_float("VOICE_MAX_AUDIO_MB", 10.0),
        confidence_threshold=_env_float("VOICE_CONFIDENCE_THRESHOLD", 0.6),
        language_confidence_threshold=_env_float("VOICE_LANGUAGE_CONFIDENCE_THRESHOLD", 0.5),
        min_evidence_similarity=_env_float("VOICE_MIN_EVIDENCE_SIMILARITY", 0.40),
        tts_max_chars=_env_int("VOICE_TTS_MAX_CHARS", 2500),
        request_timeout_s=_env_float("VOICE_REQUEST_TIMEOUT", 30.0),
        keyterms=keyterms[:50],
        metrics_enabled=_env_bool("VOICE_METRICS_ENABLED", True),
        sarvam_api_key=sarvam_key,
        openai_api_key=openai_key,
    )
