import sys
import io
if isinstance(sys.stdout, io.TextIOWrapper) and \
    sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
import os
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from chromadb.utils import embedding_functions

# Constants
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
SOURCES_FILE = BASE_DIR / "sources.json"

# We use sentence-transformers via chromadb's default embedding function or specifically request it.
# SentenceTransformerEmbeddingFunction uses 'all-MiniLM-L6-v2' by default which is local and good for general text.
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
collection = chroma_client.get_or_create_collection(
    name="bis_knowledge_base",
    embedding_function=embedding_function  # type: ignore
)

# Category detection patterns — maps filename/path keywords to a category
CATEGORY_PATTERNS = [
    (r'hallmark|huid|ahc|jewel|gold.refin|gold.monetiz', 'Hallmarking'),
    (r'product.certif|scheme.i|isi.mark|conformity|grant.of.licen', 'Product Certification'),
    (r'qco|quality.control.order|gazette|notification', 'Quality Control Orders'),
    (r'crs|compulsory.registration|electronics|meity|it.goods', 'CRS / Electronics'),
    (r'fmcs|foreign.manufactur', 'FMCS'),
    (r'water|drinking|is.14543|is.10500|is.13428', 'Drinking Water'),
    (r'steel|iron|ferr', 'Steel & Iron'),
    (r'chemical|acid|methanol|aniline|toluene|vinyl|acryl|poly', 'Chemicals & Polymers'),
    (r'textile|cotton|polyester|yarn|fibre|fabric|jute', 'Textiles'),
    (r'food|fssai|edible', 'Food Safety'),
    (r'footwear|leather|rubber', 'Footwear'),
    (r'solar|renewable|mnre', 'Solar & Renewable Energy'),
    (r'toy|bicycle|helmet|safety', 'Consumer Safety Products'),
    (r'electrical|appliance|fan|refrigerat|air.condition|washing', 'Electrical Appliances'),
    (r'copper|alumin|nickel|zinc|tin', 'Non-Ferrous Metals'),
    (r'annual.report|review.statement|delay.statement', 'Annual Reports'),
    (r'fee|marking.fee|cost|charge', 'Fees & Charges'),
    (r'bis.act|regulation|amendment|bis.org', 'BIS Act & Regulations'),
    (r'faq|frequently', 'FAQs'),
    (r'consumer|complaint', 'Consumer Affairs'),
    (r'lab|testing|cluster', 'Laboratories & Testing'),
    (r'intern|capsule|training|handbook', 'Training & Internship'),
]


def detect_category(file_path_str: str) -> str:
    """Auto-detect BIS category from file path/name."""
    text = file_path_str.lower().replace('_', ' ').replace('-', ' ')
    for pattern, category in CATEGORY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return category
    return "General BIS"


def load_sources():
    if SOURCES_FILE.exists():
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_sources(sources):
    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=4)

def calculate_file_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += str(page.get_text("text")) + "\n"
    return text

def extract_text_from_html(file_path):
    """Extract meaningful content from BIS HTML pages, stripping navigation boilerplate."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "html.parser")

        # Remove script, style, and non-content elements
        for tag in soup.find_all(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()

        # Remove navigation, header, footer, and sidebar elements
        for tag in soup.find_all(["nav", "header", "footer"]):
            tag.decompose()
        for tag in soup.find_all(attrs={"role": ["navigation", "banner", "contentinfo"]}):  # type: ignore
            tag.decompose()
        for tag in soup.find_all(class_=lambda c: c and any(  # type: ignore
            kw in str(c).lower() for kw in [
                "navbar", "nav-", "navigation", "menu", "sidebar",
                "header", "footer", "breadcrumb", "skip-link",
                "social", "cookie", "banner"
            ]
        )):
            tag.decompose()
        for tag in soup.find_all(id=lambda i: i and any(  # type: ignore
            kw in str(i).lower() for kw in [
                "navbar", "nav-", "navigation", "menu", "sidebar",
                "header", "footer", "breadcrumb"
            ]
        )):
            tag.decompose()

        # Try to find main content area first
        main_content = (
            soup.find("main") or
            soup.find(attrs={"role": "main"}) or  # type: ignore
            soup.find(id=lambda i: i and "content" in str(i).lower()) or  # type: ignore
            soup.find(class_=lambda c: c and "content" in str(c).lower())  # type: ignore
        )
        
        target = main_content if main_content else soup

        raw_text = target.get_text(separator="\n", strip=True)

        # Remove residual BIS navigation boilerplate lines
        nav_markers = {
            "solar power initiative", "pensioners", "comic books",
            "bis logo guidelines", "sales office", "regional office",
            "branch office", "head quarter", "bis apps", "bis  e-book",
            "skip to main content", "skip to content"
        }
        cleaned_lines = []
        for line in raw_text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower() in nav_markers:
                continue
            cleaned_lines.append(stripped)

        text = "\n".join(cleaned_lines)

        # If almost nothing remains after cleaning, fall back to full text
        if len(text) < 100:
            text = soup.get_text(separator="\n", strip=True)

        return text
    except Exception as e:
        print(f"Error parsing HTML {file_path}: {e}")
        return None

def process_file(file_path):
    ext = file_path.suffix.lower()
    try:
        if ext == ".pdf":
            return extract_text_from_pdf(file_path)
        elif ext in [".html", ".htm"]:
            return extract_text_from_html(file_path)
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext in [".csv", ".json"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        else:
            print(f"Unsupported file type: {ext}")
            return None
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None


def extract_clean_title(file_path: Path, file_id: str) -> str:
    """Generate a human-readable title from filename."""
    name = file_path.stem
    # Strip wp-content upload prefix
    name = re.sub(r'^wp[-_]content[-_]uploads[-_]\d+[-_]\d+[-_]', '', name, flags=re.IGNORECASE)
    # Strip path prefixes
    name = re.sub(r'^[a-z]+[\\/]', '', name)
    # Strip language suffix
    name = re.sub(r'_lang-[a-z]+', '', name)
    # Replace separators with spaces
    name = re.sub(r'[-_]+', ' ', name).strip()
    # URL-decode percent-encoded chars
    try:
        from urllib.parse import unquote
        name = unquote(name)
    except Exception:
        pass
    return name.title() if name else file_path.stem.title()


def ingest_documents():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=250,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    # Count all files first for progress
    all_files = [f for f in DATA_DIR.rglob("*") if f.is_file()]
    total_files = len(all_files)
    files_processed = 0
    files_skipped = 0
    total_chunks_added = 0
    errors = []
    
    print(f"Found {total_files} files in {DATA_DIR}")
    print("=" * 60)
    
    for idx, file_path in enumerate(all_files, 1):
        file_hash = calculate_file_hash(file_path)
        file_id = str(file_path.relative_to(DATA_DIR)).replace("\\", "/")
        
        # Check if file has been processed and hasn't changed
        if file_id in sources and sources[file_id]["hash"] == file_hash:
            files_skipped += 1
            if idx % 50 == 0:
                print(f"  [{idx}/{total_files}] Skipping unmodified files... ({files_skipped} skipped)")
            continue
            
        print(f"  [{idx}/{total_files}] Processing: {file_id}")
        
        try:
            text = process_file(file_path)
        except Exception as e:
            errors.append((file_id, str(e)))
            print(f"    ERROR: {e}")
            continue
        
        if not text or len(text.strip()) < 50:
            print(f"    Skipped (no meaningful text extracted)")
            continue
            
        # Create chunks
        chunks = text_splitter.split_text(text)
        
        if not chunks:
            print(f"    Skipped (no chunks generated)")
            continue
        
        # Detect category and file type
        category = detect_category(file_id)
        file_type = file_path.suffix.lower().lstrip(".")
        title = extract_clean_title(file_path, file_id)
        
        # Build metadata and documents
        metadatas = []
        documents = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "source": file_id,
                "title": title,
                "category": category,
                "file_type": file_type,
                "last_updated": datetime.now().isoformat(),
            })
            ids.append(f"{file_id}_chunk_{i}")
        
        # Delete old chunks for this file if it was previously processed
        if file_id in sources:
            try:
                collection.delete(where={"source": file_id})
            except Exception:
                pass
            
        # Add to ChromaDB in batches (ChromaDB has a limit of ~5000 per add)
        batch_size = 100
        for start in range(0, len(documents), batch_size):
            end = min(start + batch_size, len(documents))
            try:
                collection.add(
                    documents=documents[start:end],
                    metadatas=metadatas[start:end],
                    ids=ids[start:end]
                )
            except Exception as e:
                errors.append((file_id, f"Chroma add error: {str(e)}"))
                print(f"    Chroma ADD ERROR: {e}")
            
        # Update sources tracking
        sources[file_id] = {
            "hash": file_hash,
            "processed_at": datetime.now().isoformat(),
            "chunks": len(documents),
            "category": category,
            "title": title,
            "file_type": file_type,
        }
        files_processed += 1
        total_chunks_added += len(documents)
        
        # Save manifest periodically
        if files_processed % 20 == 0:
            save_sources(sources)
            print(f"    [Checkpoint] {files_processed} files processed, {total_chunks_added} chunks added")
            
    save_sources(sources)
    
    print("\n" + "=" * 60)
    print(f"INGESTION COMPLETE")
    print(f"  Files processed/updated: {files_processed}")
    print(f"  Files skipped (unchanged): {files_skipped}")
    print(f"  Total chunks added: {total_chunks_added}")
    print(f"  Total chunks in vectorstore: {collection.count()}")
    print(f"  Errors: {len(errors)}")
    if errors:
        print(f"  Error details:")
        for fid, err in errors[:10]:
            print(f"    - {fid}: {err}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")

if __name__ == "__main__":
    print("Starting ingestion pipeline...")
    print(f"Data directory: {DATA_DIR}")
    print(f"Vectorstore: {VECTORSTORE_DIR}")
    ingest_documents()
