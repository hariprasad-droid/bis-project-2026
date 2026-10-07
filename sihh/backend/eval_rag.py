"""
Retrieval evaluation for the BIS RAG pipeline (no LLM calls, fast).

Measures hit@k and MRR of the reranked top-k against expected source keywords.

Usage:
  python eval_rag.py              # hybrid search (if the RPC exists) + rerank
  python eval_rag.py --dense      # force dense-only search, for before/after comparison
  python eval_rag.py --k 5 -v     # verbose: show the top sources for every query
"""
import sys
import io
import argparse

if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import rag_engine

# (query, [any of these keywords must appear in the source path or title])
EVAL_SET = [
    ("What is the hallmarking process for gold jewellery?", ["hallmark"]),
    ("what is HUID number on jewellery", ["hallmark", "huid"]),
    ("how to register as a jeweller for hallmarking", ["hallmark", "jeweller"]),
    ("What is an Assaying and Hallmarking Centre (AHC)?", ["hallmark", "ahc", "assay"]),
    ("Specifications for packaged drinking water IS 14543", ["water", "14543"]),
    ("IS 10500 drinking water requirements", ["water", "10500"]),
    ("what is CRS scheme for mobile chargers", ["crs", "registration", "electronic"]),
    ("Compulsory Registration Scheme electronics products list", ["crs", "registration", "electronic"]),
    ("What is ISI mark and how to get it?", ["product_certification", "certification", "isi", "scheme"]),
    ("steps to get BIS licence for factory", ["product_certification", "certification", "licence", "scheme"]),
    ("Foreign Manufacturers Certification Scheme process", ["fmcs", "foreign"]),
    ("What are Quality Control Orders?", ["quality_control", "qco", "quality control"]),
    ("Is QCO mandatory for steel products?", ["quality_control", "qco", "steel"]),
    ("BIS marking fee and application fee", ["fee", "charge"]),
    ("how much does BIS certification cost", ["fee", "charge"]),
    ("What does the BIS Act 2016 say?", ["bis_act", "act"]),
    ("penalties under BIS Act for misuse of standard mark", ["bis_act", "act"]),
    ("how to file a consumer complaint with BIS", ["consumer", "complaint", "faq"]),
    ("BIS recognised testing laboratories", ["lab", "testing"]),
    ("frequently asked questions about BIS", ["faq"]),
]


def source_matches(chunk: dict, keywords: list[str]) -> bool:
    meta = chunk.get("metadata", {}) or {}
    hay = f"{meta.get('source', '')} {meta.get('title', '')} {meta.get('category', '')}".lower().replace("-", "_")
    return any(k.lower().replace("-", "_") in hay or k.lower() in hay.replace("_", " ") for k in keywords)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--dense", action="store_true", help="force dense-only retrieval")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.dense:
        rag_engine._hybrid_available = False

    hits, rr_total, modes = 0, 0.0, set()
    for query, keywords in EVAL_SET:
        candidates = rag_engine.retrieve_chunks(query, top_k=40)
        if candidates:
            modes.add(candidates[0].get("retrieval_mode", "?"))
        top = rag_engine.rerank_chunks(query, candidates, top_n=args.k)

        rank = next((i + 1 for i, c in enumerate(top) if source_matches(c, keywords)), None)
        if rank:
            hits += 1
            rr_total += 1.0 / rank
        status = f"HIT@{rank}" if rank else "MISS "
        print(f"[{status:6}] {query}")
        if args.verbose or not rank:
            for i, c in enumerate(top):
                m = c["metadata"]
                print(f"      {i+1}. {m.get('source', '?')}  score={c.get('rerank_score', 0):.3f} "
                      f"sim={c.get('similarity', 0):.3f} overlap={c.get('lexical_overlap', 0):.2f}")

    n = len(EVAL_SET)
    print("\n" + "=" * 60)
    print(f"Retrieval mode : {', '.join(sorted(modes)) or 'n/a'}")
    print(f"Nomic prefixes : {'ON' if rag_engine.use_nomic_prefixes() else 'OFF'}")
    print(f"Hit@{args.k}         : {hits}/{n} = {hits / n:.2%}")
    print(f"MRR@{args.k}         : {rr_total / n:.3f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
