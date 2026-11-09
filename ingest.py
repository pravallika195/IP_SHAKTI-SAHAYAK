"""Build the IP-SAKTI knowledge base from PDF, DOCX and TXT documents.

Run: python ingest.py
Replace/rebuild the complete corpus: python ingest.py --reset
"""
import logging
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import DATA_DIR, COLLECTION_NAME
from data_loader import load_documents
from text_chunker import chunk_documents
from embedder import get_embeddings
from vector_store import get_client, add_documents
from retriever import clear_bm25_cache

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("ingestion.log", mode="a", encoding="utf-8")])
logger = logging.getLogger(__name__)


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value)[:180]


def run_ingestion() -> int:
    documents = load_documents(DATA_DIR)
    if not documents:
        raise RuntimeError(f"No supported documents found under {DATA_DIR}. Add PDF, DOCX or TXT files.")
    chunks = chunk_documents(documents)
    if not chunks:
        raise RuntimeError("No text chunks were produced. Check document extraction/OCR.")

    logger.info("Embedding %d chunks using configured multilingual model", len(chunks))
    texts = [item["text"] for item in chunks]
    embeddings = get_embeddings(texts, input_type="passage")
    metadatas, ids = [], []
    for item in chunks:
        metadata = {k: v for k, v in item.items() if k not in {"text", "chunk_id"} and v is not None}
        # Chroma metadata supports scalar values; keep every value scalar.
        metadatas.append({k: (v if isinstance(v, (str, int, float, bool)) else str(v)) for k, v in metadata.items()})
        ids.append(_safe_id(item["chunk_id"]))

    client = get_client()
    target_name = COLLECTION_NAME
    staging_name = f"{COLLECTION_NAME}_staging"
    existing_names = {c.name if hasattr(c, "name") else str(c) for c in client.list_collections()}
    if staging_name in existing_names:
        client.delete_collection(staging_name)
    staging = client.create_collection(staging_name, metadata={"description": "Staging index for IP-SAKTI", "hnsw:space": "cosine"})
    add_documents(texts, embeddings, metadatas, ids, collection=staging)
    if staging.count() != len(texts):
        raise RuntimeError(f"Staging validation failed: expected {len(texts)}, found {staging.count()}")

    # Promote only after the full staging index is populated and validated.
    existing_names = {c.name if hasattr(c, "name") else str(c) for c in client.list_collections()}
    if target_name in existing_names:
        client.delete_collection(target_name)
    target = client.create_collection(target_name, metadata={"description": "IP-SAKTI AYUSH prior-art corpus", "hnsw:space": "cosine"})
    for start in range(0, len(texts), 256):
        end = start + 256
        target.upsert(ids=ids[start:end], documents=texts[start:end], embeddings=embeddings[start:end], metadatas=metadatas[start:end])
    if target.count() != len(texts):
        raise RuntimeError("Promotion validation failed; inspect the staging collection before retrying.")
    client.delete_collection(staging_name)
    clear_bm25_cache()
    logger.info("Ingestion complete: %d source units, %d chunks, collection=%s", len(documents), len(chunks), target_name)
    return len(chunks)


if __name__ == "__main__":
    try:
        count = run_ingestion()
        print(f"Indexed {count} chunks into {COLLECTION_NAME}.")
    except Exception as exc:
        logger.exception("Ingestion failed: %s", exc)
        raise SystemExit(1)
