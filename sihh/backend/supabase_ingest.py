import os
import json
from pathlib import Path
from dotenv import load_dotenv
import openai
from supabase import create_client

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY]):
    print("Error: Missing SUPABASE_URL, SUPABASE_KEY, or OPENAI_API_KEY in .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY

def ingest_to_supabase(text, meta):
    # Get embedding
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    embedding = response.data[0].embedding
    
    # Insert to Supabase
    data, count = supabase.table("documents").insert({
        "content": text,
        "metadata": meta,
        "embedding": embedding
    }).execute()
    print(f"Inserted chunk for {meta.get('source')}")

print("Run this file adapted from your original ingest.py to upload to Supabase.")
