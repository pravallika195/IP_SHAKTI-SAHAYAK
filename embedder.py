"""Multilingual E5 embeddings. Always use passage/query prefixes consistently."""
import logging
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)
_model = None


def get_model():
    global _model
    if _model is None:
        logger.info("Loading multilingual embedding model: %s", EMBEDDING_MODEL)
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def get_embeddings(texts: list[str], batch_size: int = 32, input_type: str = "passage") -> list[list[float]]:
    if not texts:
        return []
    if input_type not in {"passage", "query"}:
        raise ValueError("input_type must be 'passage' or 'query'")
    prefix = "query: " if input_type == "query" else "passage: "
    prepared = [prefix + str(text).strip() for text in texts]
    vectors = get_model().encode(prepared, batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)
    return vectors.tolist()
