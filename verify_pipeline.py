"""Offline structural checks for the IP-SAKTI RAG pipeline (no LLM key required)."""
import sys
from pathlib import Path
from config import DATA_DIR, COLLECTION_NAME, EMBEDDING_MODEL
from data_loader import load_documents
from text_chunker import chunk_documents
from vector_store import get_or_create_collection

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    print("IP-SAKTI pipeline verification")
    print("Data directory:", DATA_DIR)
    print("Embedding model:", EMBEDDING_MODEL)
    print("Collection:", COLLECTION_NAME)
    if not DATA_DIR.exists():
        print("No corpus directory yet. Create data/documents and add supported files.")
        return
    docs = load_documents(max_files=3)
    print("Loaded sample text units:", len(docs), "(tested on 3 sample files)")
    if not docs:
        print("No text extracted. For scanned PDFs, enable OCR and install Tesseract language packs.")
        return
    chunks = chunk_documents(docs)
    print("Chunks generated:", len(chunks))
    print("Sample metadata:", {k: v for k, v in chunks[0].items() if k != "text"})
    collection = get_or_create_collection()
    print("Existing indexed chunks:", collection.count())
    print("Structural checks passed. Run python ingest.py to build/update the index.")

if __name__ == "__main__":
    main()
