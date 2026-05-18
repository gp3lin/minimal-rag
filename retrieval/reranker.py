"""
BGE cross-encoder reranker: (query, passage) çiftlerini puanlar, top-k döner.
Model: BAAI/bge-reranker-base (~400MB, ilk çalıştırmada indirilir)
"""
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

RERANKER_MODEL = "BAAI/bge-reranker-base"
RERANK_TOP_K = 5


@lru_cache(maxsize=1)
def _get_reranker():
    from sentence_transformers import CrossEncoder
    logger.info(f"Reranker yükleniyor: {RERANKER_MODEL}")
    return CrossEncoder(RERANKER_MODEL)


def rerank(query: str, chunks: list[dict], top_k: int = RERANK_TOP_K) -> list[dict]:
    """Chunk listesini rerank eder, top_k tane döner."""
    if not chunks:
        return []

    reranker = _get_reranker()
    pairs = [(query, c["text"]) for c in chunks]
    scores = reranker.predict(pairs)

    ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    result = []
    for score, chunk in ranked[:top_k]:
        chunk = dict(chunk)
        chunk["rerank_score"] = round(float(score), 4)
        result.append(chunk)

    logger.info(f"Rerank: {len(chunks)} → {len(result)} chunk (top score: {result[0]['rerank_score'] if result else '-'})")
    return result
