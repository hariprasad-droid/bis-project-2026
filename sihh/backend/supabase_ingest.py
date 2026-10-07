"""
Ingest scraped BIS documents into Supabase pgvector.
Uses Hugging Face Inference API for free embeddings (nomic-ai/nomic-embed-text-v1.5, 768 dims).

Ultra RAG (embed_version=2):
  - Chunks are embedded as 'search_document: <title | category>\n<chunk>' (Nomic task prefix +
    contextual header). rag_engine auto-enables the matching 'search_query:' prefix.

Usage:
  python supabase_ingest.py            # ingest (appends rows)
  python supabase_ingest.py --reset    # DELETE all rows first, then re-ingest (recommended once)
  python supabase_ingest.py --all      # no file-count limits
"""
import sys, io, os, json, re, time
if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from dotenv import load_dotenv
import requests
from supabase import create_client

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# Hugging Face Inference API (free, no key needed for public models)
HF_EMBED_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/nomic-ai/nomic-embed-text-v1.5"

DATA_DIR = BASE_DIR / "data" / "raw"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CATEGORY_PATTERNS = [
    (r'hallmark|huid|ahc|jewel|gold', 'Hallmarking'),
    (r'product.certif|scheme.i|isi.mark|conformity|licence', 'Product Certification'),
    (r'qco|quality.control.order|gazette', 'Quality Control Orders'),
    (r'crs|compulsory.registration|electronics|meity', 'CRS / Electronics'),
    (r'fmcs|foreign.manufactur', 'FMCS'),
    (r'water|drinking|is.14543|is.10500', 'Drinking Water'),
    (r'fee|marking.fee|cost|charge', 'Fees & Charges'),
    (r'bis.act|regulation|amendment', 'BIS Act & Regulations'),
    (r'faq|frequently', 'FAQs'),
    (r'consumer|complaint', 'Consumer Affairs'),
]

def detect_category(filename):
    name_lower = filename.lower()
    for pattern, category in CATEGORY_PATTERNS:
        if re.search(pattern, name_lower):
            return category
    return "General"

_embedding_model = None
EMBED_VERSION = 2
DOC_PREFIX = "search_document: "


def _load_model():
    global _embedding_model
    if _embedding_model is None:
        import os
        os.environ["FASTEMBED_CACHE_PATH"] = "/tmp/fastembed_cache"
        from fastembed import TextEmbedding
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            print("Loading fastembed model...", end=" ", flush=True)
            _embedding_model = TextEmbedding("nomic-ai/nomic-embed-text-v1.5")
            print("Done.")
    return _embedding_model


def get_embedding_hf(text):
    """Get 768-dim embedding using fastembed."""
    try:
        emb = list(_load_model().embed([text[:2000]]))[0].tolist()
        return emb
    except Exception as e:
        print(f"    Embedding error: {e}")
        return None


def embed_documents(texts):
    """Batch-embed document texts with the Nomic document prefix."""
    try:
        inputs = [(DOC_PREFIX + t)[:2000] for t in texts]
        return [e.tolist() for e in _load_model().embed(inputs, batch_size=16)]
    except Exception as e:
        print(f"    Batch embedding error: {e}")
        return [get_embedding_hf(DOC_PREFIX + t) for t in texts]

def chunk_text(text, chunk_size=1000, overlap=250):
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        return text_splitter.split_text(text)
    except ImportError:
        # Fallback if langchain is not available
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start += chunk_size - overlap
        return chunks

def ingest_file(filepath, category=None):
    name = filepath.name
    if category is None:
        category = detect_category(name)
    
    print(f"\n{'='*50}")
    print(f"Processing: {name} [{category}]")
    
    try:
        if filepath.suffix in ('.html', '.htm'):
            from bs4 import BeautifulSoup
            raw = filepath.read_text(encoding='utf-8', errors='ignore')
            soup = BeautifulSoup(raw, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            text = soup.get_text(separator='\n', strip=True)
        elif filepath.suffix == '.pdf':
            import fitz
            doc = fitz.open(str(filepath))
            text = ""
            for page in doc:
                text += str(page.get_text("text")) + "\n"
        else:
            text = filepath.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        print(f"  Read error: {e}")
        return 0
    
    if len(text.strip()) < 50:
        print(f"  Too short, skipping")
        return 0
    
    chunks = chunk_text(text)
    print(f"  {len(chunks)} chunks to embed")

    title = name.replace('.txt', '').replace('.html', '').replace('.htm', '').replace('.pdf', '').replace('_', ' ').replace('-', ' ').title()
    header = f"{title} | {category}\n"
    embeddings = embed_documents([header + c for c in chunks])

    rows = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        if embedding is None:
            print(f"  Chunk {i+1}: embedding FAILED")
            continue

        # Ensure 768 dimensions
        if len(embedding) != 768:
            print(f"  Chunk {i+1}: wrong dims ({len(embedding)}), padding/truncating")
            if len(embedding) > 768:
                embedding = embedding[:768]
            else:
                embedding = embedding + [0.0] * (768 - len(embedding))

        meta = {
            "source": str(filepath.relative_to(BASE_DIR)),
            "title": title,
            "category": category,
            "file_type": filepath.suffix.lstrip('.'),
            "chunk_index": i,
            "embed_version": EMBED_VERSION,
        }
        rows.append({"content": chunk, "metadata": meta, "embedding": embedding})

    inserted = 0
    for b in range(0, len(rows), 50):
        batch = rows[b:b + 50]
        try:
            supabase.table("documents").insert(batch).execute()
            inserted += len(batch)
        except Exception as e:
            print(f"  INSERT ERROR (batch {b // 50 + 1}): {e}")
        time.sleep(0.2)  # Rate limiting

    print(f"  => Inserted {inserted}/{len(chunks)} chunks")
    return inserted

def reset_documents():
    """Delete every row in the documents table (used before a full re-ingest)."""
    print("Deleting all existing rows from 'documents'...")
    supabase.table("documents").delete().gte("id", 0).execute()
    print("Done.")

def main():
    args = set(sys.argv[1:])
    no_limit = "--all" in args
    if "--reset" in args:
        confirm = input("This will DELETE all documents in Supabase. Type 'yes' to continue: ")
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            return
        reset_documents()

    total = 0
    
    # 1. Text files
    for f in sorted(DATA_DIR.glob("*.txt")):
        total += ingest_file(f)
    
    # 2. HTML files 
    html_dir = DATA_DIR / "html"
    if html_dir.exists():
        html_files = sorted(list(html_dir.glob("*.html")) + list(html_dir.glob("*.htm")))
        for f in (html_files if no_limit else html_files[:40]):
            total += ingest_file(f)
    
    # 3. PDF files
    pdf_dir = DATA_DIR / "pdf"
    if pdf_dir.exists():
        pdf_files = sorted(pdf_dir.glob("*.pdf"))
        for f in (pdf_files if no_limit else pdf_files[:20]):
            total += ingest_file(f)
    
    print(f"\n{'='*50}")
    print(f"DONE! Total chunks inserted: {total}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
