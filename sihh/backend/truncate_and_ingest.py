import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import time
import subprocess

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing SUPABASE_URL or SUPABASE_KEY in .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Deleting all records from 'documents' table...")
try:
    # Delete all rows where id is not null (which is all rows)
    res = supabase.table("documents").delete().neq("id", -1).execute()
    print(f"Deleted records.")
except Exception as e:
    print(f"Error deleting records: {e}")

time.sleep(2)
print("Now running supabase_ingest.py...")
subprocess.run([".\\venv\\Scripts\\python.exe", "supabase_ingest.py"])
print("Ingestion complete.")
