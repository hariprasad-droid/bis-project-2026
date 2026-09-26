import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

import chromadb

VECTORSTORE_DIR = BASE_DIR / "vectorstore"

_chroma_client = None
_embedding_function = None
_cross_encoder = None
_cross_encoder_attempted = False

# OpenRouter Free/Community Models in priority order
OPENROUTER_MODELS = [
    "inclusionai/ling-3.0-flash-fin:free",
    "dots-studio/dots-3-note-preview:free",
    "liquid/lfm-2.5-2.6b:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
]

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    return _chroma_client

def get_embedding_function():
    global _embedding_function
    if _embedding_function is None:
        from chromadb.utils import embedding_functions
        _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
    return _embedding_function

def get_cross_encoder():
    global _cross_encoder, _cross_encoder_attempted
    if not _cross_encoder_attempted:
        _cross_encoder_attempted = True
        try:
            from sentence_transformers import CrossEncoder
            _cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)
        except Exception as e:
            print(f"[RAG] Warning: Could not load CrossEncoder: {e}")
            _cross_encoder = None
    return _cross_encoder

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

    if any(w in q_lower for w in ["hallmark", "halmrk", "gold", "silver", "jewel", "huid", "ahc", "refinery"]):
        expanded_terms.append("hallmarking gold jewellery HUID AHC guidelines regulations mandatory hallmarking order gold refinery")
    if any(w in q_lower for w in ["crs", "charger", "mobile", "battery", "laptop", "electronics", "meity", "registration scheme"]):
        expanded_terms.append("Compulsory Registration Scheme CRS IT electronics registration scheme-ii MeitY")
    if any(w in q_lower for w in ["water", "drinking", "packaged", "mineral"]):
        expanded_terms.append("IS 10500 IS 14543 IS 13428 packaged drinking water guidelines specification")
    if any(w in q_lower for w in ["isi", "licence", "license", "factory", "grant"]):
        expanded_terms.append("Product Certification Scheme Scheme-I ISI mark conformity assessment grant of licence")
    if any(w in q_lower for w in ["foreign", "fmcs", "import", "overseas"]):
        expanded_terms.append("Foreign Manufacturers Certification Scheme FMCS")
    if any(w in q_lower for w in ["fee", "cost", "charge", "price", "marking fee"]):
        expanded_terms.append("fee structure marking fee application fee")
    if any(w in q_lower for w in ["qco", "quality control order", "gazette", "notification", "mandatory"]):
        expanded_terms.append("Quality Control Order QCO gazette notification mandatory compulsory certification")
    if any(w in q_lower for w in ["bis act", "regulation", "2016", "amendment"]):
        expanded_terms.append("BIS Act 2016 regulations amendment rules")
    if any(w in q_lower for w in ["steel", "iron", "ferr"]):
        expanded_terms.append("steel iron ferronickel quality control order specification")
    if any(w in q_lower for w in ["chemical", "acid", "polymer", "plastic", "pvc", "polyethylene"]):
        expanded_terms.append("chemical polymer quality control order specification")
    if any(w in q_lower for w in ["textile", "cotton", "yarn", "fibre"]):
        expanded_terms.append("textile cotton yarn fibre quality control order")
    if any(w in q_lower for w in ["food", "fssai", "edible"]):
        expanded_terms.append("food safety FSSAI standards")
    if any(w in q_lower for w in ["solar", "renewable", "pv", "inverter"]):
        expanded_terms.append("solar photovoltaic inverter MNRE renewable energy standards")
    if any(w in q_lower for w in ["electrical", "appliance", "fan", "refrigerat", "ac", "air condition", "washing"]):
        expanded_terms.append("electrical appliance quality control order domestic")
    if any(w in q_lower for w in ["lab", "testing", "recognized"]):
        expanded_terms.append("laboratory testing facility BIS recognized lab")
    if any(w in q_lower for w in ["consumer", "complaint", "grievance"]):
        expanded_terms.append("consumer affairs complaint grievance redressal")
    if any(w in q_lower for w in ["footwear", "shoe", "leather"]):
        expanded_terms.append("footwear leather rubber quality control order")
    if any(w in q_lower for w in ["helmet", "safety", "toy", "bicycle"]):
        expanded_terms.append("helmet safety toy bicycle consumer safety standards")
    if any(w in q_lower for w in ["copper", "alumin", "nickel", "zinc", "tin"]):
        expanded_terms.append("non-ferrous metal copper aluminium nickel zinc tin quality control")

    if expanded_terms:
        return f"{q_clean} {' '.join(expanded_terms)}"
    return q_clean

def retrieve_chunks(query: str, top_k: int = 40):
    """Dense retrieval from ChromaDB knowledge base with boilerplate elimination."""
    search_query = normalize_bis_query(query)
    try:
        collection = get_chroma_client().get_collection(
            name="bis_knowledge_base",
            embedding_function=get_embedding_function()  # type: ignore
        )
    except Exception as e:
        print(f"[RAG] Collection error: {e}")
        return []

    try:
        results = collection.query(
            query_texts=[search_query],
            n_results=top_k,
        )
    except Exception as e:
        print(f"[RAG] Query error: {e}")
        return []

    docs_list = results.get('documents')
    if not docs_list or not docs_list[0]:
        return []

    retrieved = []
    unfiltered = []
    docs = docs_list[0]
    
    metadatas_list = results.get('metadatas')
    metadatas = metadatas_list[0] if metadatas_list else [{}] * len(docs)
    
    distances_list = results.get('distances')
    distances = distances_list[0] if distances_list else [0] * len(docs)

    q_lower = query.lower()
    key_terms = [t for t in [
        "hallmark", "crs", "is 10500", "is 1293", "gold", "water", "fmcs",
        "isi", "charger", "mobile", "jewellery", "qco", "quality control",
        "steel", "chemical", "textile", "footwear", "solar", "electrical",
        "helmet", "bicycle", "copper", "alumin", "food", "fssai",
        "bis act", "regulation", "fee", "lab", "testing", "consumer"
    ] if t in q_lower]

    for doc, meta, dist in zip(docs, metadatas, distances):
        adjusted_dist = dist
        doc_lower = doc.lower()
        title_lower = str(meta.get("title") or meta.get("source") or "").lower()
        category_lower = str(meta.get("category") or "").lower()

        for term in key_terms:
            if term in doc_lower or term in title_lower or term in category_lower:
                adjusted_dist -= 0.08

        entry = {
            "text": doc,
            "metadata": meta,
            "distance": adjusted_dist,
            "raw_distance": dist
        }

        # Track all results (unfiltered fallback)
        unfiltered.append(entry)

        # Skip pure navigation menus
        if not is_boilerplate(doc):
            retrieved.append(entry)

    # If boilerplate filter removed everything, fall back to unfiltered results
    if not retrieved and unfiltered:
        print("[RAG] Warning: All chunks filtered as boilerplate, using unfiltered results")
        retrieved = unfiltered

    retrieved.sort(key=lambda x: x["distance"])
    return retrieved

def rerank_chunks(query: str, chunks: list, top_n: int = 5):
    """Cross-encoder neural reranking."""
    if not chunks:
        return []

    cross_encoder = get_cross_encoder()
    if not cross_encoder:
        return sorted(chunks, key=lambda x: x.get("distance", float('inf')))[:top_n]

    pairs = [[query, chunk['text']] for chunk in chunks]
    try:
        scores = cross_encoder.predict(pairs)
        for i, chunk in enumerate(chunks):
            chunk['rerank_score'] = float(scores[i])
        reranked = sorted(chunks, key=lambda x: x['rerank_score'], reverse=True)
        return reranked[:top_n]
    except Exception as e:
        print(f"[RAG] Cross-encoder error: {e}")
        return sorted(chunks, key=lambda x: x.get("distance", float('inf')))[:top_n]

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
        res = requests.post(url, headers=headers, json=payload, timeout=25)
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
    """Unified multi-tier API orchestrator: Custom -> OpenRouter pool -> Local Ollama."""
    if custom_api_url and custom_model:
        answer = call_custom_openai_llm(messages, custom_api_url, custom_api_key or "", custom_model)
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

def verify_citations(llm_response: str, retrieved_chunks: list) -> list[dict]:
    """Always return the source files used to generate the answer as clickable citations."""
    citations = []
    seen_sources = set()

    # Always include the top reranked sources that were passed to the LLM
    for chunk in retrieved_chunks:
        meta = chunk.get('metadata', {})
        raw_source = meta.get('source', '').replace('\\', '/')
        title = clean_source_name(raw_source)
        category = meta.get('category', '')

        if raw_source in seen_sources:
            continue
        seen_sources.add(raw_source)

        citation = {
            "source": raw_source,
            "title": title,
            "category": category,
            "file_type": meta.get('file_type', ''),
        }
        citations.append(citation)

    return citations


def get_vectorstore_stats() -> dict:
    """Return stats about the vectorstore for the /status endpoint."""
    try:
        collection = get_chroma_client().get_collection(
            name="bis_knowledge_base",
            embedding_function=get_embedding_function()  # type: ignore
        )
        total_chunks = collection.count()

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

        # Vectorstore size on disk
        vs_size = 0
        vs_dir = BASE_DIR / "vectorstore"
        if vs_dir.exists():
            for f in vs_dir.rglob("*"):
                if f.is_file():
                    vs_size += f.stat().st_size

        return {
            "total_chunks": total_chunks,
            "total_files": total_files,
            "vectorstore_size_mb": round(vs_size / (1024 * 1024), 1),
            "categories": categories,
            "status": "ready" if total_chunks > 0 else "empty",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def generate_answer(query: str, history: list | None = None, top_k: int = 15, custom_api_url: str | None = None, custom_api_key: str | None = None, custom_model: str | None = None) -> dict:
    """End-to-end RAG workflow over BIS Knowledge Base."""
    initial_chunks = retrieve_chunks(query, top_k=40)
    if not initial_chunks:
        return {
            "answer": "I do not have that information in my knowledge base. Please try rephrasing your question, or ask about BIS certifications, hallmarking, product standards, or quality control orders.",
            "citations": [],
            "confidence": "low"
        }

    best_chunks = rerank_chunks(query, initial_chunks, top_n=5)

    # Check if top chunk meets minimum relevance
    top_chunk = best_chunks[0]
    if top_chunk.get('distance', 1.0) > 0.65 and top_chunk.get('rerank_score', 0) < -8.0:
        return {
            "answer": "I do not have sufficient information in my knowledge base to answer this accurately. Please try asking about specific BIS topics like hallmarking, ISI mark, CRS, or product certification.",
            "citations": [],
            "confidence": "low"
        }

    # Format context — include source file path explicitly so the LLM can reference it
    context_parts = []
    for i, chunk in enumerate(best_chunks):
        raw_source = chunk['metadata'].get('source', '')
        title = clean_source_name(raw_source)
        category = chunk['metadata'].get('category', 'General')
        text = chunk['text'].strip()
        context_parts.append(
            f"--- SOURCE {i+1}: {title} (Category: {category}) [File: {raw_source}] ---\n{text}"
        )

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
        "4. At the end, briefly mention which source documents were used.\n"
        "5. If the context does not contain the answer, say: 'I do not have that information in my knowledge base.'\n"
        "6. Be concise but thorough. Aim for clear, actionable, well-structured answers.\n\n"
        f"BIS OFFICIAL CONTEXT:\n{context_str}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})

    answer = omni_llm_generate(messages, custom_api_url, custom_api_key, custom_model)

    if not answer:
        # Fallback: return best chunks as raw text
        top_snippet = best_chunks[0]['text'][:500]
        top_title = clean_source_name(best_chunks[0]['metadata'].get('source', ''))
        answer = (
            f"Based on official BIS documentation ({top_title}):\n\n"
            f"{top_snippet}...\n\n"
            f"(Source: {top_title})"
        )

    citations = verify_citations(answer, best_chunks)
    
    # Determine confidence based on retrieval quality
    top_dist = best_chunks[0].get('distance', 1.0)
    top_rerank = best_chunks[0].get('rerank_score', 0)
    if top_dist < 0.35 or top_rerank > -2.0:
        confidence = "high"
    elif top_dist < 0.50 or top_rerank > -5.0:
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
