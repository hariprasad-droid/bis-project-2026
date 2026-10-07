import os
import chromadb
import requests
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path
import time

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
OLLAMA_CLOUD_API_KEY = os.environ.get("OLLAMA_CLOUD_API_KEY", "")
OLLAMA_URL = os.environ.get("OLLAMA_CLOUD_URL", "").replace("/chat/completions", "/embeddings")

if not SUPABASE_URL or not SUPABASE_KEY or not OLLAMA_CLOUD_API_KEY:
    print("Missing environment variables. Check .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = chromadb.PersistentClient(path=str(BASE_DIR / "vectorstore"))
collection = client.get_or_create_collection(name="bis_knowledge_base")

docs = collection.get(include=["documents", "metadatas"])
documents = docs.get("documents")
metadatas = docs.get("metadatas")

if not documents or not metadatas:
    print("No documents found in local ChromaDB.")
    exit(0)

total_docs = len(documents)
print(f"Found {total_docs} documents in local ChromaDB.")

success_count = 0
for i in range(total_docs):
    text = documents[i]
    metadata = metadatas[i]
    
    # 1. Get Embedding
    headers = {
        "Authorization": f"Bearer {OLLAMA_CLOUD_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nomic-embed-text",
        "input": text
    }
    try:
        resp = requests.post(OLLAMA_URL, headers=headers, json=payload, timeout=20)
        if resp.status_code == 200:
            embedding = resp.json()["data"][0]["embedding"]
            
            # 2. Push to Supabase
            supabase.table("documents").insert({
                "content": text,
                "metadata": metadata, # type: ignore
                "embedding": embedding
            }).execute()
            
            success_count += 1
            if i % 10 == 0:
                print(f"Progress: {i}/{total_docs} (Success: {success_count})")
        else:
            print(f"Failed to embed chunk {i}. Status: {resp.status_code}")
    except Exception as e:
        print(f"Error on chunk {i}: {e}")

print(f"\nMigration complete! Successfully migrated {success_count} out of {total_docs} documents.")
