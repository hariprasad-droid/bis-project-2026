"""
BIS Sahayak voice layer.

This package is an *interface* layer only: it turns speech into text and text
into speech. It never acts as a knowledge source. Every factual answer is still
produced by the BIS RAG engine (``rag_engine``) and validated by
``voice.grounding.GroundingGuard`` before it is shown or spoken.

Modules:
    config              Environment-based configuration
    errors              Error codes + user-friendly messages
    languages           Supported-language registry (per provider)
    language_detection  LanguageDetectionService
    stt                 SpeechToTextService + providers
    tts                 TextToSpeechService + providers
    normalization       Query normalisation / term protection / context
    translation         Translation adapter (term-safe)
    grounding           Evidence + answer validation ("DO NOT GUESS")
    pipeline            VoiceQueryPipeline (voice -> RAG -> verified answer)
    metrics             In-memory latency / quality counters
    router              FastAPI routes (/voice/*)
"""
