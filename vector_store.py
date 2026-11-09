"""ChromaDB persistence for the IP-SAKTI corpus (cosine distance)."""
import logging
import chromadb
from config import VECTOR_STORE_DIR, COLLECTION_NAME

logger = logging.getLogger(__name__)


def get_client():
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))


def get_or_create_collection(client=None):
    client = client or get_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "IP-SAKTI AYUSH prior-art corpus", "hnsw:space": "cosine"},
    )
    metric = (collection.metadata or {}).get("hnsw:space")
    if metric != "cosine":
        raise RuntimeError(
            f"Collection '{COLLECTION_NAME}' is not configured for cosine distance (found {metric!r}). "
            "Back up and remove the IP-SAKTI vector-store directory, then run python ingest.py."
        )
    return collection


def add_documents(texts, embeddings, metadatas, ids, collection=None, batch_size=256):
    if not (len(texts) == len(embeddings) == len(metadatas) == len(ids)):
        raise ValueError("texts, embeddings, metadatas and ids must have equal lengths")
    collection = collection or get_or_create_collection()
    for start in range(0, len(texts), batch_size):
        end = start + batch_size
        # upsert makes repeated ingestion of the same IDs idempotent.
        collection.upsert(documents=texts[start:end], embeddings=embeddings[start:end],
                          metadatas=metadatas[start:end], ids=ids[start:end])
    logger.info("Collection now contains %d chunks", collection.count())


def query_collection(query_embedding, n_results=10, collection=None, where=None):
    collection = collection or get_or_create_collection()
    if collection.count() == 0:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
    return collection.query(query_embeddings=[query_embedding], n_results=min(n_results, collection.count()),
                            where=where, include=["documents", "metadatas", "distances"])
