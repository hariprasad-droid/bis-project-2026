import sys
import io
if isinstance(sys.stdout, io.TextIOWrapper) and \
    sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
import json
from rag_engine import retrieve_chunks, generate_answer

q = "What documents are required to apply for a CRS (Compulsory Registration Scheme) certificate for mobile chargers?"
print("--- RETRIEVAL ---")
chunks = retrieve_chunks(q, top_k=5)
for i, c in enumerate(chunks):
    print(f"[{i+1}] Source: {c['metadata']['source']} (Dist: {c['distance']})")
    print(c['text'][:200])
    print("="*40)

print("\n--- GENERATED ANSWER ---")
res = generate_answer(q)
print(json.dumps(res, indent=2))
