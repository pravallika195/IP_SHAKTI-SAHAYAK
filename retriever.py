"""Multilingual hybrid retrieval: dense Chroma search + BM25 + reciprocal-rank fusion."""
from __future__ import annotations
import logging
import re
from collections import defaultdict
from rank_bm25 import BM25Okapi
from embedder import get_embeddings
from vector_store import get_or_create_collection
from config import RETRIEVAL_CANDIDATES

logger = logging.getLogger(__name__)
DEFAULT_TOP_K = 6

# In-memory BM25 caches keyed by collection name to avoid rebuilding on every query
_caches: dict[str, dict] = {}


def clear_bm25_cache():
    """Invalidate all BM25 index caches."""
    global _caches
    _caches.clear()


def _tokens(text: str) -> list[str]:
    # Unicode-aware tokenization retains Devanagari and Telugu characters.
    return re.findall(r"[^\W_]+", (text or "").casefold(), flags=re.UNICODE)


def _get_or_build_bm25(collection):
    """Fetch collection corpus and build BM25 index once per collection; cache in memory."""
    global _caches
    total = collection.count()
    coll_name = getattr(collection, "name", str(collection))

    cached = _caches.get(coll_name)
    if (
        cached is not None
        and cached.get("bm25") is not None
        and cached.get("count") == total
    ):
        return cached

    logger.info("Initializing in-memory BM25 index for collection '%s' (%d chunks)...", coll_name, total)
    corpus = collection.get(include=["documents", "metadatas"])
    corpus_ids = corpus.get("ids", [])
    corpus_docs = corpus.get("documents", [])
    corpus_meta = corpus.get("metadatas", [])

    tokenized = [_tokens(doc) for doc in corpus_docs]
    bm25 = BM25Okapi(tokenized) if (tokenized and any(tokenized)) else None

    by_id = {item_id: (corpus_docs[i], corpus_meta[i]) for i, item_id in enumerate(corpus_ids)}

    cached = {
        "count": total,
        "collection_name": coll_name,
        "corpus_ids": corpus_ids,
        "corpus_docs": corpus_docs,
        "corpus_meta": corpus_meta,
        "bm25": bm25,
        "by_id": by_id,
    }
    _caches[coll_name] = cached
    logger.info("BM25 index ready for '%s' (%d documents indexed).", coll_name, len(corpus_ids))
    return cached


def retrieve(query: str, top_k: int = DEFAULT_TOP_K, filters: dict | None = None,
             candidate_k: int = RETRIEVAL_CANDIDATES, rrf_k: int = 60,
             collection=None) -> list[dict]:
    if not query or not query.strip():
        return []
    collection = collection or get_or_create_collection()
    total = collection.count()
    if total == 0:
        return []

    where = None
    if filters:
        clauses = [{key: value} for key, value in filters.items()]
        where = clauses[0] if len(clauses) == 1 else {"$and": clauses}

    # 1. Dense Chroma retrieval
    query_vector = get_embeddings([query], input_type="query")[0]
    dense = collection.query(query_embeddings=[query_vector], n_results=min(candidate_k, total), where=where,
                             include=["documents", "metadatas", "distances"])
    dense_ids = dense.get("ids", [[]])[0]

    # 2. Fast BM25 Lexical retrieval using in-memory cached index
    cache = _get_or_build_bm25(collection)
    lexical_ranked = []
    if cache["bm25"]:
        query_tokens = _tokens(query)
        if query_tokens:
            scores = cache["bm25"].get_scores(query_tokens)
            sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            for idx in sorted_indices:
                if scores[idx] <= 0:
                    break
                item_id = cache["corpus_ids"][idx]
                # If metadata filters are active, verify the chunk matches
                if filters:
                    meta = cache["corpus_meta"][idx]
                    if not all(meta.get(k) == v for k, v in filters.items()):
                        continue
                lexical_ranked.append(item_id)
                if len(lexical_ranked) >= candidate_k:
                    break

    # 3. Reciprocal Rank Fusion
    fused = defaultdict(float)
    for rank, item_id in enumerate(dense_ids, 1):
        fused[item_id] += 1.0 / (rrf_k + rank)
    for rank, item_id in enumerate(lexical_ranked, 1):
        fused[item_id] += 1.0 / (rrf_k + rank)

    by_id = cache["by_id"]
    dense_distance = {item_id: dense["distances"][0][i] for i, item_id in enumerate(dense_ids)}
    ranked_ids = sorted(fused, key=fused.get, reverse=True)[:top_k]
    output = []
    coll_name = getattr(collection, "name", "corpus")
    for rank, item_id in enumerate(ranked_ids, 1):
        if item_id not in by_id:
            continue
        text, meta = by_id[item_id]
        output.append({
            "id": item_id, "text": text, "source": meta.get("source", meta.get("source_database", "unknown")),
            "source_path": meta.get("source_path", meta.get("source", "unknown")),
            "page": meta.get("page", 0), "section": meta.get("section", "body"),
            "document_type": meta.get("document_type", "other"),
            "language": meta.get("language", "und"),
            "publication_number": meta.get("publication_number", ""),
            "priority_date": meta.get("priority_date", ""), "publication_date": meta.get("publication_date", ""),
            "distance": dense_distance.get(item_id), "rrf_score": round(fused[item_id], 6), "rank": rank,
            "collection": coll_name,
            "raw_metadata": meta
        })
    logger.info("Hybrid retrieval for '%s' returned %d chunks from %d indexed chunks", coll_name, len(output), total)
    return output


def retrieve_multi(query: str, collection_names: list[str] | None = None,
                   top_k: int = DEFAULT_TOP_K, filters: dict | None = None,
                   candidate_k: int = RETRIEVAL_CANDIDATES, rrf_k: int = 60) -> list[dict]:
    """Retrieve across multiple ChromaDB collections and merge candidates via RRF."""
    from vector_store import get_client
    client = get_client()

    if not collection_names:
        collection_names = ["ip_sakti_ayush_v1", "ip_sakti_curcuma_test_v1"]

    existing = {c.name if hasattr(c, "name") else str(c) for c in client.list_collections()}
    target_names = [name for name in collection_names if name in existing]

    if not target_names:
        return []

    if len(target_names) == 1:
        coll = client.get_collection(target_names[0])
        return retrieve(query, top_k=top_k, filters=filters, candidate_k=candidate_k, rrf_k=rrf_k, collection=coll)

    # Multi-collection retrieval and global RRF fusion
    all_results = []
    global_fused = defaultdict(float)
    item_map = {}

    for coll_name in target_names:
        coll = client.get_collection(coll_name)
        coll_results = retrieve(query, top_k=candidate_k, filters=filters, candidate_k=candidate_k, rrf_k=rrf_k, collection=coll)
        for rank, res in enumerate(coll_results, 1):
            uid = f"{coll_name}::{res['id']}"
            global_fused[uid] += 1.0 / (rrf_k + rank)
            if uid not in item_map:
                item_map[uid] = res

    ranked_uids = sorted(global_fused, key=global_fused.get, reverse=True)[:top_k]
    final_output = []
    for rank, uid in enumerate(ranked_uids, 1):
        item = item_map[uid]
        item["global_rank"] = rank
        item["global_rrf_score"] = round(global_fused[uid], 6)
        final_output.append(item)

    logger.info("Multi-collection retrieval across %s returned %d top chunks", target_names, len(final_output))
    return final_output


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for result in retrieve("turmeric neem herbal formulation patent claims", top_k=5):
        print(result["rank"], result["source"], result["page"], result["section"], result["rrf_score"])

