import os
import json
from pathlib import Path
from dotenv import load_dotenv
import openai
from supabase import create_client

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY]):
    print("Error: Missing SUPABASE_URL, SUPABASE_KEY, or OPENAI_API_KEY in .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY

def check_table_exists():
    try:
        # Check if we can query the documents table
        response = supabase.table("documents").select("id").limit(1).execute()
        return True
    except Exception as e:
        print("\n[!] CRITICAL ERROR: The 'documents' table does not exist or permissions are blocked.")
        print("You MUST run the code inside `supabase_setup.sql` in your Supabase SQL Editor first!")
        print(f"Error Details: {e}")
        return False

def push_to_supabase(text_chunk, metadata):
    try:
        # 1. Generate Embedding using OpenAI
        response = openai.embeddings.create(
            input=text_chunk,
            model="text-embedding-3-small"
        )
        embedding = response.data[0].embedding
        
        # 2. Insert into Supabase Table
        data, count = supabase.table("documents").insert({
            "content": text_chunk,
            "metadata": metadata,
            "embedding": embedding
        }).execute()
        return True
    except Exception as e:
        print(f"Error inserting chunk: {e}")
        return False

if __name__ == "__main__":
    print("--- BIS Sahayak Supabase Migration ---")
    if not check_table_exists():
        exit(1)
        
    print("\nDatabase is ready! To migrate your data, you should pass chunks to push_to_supabase(text, metadata)")
    print("If you have an OpenAI API Key set up, this script is ready to push your files to the cloud.")
