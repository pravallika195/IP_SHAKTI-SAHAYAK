"""Command-line interface for IP-SAKTI Sahayak."""
import argparse
import json
import sys
from rag_pipeline import RAGPipeline
from config import TOP_K

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="IP-SAKTI AYUSH prior-art research assistant")
    parser.add_argument("--query", help="Formulation, ingredient or prior-art question")
    parser.add_argument("--language", default="English", help="Answer language")
    args = parser.parse_args()
    query = args.query or input("Describe the AYUSH formulation / prior-art question: ").strip()
    language = args.language if args.query else (input("Answer language [English/Hindi/Telugu] (default English): ").strip() or "English")
    pipeline = RAGPipeline(top_k=TOP_K)
    result = pipeline.run(query, user_language=language)
    print("\n" + "=" * 72 + "\nIP-SAKTI SAHAYAK — EVIDENCE-BASED RESEARCH OUTPUT\n" + "=" * 72)
    print(result["answer"])
    print("\nRetrieved sources:")
    print(json.dumps(result["sources"], ensure_ascii=False, indent=2))
    print("\nNote: Retrieval similarity is not a legal novelty, validity or infringement opinion.")


if __name__ == "__main__":
    main()
