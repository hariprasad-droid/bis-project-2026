import os
import re
import requests
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from supabase import create_client, Client


SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

_supabase_client = None

def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client

_embedding_model = None
def get_embedding(text: str) -> list[float]:
    """Get 768-dim embedding using local sentence-transformers, fallback to HF API on Vercel."""
    global _embedding_model
    try:
        from sentence_transformers import SentenceTransformer
        if _embedding_model is None:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                _embedding_model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
        
        # Generate embedding
        emb = _embedding_model.encode(text[:2000])
        emb_list = emb.tolist()
        
        # Ensure 768 dims
        if len(emb_list) > 768:
            emb_list = emb_list[:768]
        elif len(emb_list) < 768:
            emb_list = emb_list + [0.0] * (768 - len(emb_list))
        return emb_list
    except ImportError:
        # Fallback for Vercel/Render
        try:
            import os
            os.environ["FASTEMBED_CACHE_PATH"] = "/tmp/fastembed_cache"
            from fastembed import TextEmbedding
            if _embedding_model is None:
                _embedding_model = TextEmbedding("nomic-ai/nomic-embed-text-v1.5")
            
            emb = list(_embedding_model.embed([text[:2000]]))[0].tolist()
            if len(emb) > 768:
                emb = emb[:768]
            elif len(emb) < 768:
                emb = emb + [0.0] * (768 - len(emb))
            return emb
        except ImportError:
            # Fallback to HuggingFace if fastembed is not installed
            import requests
            import time
            import os
            HF_EMBED_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/nomic-ai/nomic-embed-text-v1.5"
            payload = {"inputs": text[:2000], "options": {"wait_for_model": True}}
            headers = {}
            hf_token = os.environ.get("HF_TOKEN")
            if hf_token:
                headers["Authorization"] = f"Bearer {hf_token}"
            for attempt in range(3):
                try:
                    response = requests.post(HF_EMBED_URL, headers=headers, json=payload, timeout=30)
                    if response.status_code == 200:
                        emb = response.json()
                        if isinstance(emb, list) and len(emb) > 0:
                            if isinstance(emb[0], list):
                                n = len(emb)
                                dim = len(emb[0])
                                pooled = [sum(emb[t][d] for t in range(n)) / n for d in range(dim)]
                                if len(pooled) > 768:
                                    pooled = pooled[:768]
                                elif len(pooled) < 768:
                                    pooled = pooled + [0.0] * (768 - len(pooled))
                                return pooled
                            return emb
                    else:
                        print(f"[Embed] HF API Error: {response.status_code} - {response.text}")
                    if response.status_code == 503:
                        time.sleep(3)
                except Exception as e:
                    print(f"[Embed] HF API Exception: {e}")
                    time.sleep(1)
            return []


def is_boilerplate(text: str) -> bool:
    """Filter out scraped navigation bar fragments from HTML pages."""
    nav_markers = [
        "Solar Power Initiative", "Pensioners", "Directory", "Enquiry",
        "Head Quarter", "Comic Books", "BIS Logo Guidelines", "Sales Office", "Regional Office"
    ]
    matches = sum(1 for m in nav_markers if m.lower() in text.lower())
    # Require at least 5 markers to be considered boilerplate (was 3, too aggressive)
    return matches >= 5

def clean_source_name(source: str) -> str:
    """Format file path into clean, readable citation title."""
    if not source:
        return "BIS Guidelines"
    name = Path(source).stem
    name = re.sub(r'^wp[-_]content[-_]uploads[-_]\d+[-_]\d+[-_]', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^[a-z]+[\\/]', '', name)
    name = re.sub(r'_lang-[a-z]+', '', name)
    name = re.sub(r'[-_]', ' ', name).strip()
    # URL decode percent-encoded chars
    try:
        from urllib.parse import unquote
        name = unquote(name)
    except Exception:
        pass
    return name.title()

def normalize_bis_query(query: str) -> str:
    """Expands informal queries into rich BIS search concepts."""
    q_clean = query.strip()
    q_lower = q_clean.lower()
    expanded_terms = []

    # Detect Indian Standard patterns
    is_match = re.findall(r'\b(is\s*\d+)\b', q_lower)
    if is_match:
        for m in is_match:
            expanded_terms.append(m.upper())

    if _has_any(q_lower, ["hallmark", "halmrk", "gold", "silver", "jewel", "huid", "ahc", "refinery"]):
        expanded_terms.append("hallmarking gold jewellery HUID AHC guidelines regulations mandatory hallmarking order gold refinery")
    if _has_any(q_lower, ["crs", "charger", "mobile", "battery", "laptop", "electronics", "meity", "registration scheme"]):
        expanded_terms.append("Compulsory Registration Scheme CRS IT electronics registration scheme-ii MeitY")
    if _has_any(q_lower, ["water", "drinking", "packaged", "mineral"]):
        expanded_terms.append("IS 10500 IS 14543 IS 13428 packaged drinking water guidelines specification")
    if _has_any(q_lower, ["isi", "licence", "license", "factory", "grant"]):
        expanded_terms.append("Product Certification Scheme Scheme-I ISI mark conformity assessment grant of licence")
    if _has_any(q_lower, ["foreign", "fmcs", "import", "overseas"]):
        expanded_terms.append("Foreign Manufacturers Certification Scheme FMCS")
    if _has_any(q_lower, ["fee", "cost", "charge", "price", "marking fee"]):
        expanded_terms.append("fee structure marking fee application fee")
    if _has_any(q_lower, ["qco", "quality control order", "gazette", "notification", "mandatory"]):
        expanded_terms.append("Quality Control Order QCO gazette notification mandatory compulsory certification")
    if _has_any(q_lower, ["bis act", "regulation", "2016", "amendment"]):
        expanded_terms.append("BIS Act 2016 regulations amendment rules")
    if _has_any(q_lower, ["steel", "iron", "ferr"]):
        expanded_terms.append("steel iron ferronickel quality control order specification")
    if _has_any(q_lower, ["chemical", "acid", "polymer", "plastic", "pvc", "polyethylene"]):
        expanded_terms.append("chemical polymer quality control order specification")
    if _has_any(q_lower, ["textile", "cotton", "yarn", "fibre"]):
        expanded_terms.append("textile cotton yarn fibre quality control order")
    if _has_any(q_lower, ["food", "fssai", "edible"]):
        expanded_terms.append("food safety FSSAI standards")
    if _has_any(q_lower, ["solar", "renewable", "pv", "inverter"]):
        expanded_terms.append("solar photovoltaic inverter MNRE renewable energy standards")
    if _has_any(q_lower, ["electrical", "appliance", "fan", "refrigerat", "ac", "air condition", "washing"]):
        expanded_terms.append("electrical appliance quality control order domestic")
    if _has_any(q_lower, ["lab", "testing", "recognized"]):
        expanded_terms.append("laboratory testing facility BIS recognized lab")
    if _has_any(q_lower, ["consumer", "complaint", "grievance"]):
        expanded_terms.append("consumer affairs complaint grievance redressal")
    if _has_any(q_lower, ["footwear", "shoe", "leather"]):
        expanded_terms.append("footwear leather rubber quality control order")
    if _has_any(q_lower, ["helmet", "safety", "toy", "bicycle"]):
        expanded_terms.append("helmet safety toy bicycle consumer safety standards")
    if _has_any(q_lower, ["copper", "alumin", "nickel", "zinc", "tin"]):
        expanded_terms.append("non-ferrous metal copper aluminium nickel zinc tin quality control")

    if expanded_terms:
        return f"{q_clean} {' '.join(expanded_terms)}"
    return q_clean

# OpenRouter Free/Community Models in priority order
OPENROUTER_MODELS = [
    "inclusionai/ling-3.0-flash-fin:free",
    "dots-studio/dots-3-note-preview:free",
    "liquid/lfm-2.5-2.6b:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
]

# ---------------------------------------------------------------------------
# Query understanding helpers
# ---------------------------------------------------------------------------

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "am", "do", "does", "did",
    "what", "which", "who", "whom", "how", "why", "when", "where", "can", "could", "should",
    "would", "will", "shall", "may", "might", "must", "i", "me", "my", "we", "our", "you",
    "your", "it", "its", "this", "that", "these", "those", "they", "them", "their", "of",
    "in", "on", "at", "to", "for", "from", "by", "with", "about", "and", "or", "not", "no",
    "if", "so", "as", "than", "then", "there", "here", "any", "all", "some", "get", "tell",
    "please", "explain", "give", "need", "want", "know", "under", "into", "also", "much",
    "many", "more", "bis", "india", "indian",
}

KEY_TERMS = [
    "hallmark", "crs", "is 10500", "is 1293", "gold", "water", "fmcs",
    "isi", "charger", "mobile", "jewellery", "qco", "quality control",
    "steel", "chemical", "textile", "footwear", "solar", "electrical",
    "helmet", "bicycle", "copper", "alumin", "food", "fssai",
    "bis act", "regulation", "fee", "lab", "testing", "consumer"
]

_FOLLOWUP_RE = re.compile(
    r"\b(it|its|this|that|these|those|they|them|their|same|above|what about|how about|and for|also)\b"
)


def _has_any(text: str, words: list[str]) -> bool:
    """Word-boundary keyword match. Short words (<=3 chars) must match a whole word,
    longer words may match a word prefix (e.g. 'hallmark' -> 'hallmarking')."""
    for w in words:
        pattern = rf"\b{re.escape(w)}\b" if len(w) <= 3 else rf"\b{re.escape(w)}"
        if re.search(pattern, text):
            return True
    return False


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _content_terms(text: str) -> list[str]:
    seen: list[str] = []
    for t in _tokens(text):
        if len(t) >= 2 and t not in STOPWORDS and t not in seen:
            seen.append(t)
    return seen


def extract_is_numbers(query: str) -> list[str]:
    """Find Indian Standard numbers: 'IS 10500', 'is10500', 'IS 1293:2019', 'IS/ISO 9001'."""
    nums = re.findall(r"\bis\s*[/:-]?\s*(?:iso\s*)?(\d{3,6})\b", query.lower())
    return list(dict.fromkeys(nums))


def bis_expansion_terms(query: str) -> str:
    """Domain expansion terms only (without the original query)."""
    q_clean = query.strip()
    expanded = normalize_bis_query(q_clean)
    return expanded[len(q_clean):].strip()


def build_keyword_query(query: str) -> str:
    """OR-joined keyword string for Postgres websearch_to_tsquery."""
    terms = _content_terms(query) + extract_is_numbers(query) + _content_terms(bis_expansion_terms(query))
    terms = list(dict.fromkeys(terms))[:40]
    return " or ".join(terms)


def contextualize_query(query: str, history: list | None) -> str:
    """Turn short follow-ups ('what about its fee?') into standalone search queries
    by prepending the previous user question."""
    if not history:
        return query
    if len(query.split()) > 8 or not _FOLLOWUP_RE.search(query.lower()):
        return query
    for msg in reversed(history):
        content = str(msg.get("content", "")).strip()
        if msg.get("role") == "user" and content and content.lower() != query.strip().lower():
            return f"{content[:300]} {query}"
    return query


# ---------------------------------------------------------------------------
# Embeddings (Nomic v1.5 task prefixes)
# ---------------------------------------------------------------------------

_prefix_mode: bool | None = None


def use_nomic_prefixes() -> bool:
    """Nomic v1.5 expects 'search_query:' / 'search_document:' prefixes. Only enable the
    query prefix once documents were re-ingested with the document prefix (embed_version=2).
    Override with NOMIC_PREFIXES=on|off."""
    global _prefix_mode
    env = os.environ.get("NOMIC_PREFIXES", "auto").lower()
    if env in ("1", "true", "on", "yes"):
        return True
    if env in ("0", "false", "off", "no"):
        return False
    if _prefix_mode is None:
        try:
            res = (get_supabase_client().table("documents").select("id")
                   .eq("metadata->>embed_version", "2").limit(1).execute())
            _prefix_mode = bool(res.data)
        except Exception as e:
            print(f"[RAG] Prefix auto-detect failed, disabling prefixes: {e}")
            _prefix_mode = False
        print(f"[RAG] Nomic task prefixes: {'ON' if _prefix_mode else 'OFF'}")
    return _prefix_mode


def embed_query(text: str) -> list[float]:
    prefix = "search_query: " if use_nomic_prefixes() else ""
    return get_embedding(prefix + text)


# ---------------------------------------------------------------------------
# Retrieval: hybrid (keyword + vector, RRF) with dense-only fallback
# ---------------------------------------------------------------------------

_hybrid_available = True


def _search_supabase(keyword_query: str, embedding: list[float], top_k: int) -> tuple[list, str]:
    global _hybrid_available
    client = get_supabase_client()
    if _hybrid_available and keyword_query:
        try:
            resp = client.rpc("hybrid_search", {
                "query_text": keyword_query,
                "query_embedding": embedding,
                "match_count": top_k,
            }).execute()
            return _as_list(resp.data), "hybrid"
        except Exception as e:
            msg = str(e)
            if "hybrid_search" in msg or "PGRST202" in msg or "fts" in msg:
                print("[RAG] hybrid_search RPC missing - run supabase_setup.sql. Using dense search.")
                _hybrid_available = False
            else:
                print(f"[RAG] hybrid_search error, falling back to dense: {e}")
    resp = client.rpc(
        "match_documents",
        {"query_embedding": embedding, "match_threshold": 0.0, "match_count": top_k},
    ).execute()
    return _as_list(resp.data), "dense"


def _as_list(data: object) -> list:
    """Supabase RPC data is typed as generic JSON; we only accept a list of rows."""
    return data if isinstance(data, list) else []


def retrieve_chunks(query: str, top_k: int = 40):
    """Hybrid retrieval from Supabase (full-text + pgvector fused with RRF)."""
    is_nums = extract_is_numbers(query)
    # Embed the user's own words (+ IS numbers); domain expansions go to the keyword side.
    dense_text = query if not is_nums else f"{query} " + " ".join(f"IS {n}" for n in is_nums)
    keyword_query = build_keyword_query(query)
    try:
        query_embedding = embed_query(dense_text)
        if not query_embedding:
            print("[RAG] Empty query embedding")
            return []
        docs_list, mode = _search_supabase(keyword_query, query_embedding, top_k)
    except Exception as e:
        print(f"[RAG] Supabase Query error: {e}")
        return []

    if not isinstance(docs_list, list):
        return []

    retrieved = []
    for item in docs_list:
        if not isinstance(item, dict):
            continue
        meta = item.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        try:
            sim = float(item.get("similarity") or 0.0)
        except (TypeError, ValueError):
            sim = 0.0
        try:
            rrf = float(item.get("score") or 0.0)
        except (TypeError, ValueError):
            rrf = 0.0
        retrieved.append({
            "id": item.get("id"),
            "text": str(item.get("content", "")),
            "metadata": meta,
            "similarity": sim,
            "distance": 1.0 - sim,
            "raw_distance": 1.0 - sim,
            "rrf": rrf,
            "keyword_rank": item.get("keyword_rank"),
            "retrieval_mode": mode,
        })
    print(f"[RAG] Retrieved {len(retrieved)} candidates via {mode} search")
    return retrieved


# ---------------------------------------------------------------------------
# Reranking
# ---------------------------------------------------------------------------

_cross_encoder: Any = None
_cross_encoder_kind = ""
_cross_encoder_failed = False


def _cross_encoder_scores(query: str, texts: list[str]) -> list[float] | None:
    """Optional cross-encoder. Enabled with ENABLE_CROSS_ENCODER=1 (downloads a model)."""
    global _cross_encoder, _cross_encoder_kind, _cross_encoder_failed
    if _cross_encoder_failed or os.environ.get("ENABLE_CROSS_ENCODER", "0").lower() not in ("1", "true", "on", "yes"):
        return None
    model_name = os.environ.get("CROSS_ENCODER_MODEL", "Xenova/ms-marco-MiniLM-L-6-v2")
    try:
        if _cross_encoder is None:
            try:
                from fastembed.rerank.cross_encoder import TextCrossEncoder
                _cross_encoder = TextCrossEncoder(model_name=model_name)
                _cross_encoder_kind = "fastembed"
            except ImportError:
                from sentence_transformers import CrossEncoder
                _cross_encoder = CrossEncoder(os.environ.get("CROSS_ENCODER_MODEL", "BAAI/bge-reranker-base"))
                _cross_encoder_kind = "st"
            print(f"[RAG] Cross-encoder loaded ({_cross_encoder_kind})")
        model: Any = _cross_encoder
        if _cross_encoder_kind == "fastembed":
            raw = list(model.rerank(query, texts))
        else:
            raw = list(model.predict([(query, t) for t in texts]))
        import math
        return [1.0 / (1.0 + math.exp(-float(s))) for s in raw]
    except Exception as e:
        print(f"[RAG] Cross-encoder unavailable, using heuristic rerank: {e}")
        _cross_encoder_failed = True
        return None


def _prefix_set(tokens: list[str]) -> set[str]:
    return {t[:5] for t in tokens}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def rerank_chunks(query: str, chunks: list, top_n: int = 5):
    """Score candidates on semantic similarity, fused rank, lexical overlap, exact IS-number
    match and boilerplate; optionally blend a cross-encoder. Then pick a diverse top_n."""
    if not chunks:
        return []

    q_lower = query.lower()
    q_terms = _content_terms(query)
    q_prefixes = {t[:5] for t in q_terms}
    is_nums = extract_is_numbers(query)
    key_terms = [t for t in KEY_TERMS if t in q_lower]
    max_rrf = max((c.get("rrf", 0.0) for c in chunks), default=0.0) or 1.0

    for c in chunks:
        text = c["text"]
        meta = c["metadata"]
        haystack = f"{text} {meta.get('title', '')} {meta.get('source', '')}".lower()
        tokens = _tokens(haystack)
        c["_tokset"] = set(_tokens(text))
        doc_prefixes = _prefix_set(tokens)

        overlap = (len(q_prefixes & doc_prefixes) / len(q_prefixes)) if q_prefixes else 0.0
        is_match = any(re.search(rf"\b(?:is\s*[/:-]?\s*(?:iso\s*)?)?{n}\b", haystack) for n in is_nums)
        key_hits = sum(1 for t in key_terms if t in haystack)
        rrf_norm = c.get("rrf", 0.0) / max_rrf if c.get("rrf") else 0.0

        score = (0.40 * c.get("similarity", 0.0)
                 + 0.25 * overlap
                 + 0.20 * rrf_norm
                 + (0.15 if is_match else 0.0)
                 + min(0.06, 0.02 * key_hits))
        if is_boilerplate(text):
            score -= 0.30
        if len(text.strip()) < 80:
            score -= 0.10

        c["lexical_overlap"] = round(overlap, 3)
        c["is_match"] = is_match
        c["heuristic_score"] = score
        c["rerank_score"] = score

    # Optional cross-encoder on the top 20 heuristic candidates
    chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
    head = chunks[:20]
    ce = _cross_encoder_scores(query, [c["text"][:1500] for c in head])
    if ce:
        for c, s in zip(head, ce):
            c["cross_encoder"] = s
            c["rerank_score"] = 0.6 * s + 0.4 * c["heuristic_score"]
        chunks.sort(key=lambda x: x["rerank_score"], reverse=True)

    # Diversity: max 2 chunks per source, drop near-duplicates
    selected: list = []
    per_source: dict[str, int] = {}
    for c in chunks:
        src = str(c["metadata"].get("source", ""))
        if per_source.get(src, 0) >= 2:
            continue
        if any(_jaccard(c["_tokset"], s["_tokset"]) > 0.8 for s in selected):
            continue
        selected.append(c)
        per_source[src] = per_source.get(src, 0) + 1
        if len(selected) >= top_n:
            break

    for c in chunks:
        c.pop("_tokset", None)
    return selected or chunks[:top_n]

def call_openrouter_llm(messages: list, api_key: str) -> str | None:
    """Executes completion across OpenRouter candidate models with fast fallback."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://bis.gov.in",
        "X-Title": "BIS AI Assistant"
    }

    for model_name in OPENROUTER_MODELS:
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1500,
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    print(f"[OmniLLM] Answered using OpenRouter model: {model_name}")
                    return content
            else:
                print(f"[OmniLLM] Model {model_name} status: {res.status_code}")
        except Exception as err:
            print(f"[OmniLLM] Model {model_name} timeout/error: {err}")

    return None

def call_local_ollama(messages: list, host: str = "http://localhost:11434") -> str | None:
    """Fallback to local Ollama instance on user machine."""
    try:
        tags_res = requests.get(f"{host}/api/tags", timeout=2)
        if tags_res.status_code != 200:
            return None
        available_models = [m["name"] for m in tags_res.json().get("models", [])]
        
        target_model = None
        for cand in ["llama3.2-vision:latest", "gemma4:31b-cloud"]:
            if cand in available_models:
                target_model = cand
                break
        if not target_model and available_models:
            target_model = available_models[0]

        if not target_model:
            return None

        ollama_payload = {
            "model": target_model,
            "messages": messages,
            "stream": False
        }
        res = requests.post(f"{host}/api/chat", json=ollama_payload, timeout=25)
        if res.status_code == 200:
            content = res.json().get("message", {}).get("content", "").strip()
            if content:
                print(f"[OmniLLM] Answered using local Ollama ({target_model})")
                return content
    except Exception as e:
        print(f"[OmniLLM] Local Ollama fallback error: {e}")
    return None

def call_custom_openai_llm(messages: list, url: str, api_key: str, model_name: str) -> str | None:
    """Executes completion against a custom OpenAI-compatible endpoint."""
    headers = {
        "Content-Type": "application/json"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1500,
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=25, verify=False)
        if res.status_code == 200:
            data = res.json()
            content = data["choices"][0]["message"]["content"].strip()
            if content:
                print(f"[OmniLLM] Answered using custom API model: {model_name}")
                return content
        else:
            print(f"[OmniLLM] Custom API status: {res.status_code}, error: {res.text}")
    except Exception as err:
        print(f"[OmniLLM] Custom API error: {err}")
    return None

def omni_llm_generate(messages: list, custom_api_url: str | None = None, custom_api_key: str | None = None, custom_model: str | None = None) -> str | None:
    """Unified multi-tier API orchestrator: Custom -> Ollama Cloud -> OpenRouter pool -> Local Ollama."""
    if custom_api_url and custom_model:
        answer = call_custom_openai_llm(messages, custom_api_url, custom_api_key or "", custom_model)
        if answer:
            return answer

    ollama_cloud_url = os.getenv("OLLAMA_CLOUD_URL")
    ollama_cloud_key = os.getenv("OLLAMA_CLOUD_API_KEY")
    ollama_cloud_model = os.getenv("OLLAMA_CLOUD_MODEL")
    if ollama_cloud_url and ollama_cloud_key and ollama_cloud_model:
        answer = call_custom_openai_llm(messages, ollama_cloud_url, ollama_cloud_key, ollama_cloud_model)
        if answer:
            return answer

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        answer = call_openrouter_llm(messages, openrouter_key)
        if answer:
            return answer

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    local_answer = call_local_ollama(messages, ollama_host)
    if local_answer:
        return local_answer

    return None

def extract_cited_indices(llm_response: str, n_sources: int) -> list[int]:
    """Find inline citation markers like [1], [2, 3], [1][4] in the answer (1-based)."""
    found: list[int] = []
    for group in re.findall(r"\[(\d+(?:\s*[,;&]\s*\d+)*)\]", llm_response or ""):
        for num in re.findall(r"\d+", group):
            idx = int(num)
            if 1 <= idx <= n_sources and idx not in found:
                found.append(idx)
    return found


def verify_citations(llm_response: str, retrieved_chunks: list) -> list[dict]:
    """Return only sources the answer actually cites ([n] markers). Falls back to the
    top 3 context sources when the model did not cite inline."""
    cited = extract_cited_indices(llm_response, len(retrieved_chunks))
    grounded = bool(cited)
    if not cited:
        cited = list(range(1, min(3, len(retrieved_chunks)) + 1))

    citations: list[dict] = []
    by_source: dict[str, dict] = {}
    for idx in cited:
        chunk = retrieved_chunks[idx - 1]
        meta = chunk.get('metadata', {}) or {}
        raw_source = str(meta.get('source', '')).replace('\\', '/')
        if raw_source in by_source:
            by_source[raw_source]["indices"].append(idx)
            continue
        snippet = re.sub(r"\s+", " ", chunk.get('text', '')).strip()[:240]
        citation = {
            "index": idx,
            "indices": [idx],
            "source": raw_source,
            "title": meta.get('title') or clean_source_name(raw_source),
            "category": meta.get('category', ''),
            "file_type": meta.get('file_type', ''),
            "url": meta.get('url', ''),
            "snippet": snippet,
            "cited": grounded,
        }
        by_source[raw_source] = citation
        citations.append(citation)

    return citations


def get_vectorstore_stats() -> dict:
    """Return stats about the vectorstore for the /status endpoint."""
    from postgrest.types import CountMethod
    try:
        client = get_supabase_client()
        # Basic count
        response = client.table('documents').select('id', count=CountMethod.exact).limit(1).execute()
        total_chunks = response.count or 0

        # Count sources from sources.json
        sources_file = BASE_DIR / "sources.json"
        total_files = 0
        categories = {}
        if sources_file.exists():
            import json
            with open(sources_file, "r", encoding="utf-8") as f:
                sources = json.load(f)
            total_files = len(sources)
            for info in sources.values():
                cat = info.get("category", "General")
                categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_chunks": total_chunks,
            "total_files": total_files,
            "vectorstore_size_mb": 0.0, # Managed by Supabase
            "categories": categories,
            "status": "ready" if total_chunks > 0 else "empty",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def generate_answer(query: str, history: list | None = None, top_k: int = 15, custom_api_url: str | None = None, custom_api_key: str | None = None, custom_model: str | None = None) -> dict:
    """End-to-end RAG workflow over BIS Knowledge Base."""
    search_query = contextualize_query(query, history)
    if search_query != query:
        print(f"[RAG] Follow-up rewritten for retrieval: {search_query[:120]}")
    initial_chunks = retrieve_chunks(search_query, top_k=40)
    if not initial_chunks:
        return {
            "answer": "I do not have that information in my knowledge base. Please try rephrasing your question, or ask about BIS certifications, hallmarking, product standards, or quality control orders.",
            "citations": [],
            "confidence": "low"
        }

    best_chunks = rerank_chunks(search_query, initial_chunks, top_n=6)

    # Relevance gate: nothing semantically close, no keyword overlap, no IS-number hit
    top_chunk = best_chunks[0]
    if (top_chunk.get('similarity', 0.0) < 0.35
            and top_chunk.get('lexical_overlap', 0.0) < 0.2
            and not top_chunk.get('is_match')):
        return {
            "answer": "I do not have sufficient information in my knowledge base to answer this accurately. Please try asking about specific BIS topics like hallmarking, ISI mark, CRS, or product certification.",
            "citations": [],
            "confidence": "low"
        }

    # Numbered context so the LLM can cite inline as [1], [2], ...
    context_parts = []
    for i, chunk in enumerate(best_chunks):
        meta = chunk['metadata']
        raw_source = meta.get('source', '')
        title = meta.get('title') or clean_source_name(raw_source)
        category = meta.get('category', 'General')
        text = chunk['text'].strip()
        context_parts.append(f"[{i+1}] {title} (Category: {category})\n{text}")

    context_str = "\n\n".join(context_parts)

    system_prompt = (
        "You are the official AI Conversational Assistant for the Bureau of Indian Standards (BIS).\n"
        "Your task is to provide accurate, professional, and helpful answers regarding Indian Standards, "
        "Hallmarking, CRS, Product Certification (ISI), Quality Control Orders (QCO), and BIS guidelines.\n\n"
        "RESPONSE FORMATTING RULES (VERY IMPORTANT):\n"
        "- Use clean **Markdown** formatting like ChatGPT or Claude.\n"
        "- Use `## Heading` for section titles when the answer has multiple sections.\n"
        "- Use **bold** for key terms, standard numbers, and important phrases.\n"
        "- Use bullet points (`-`) for listing items, features, or requirements.\n"
        "- Use numbered lists (`1.`, `2.`, `3.`) for sequential steps or processes.\n"
        "- Use Markdown tables (`| Header | Header |`) when comparing items, listing fees, or showing structured data.\n"
        "- Use `> blockquote` for quoting official BIS text verbatim.\n"
        "- NEVER use raw asterisks like `***` or `---` as separators.\n"
        "- NEVER dump unformatted walls of text. Break everything into readable sections.\n"
        "- Keep paragraphs short (2-3 sentences max).\n\n"
        "CONTENT GUIDELINES:\n"
        "1. Understand the user's intent even if their query is colloquial, informal, or misspelled.\n"
        "2. Base your response STRICTLY and ONLY on the provided BIS CONTEXT below. Do NOT fabricate or extrapolate.\n"
        "3. Mention specific Indian Standard numbers (e.g., **IS 10500**, **IS 1293**) where applicable.\n"
        "4. CITE SOURCES INLINE: after every factual sentence or bullet, add the number of the context "
        "source it came from in square brackets, e.g. `[1]` or `[2][3]`. Only use numbers that exist in the context. "
        "Do not add a separate sources list at the end.\n"
        "5. If the context does not contain the answer, say: 'I do not have that information in my knowledge base.'\n"
        "6. If sources disagree, prefer the most specific/recent one and mention the difference.\n"
        "7. Be concise but thorough. Aim for clear, actionable, well-structured answers.\n\n"
        f"BIS OFFICIAL CONTEXT:\n{context_str}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})

    answer = omni_llm_generate(messages, custom_api_url, custom_api_key, custom_model)

    if not answer:
        # Fallback: return best chunk as raw text
        top_snippet = best_chunks[0]['text'][:500]
        top_title = best_chunks[0]['metadata'].get('title') or clean_source_name(best_chunks[0]['metadata'].get('source', ''))
        answer = (
            f"Based on official BIS documentation ({top_title}):\n\n"
            f"{top_snippet}... [1]"
        )

    no_info = "do not have that information" in answer.lower()
    citations = [] if no_info else verify_citations(answer, best_chunks)
    grounded = any(c.get("cited") for c in citations)

    # Confidence from rerank score, semantic similarity, exact IS match and citation grounding
    top_score = top_chunk.get('rerank_score', 0.0)
    strong_signal = top_chunk.get('similarity', 0.0) >= 0.5 or top_chunk.get('is_match')
    if no_info:
        confidence = "low"
    elif top_score >= 0.55 and strong_signal and grounded:
        confidence = "high"
    elif top_score >= 0.40:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "answer": answer,
        "citations": citations,
        "confidence": confidence
    }


if __name__ == "__main__":
    queries = [
        "What is the hallmarking process for gold jewellery?",
        "What are the specifications and requirements for packaged drinking water under IS 10500?",
        "What is CRS scheme for electronics?",
        "What is ISI mark and how to get it?",
        "What are Quality Control Orders?"
    ]
    for q in queries:
        print(f"\n========================================\nQuery: {q}")
        res = generate_answer(q)
        print("\nANSWER:")
        print(res["answer"][:500])
        print("\nCITATIONS:")
        for c in res["citations"]:
            print(f"  - {c['title']} ({c.get('category', '')}) -> {c['source']}")
        print(f"CONFIDENCE: {res['confidence']}")
