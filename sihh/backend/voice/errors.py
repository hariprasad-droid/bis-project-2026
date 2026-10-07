"""Voice error codes and user-friendly messages.

Raw provider errors are logged server-side only (without secrets) and are never
returned to the client. Clients receive ``{"error": {"code", "message"}}``.
"""
from __future__ import annotations


class VoiceErrorCode:
    MICROPHONE_PERMISSION_DENIED = "MICROPHONE_PERMISSION_DENIED"
    NO_MICROPHONE = "NO_MICROPHONE"
    NO_SPEECH_DETECTED = "NO_SPEECH_DETECTED"
    STT_FAILED = "STT_FAILED"
    STT_UNAVAILABLE = "STT_UNAVAILABLE"
    LOW_TRANSCRIPTION_CONFIDENCE = "LOW_TRANSCRIPTION_CONFIDENCE"
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    NETWORK_ERROR = "NETWORK_ERROR"
    RAG_NO_EVIDENCE = "RAG_NO_EVIDENCE"
    RAG_FAILED = "RAG_FAILED"
    TTS_FAILED = "TTS_FAILED"
    TTS_UNAVAILABLE = "TTS_UNAVAILABLE"
    TTS_UNSUPPORTED_LANGUAGE = "TTS_UNSUPPORTED_LANGUAGE"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    AUDIO_TOO_LARGE = "AUDIO_TOO_LARGE"
    INVALID_AUDIO = "INVALID_AUDIO"
    INVALID_REQUEST = "INVALID_REQUEST"
    VOICE_DISABLED = "VOICE_DISABLED"


FRIENDLY_MESSAGES: dict[str, str] = {
    VoiceErrorCode.MICROPHONE_PERMISSION_DENIED: "Microphone access was blocked. Please allow microphone access in your browser settings and try again.",
    VoiceErrorCode.NO_MICROPHONE: "No microphone was found. Please connect a microphone or type your question instead.",
    VoiceErrorCode.NO_SPEECH_DETECTED: "I didn't hear anything. Please tap the microphone and speak a little closer.",
    VoiceErrorCode.STT_FAILED: "Sorry, I couldn't understand the recording. Please try again or type your question.",
    VoiceErrorCode.STT_UNAVAILABLE: "The speech service is not available right now. You can use your browser's speech recognition or type your question.",
    VoiceErrorCode.LOW_TRANSCRIPTION_CONFIDENCE: "I may not have heard that correctly. Please review the transcription before sending.",
    VoiceErrorCode.UNSUPPORTED_LANGUAGE: "This language isn't fully supported yet. Please review the text, or try English or another Indian language.",
    VoiceErrorCode.NETWORK_ERROR: "Network problem. Please check your connection and try again.",
    VoiceErrorCode.RAG_NO_EVIDENCE: "I could not find sufficient verified BIS information to answer this accurately.",
    VoiceErrorCode.RAG_FAILED: "I couldn't search the BIS knowledge base just now. Please try again in a moment.",
    VoiceErrorCode.TTS_FAILED: "Sorry, I couldn't play the answer aloud. You can still read it on screen.",
    VoiceErrorCode.TTS_UNAVAILABLE: "Voice playback isn't available right now. You can still read the answer on screen.",
    VoiceErrorCode.TTS_UNSUPPORTED_LANGUAGE: "Voice playback isn't available for this language yet. You can still read the answer on screen.",
    VoiceErrorCode.REQUEST_TIMEOUT: "This is taking longer than expected. Please try again.",
    VoiceErrorCode.AUDIO_TOO_LARGE: "That recording is too long. Please ask a shorter question.",
    VoiceErrorCode.INVALID_AUDIO: "The recording couldn't be read. Please try recording again.",
    VoiceErrorCode.INVALID_REQUEST: "Something was wrong with that request. Please try again.",
    VoiceErrorCode.VOICE_DISABLED: "Voice input is turned off. Please type your question.",
}

HTTP_STATUS: dict[str, int] = {
    VoiceErrorCode.NO_SPEECH_DETECTED: 422,
    VoiceErrorCode.STT_FAILED: 502,
    VoiceErrorCode.STT_UNAVAILABLE: 503,
    VoiceErrorCode.NETWORK_ERROR: 502,
    VoiceErrorCode.RAG_FAILED: 502,
    VoiceErrorCode.TTS_FAILED: 502,
    VoiceErrorCode.TTS_UNAVAILABLE: 501,
    VoiceErrorCode.TTS_UNSUPPORTED_LANGUAGE: 422,
    VoiceErrorCode.REQUEST_TIMEOUT: 504,
    VoiceErrorCode.AUDIO_TOO_LARGE: 413,
    VoiceErrorCode.INVALID_AUDIO: 400,
    VoiceErrorCode.INVALID_REQUEST: 400,
    VoiceErrorCode.VOICE_DISABLED: 403,
}


def friendly_message(code: str) -> str:
    return FRIENDLY_MESSAGES.get(code, "Something went wrong. Please try again.")


class VoiceError(Exception):
    """An error with a stable code. ``detail`` is for server logs only."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.detail = detail

    @property
    def http_status(self) -> int:
        return HTTP_STATUS.get(self.code, 500)

    def to_client(self) -> dict:
        return {"error": {"code": self.code, "message": friendly_message(self.code)}}
